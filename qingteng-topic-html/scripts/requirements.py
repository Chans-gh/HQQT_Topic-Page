"""Keep user asset requirements separate from mutable design decisions.

These checks verify recorded evidence and files, not the authenticity of user
quotes, provider calls, or the quality/meaning of an illustration.
"""
import base64
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path


def user_evidence(value):
    return (isinstance(value, dict) and value.get('actor') == 'user'
            and all(isinstance(value.get(k), str) and value[k].strip() for k in ('locator', 'text')))


def load_requirements(record, task_dir):
    contract = record.get('task', {}).get('requirements_contract')
    if contract is None:
        return None  # Legacy tasks can still be composed; fulfillment stays unknown.
    if type(contract) is not int or contract != 1 or task_dir is None:
        raise ValueError('requirements_contract=1 needs the saved task directory')
    if type(record['task'].get('production_contract')) is not int or record['task']['production_contract'] < 2:
        raise ValueError('independent asset requirements need production_contract>=2 for actual generation/alpha checks')
    path = Path(task_dir) / 'requirements.json'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['task'].get('requirements_sha256'):
        raise ValueError('requirements.json SHA mismatch; restore the pinned brief or record the actual user revision')
    data = json.loads(raw.decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('requirements.json must be an object')
    review = data.get('review', {})
    if (data.get('schema') != 'qt-requirements/1' or review.get('status') != 'checked'
            or not isinstance(review.get('context'), list) or not review['context']
            or not all(isinstance(v, str) and v.strip() for v in review['context'])
            or not isinstance(review.get('note'), str) or not review['note'].strip()
            or not isinstance(data.get('assets'), list)):
        raise ValueError('requirements history must be checked before declaring no asset requirements')
    seen = set()
    for item in data['assets']:
        if not isinstance(item, dict):
            raise ValueError('asset requirement must be an object')
        ident = item.get('id', '')
        scope = item.get('modules')
        if (not re.fullmatch(r'AR-\d{2,}', ident) or ident in seen
                or not isinstance(scope, list) or not scope or len(scope) != len(set(scope))
                or not all(isinstance(m, str) and re.fullmatch(r'M\d{2,}', m) for m in scope)
                or not item.get('purpose') or item.get('background') not in {'any', 'transparent', 'opaque'}
                or item.get('status') not in {'active', 'waived'} or not user_evidence(item.get('evidence'))):
            raise ValueError('invalid independently recorded asset requirement: ' + ident)
        if item['status'] == 'waived' and not user_evidence(item.get('change_evidence')):
            raise ValueError(ident + ': only an explicit user change can waive an existing requirement')
        seen.add(ident)
    return data


def validate_requirements(record, task_dir, mode, module_ids):
    data = load_requirements(record, task_dir)
    if data is None:
        return {'status': 'not-run', 'required': [], 'reason': 'legacy requirements were not captured; reconcile the actual conversation before a new production pass'}
    active_modules = {m['id'] for m in record.get('modules', []) if not m.get('removed')}
    media = {m['id']: m for m in record.get('media', [])}
    bindings = record.get('requirement_bindings', {})
    known = {r['id'] for r in data['assets']}
    if not isinstance(bindings, dict) or set(bindings) - known:
        raise ValueError('unknown asset requirement binding')
    required, fulfilled = [], {}
    for req in data['assets']:
        if req['status'] == 'waived':
            continue
        ident = req['id']
        if set(req['modules']) - active_modules:
            raise ValueError(ident + ': required module was removed or is unknown; preserve it or record the actual user change')
        scope = set(req['modules']) & set(module_ids)
        if not scope:
            continue
        required.append(ident)
        ids = bindings.get(ident, [])
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            raise ValueError(ident + ': missing generated-image fulfillment plan; no-gap design declarations cannot waive it')
        covered = set()
        for mid in ids:
            item = media.get(mid)
            if (not item or item.get('module') not in req['modules']
                    or mid not in next(m for m in record['modules'] if m['id'] == item['module']).get('media', [])
                    or item.get('plan') != 'generate' or item.get('status') == 'omitted'
                    or item.get('role') not in {'illustration', 'cover', 'person'}
                    or req['background'] != 'any' and item.get('background') != req['background']):
                raise ValueError(ident + ': original screenshots, icons, omitted images or wrong backgrounds do not fulfill the required generated illustration')
            if mode == 'final' and (item.get('status') != 'complete' or not item.get('local_path')):
                raise ValueError(ident + ': generated image is still incomplete')
            covered.add(item['module'])
        if scope - covered:
            raise ValueError(ident + ': required modules lack generated illustrations: ' + ','.join(sorted(scope-covered)))
        fulfilled[ident] = ids
    return {'status': 'pass', 'required': required, 'bindings': fulfilled,
            'scope': 'Pinned user brief and declared coverage only; actual bytes and visual judgment are checked separately.'}


class EmbeddedMedia(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.images = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'figure':
            self.current = attrs.get('data-media-id')
        if tag == 'img' and self.current:
            uri = attrs.get('src', '')
            if not re.match(r'^data:image/[^;,]+;base64,', uri):
                raise ValueError('required image is not embedded base64 media')
            raw = base64.b64decode(uri.split(',', 1)[1], validate=True)
            self.images.setdefault(self.current, []).append(hashlib.sha256(raw).hexdigest())

    def handle_endtag(self, tag):
        if tag == 'figure':
            self.current = None


def audit_requirement_media(html, record, task_dir, module_ids=None):
    module_ids = module_ids if module_ids is not None else [m['id'] for m in record.get('modules', []) if not m.get('removed')]
    result = validate_requirements(record, task_dir, 'final', module_ids)
    if result['status'] != 'pass':
        return result
    # Reuse production byte validation for MIME/provider/SHA/PNG alpha. No generator.
    from production import audit_assets
    scoped = {**record, 'modules': [m for m in record.get('modules', []) if m['id'] in module_ids]}
    audited = audit_assets(scoped, task_dir, 'final')
    actual = EmbeddedMedia(html).images
    for item in audited['assets']:
        if actual.get(item['id']) != [item['sha256']]:
            raise ValueError(item['id'] + ': actual embedded image bytes differ from the task asset')
    return {**result, 'generated_assets': audited['task_generated_assets'],
            'scope': 'Actual embedded bytes, generated asset records and required coverage; not proof of provider calls or visual quality.'}
