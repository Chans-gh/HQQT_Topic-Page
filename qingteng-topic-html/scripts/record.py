"""Deterministic scope checks. Recorded evidence is NOT proof of human consent."""
import re

STAGES = {'INTAKE', 'LIST_REVIEW', 'DRAFT', 'DRAFT_REVIEW', 'REFINE', 'DELIVERY'}


def objects(record):
    result = {}
    for kind in ('modules', 'sources', 'media'):
        items = record.get(kind, [])
        if not isinstance(items, list):
            raise ValueError(f'{kind} must be a list')
        found = {}
        for item in items:
            ident = item.get('id', '')
            pattern = {'modules': r'M\d{2,}', 'sources': r'S[\w-]+', 'media': r'IMG-\d{2,}'}[kind]
            if not re.fullmatch(pattern, ident) or ident in found:
                raise ValueError(f'invalid/duplicate {kind} ID: {ident}')
            if not isinstance(item.get('revision'), int) or item['revision'] < 1:
                raise ValueError(f'{ident}: positive revision required')
            found[ident] = item
        result[kind] = found
    return result


def approved(record, stage, kind, item):
    """Exact per-object version AND revision. Unchanged objects keep prior versions."""
    version_key = 'list_version' if stage == 'list' else 'draft_version'
    revision_key = 'draft_revision' if stage == 'draft' and kind == 'modules' else 'revision'
    version = item.get(version_key)
    revision = item.get(revision_key)
    if not version or not revision:
        return False
    for entry in record.get('approvals', []):
        evidence = entry.get('evidence', {})
        if (entry.get('stage') == stage and entry.get('version') == version
                and evidence.get('actor') == 'user' and evidence.get('locator')
                and evidence.get('text', '').strip()
                and entry.get('scope', {}).get(kind, {}).get(item['id']) == revision):
            return True
    return False


def validate_record(record, mode, module_ids):
    if mode not in {'draft', 'refine', 'final'}:
        raise ValueError('mode must be draft/refine/final')
    task = record.get('task', {})
    allowed = {'draft': {'DRAFT', 'DRAFT_REVIEW'}, 'refine': {'REFINE'}, 'final': {'DELIVERY'}}
    if task.get('stage') not in allowed[mode]:
        raise ValueError(f'phase does not allow {mode}: {task.get("stage")}')
    data = objects(record)
    if not module_ids or len(module_ids) != len(set(module_ids)):
        raise ValueError('nonempty unique module scope required')
    for ident in module_ids:
        item = data['modules'].get(ident)
        if not item or item.get('removed'):
            raise ValueError(f'unknown/removed module {ident}')
        if not approved(record, 'list', 'modules', item):
            raise ValueError(f'{ident}: missing exact list approval')
        if mode != 'draft' and not approved(record, 'draft', 'modules', item):
            raise ValueError(f'{ident}: missing exact draft approval')
        for sid in item.get('sources', []):
            if sid not in data['sources']:
                raise ValueError(f'{ident}: unknown source {sid}')
        for mid in item.get('media', []):
            if mid not in data['media'] or data['media'][mid].get('module') != ident:
                raise ValueError(f'{ident}: invalid media association {mid}')
        if mode == 'final':
            for sid in item.get('sources', []):
                source = data['sources'][sid]
                if (source.get('verification') != 'verified' or source.get('adoption') != 'adopted'
                        or not (approved(record, 'list', 'sources', source) or approved(record, 'draft', 'sources', source))):
                    raise ValueError(f'{sid}: unresolved source prevents final')
            for mid in item.get('media', []):
                media = data['media'][mid]
                if media.get('status') == 'omitted':
                    if not approved(record, 'omit', 'media', media):
                        raise ValueError(f'{mid}: omission needs explicit scope evidence')
                    continue
                if media.get('status') not in {'available', 'complete'} or not media.get('local_path'):
                    raise ValueError(f'{mid}: unresolved image prevents final')
                if media.get('plan') == 'input':
                    if not approved(record, 'reuse', 'media', media):
                        raise ValueError(f'{mid}: input reuse is not authorized')
                elif media.get('plan') == 'generate':
                    if not (approved(record, 'draft', 'media', media) and approved(record, 'generate', 'media', media)):
                        raise ValueError(f'{mid}: generation is not authorized')
                else:
                    raise ValueError(f'{mid}: source plan still undecided')
        if mode == 'final' and item.get('issues'):
            raise ValueError(f'{ident}: unresolved facts/review issues')
    if mode == 'final':
        # A deliberately partial final delivery needs an explicit deliverable scope.
        active = {m['id'] for m in data['modules'].values() if not m.get('removed')}
        if set(module_ids) != active and set(task.get('delivery_scope', [])) != set(module_ids):
            raise ValueError('partial final requires explicit task.delivery_scope')
    return data


def generation_plan(record, module_ids):
    """Pure output only. Never calls any generator or updates approvals/status."""
    data = validate_record(record, 'refine', module_ids)
    eligible, blocked = [], []
    current_media = {mid for ident in module_ids for mid in data['modules'][ident].get('media', [])}
    for item in data['media'].values():
        if item['id'] not in current_media or item.get('module') not in module_ids or item.get('plan') != 'generate':
            continue
        if item.get('status') in {'complete', 'omitted'}:
            continue
        if (approved(record, 'draft', 'media', item)
                and approved(record, 'generate', 'media', item)):
            eligible.append(item['id'])
        else:
            blocked.append(item['id'])
    return {'eligible': eligible, 'blocked': blocked,
            'notice': 'Record check only; executor must verify actual user evidence. No calls executed.'}
