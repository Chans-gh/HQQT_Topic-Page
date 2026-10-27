"""Deterministic scope checks. Recorded evidence is NOT proof of human consent."""
import re

STAGES = {'INTAKE', 'LIST_REVIEW', 'DRAFT', 'DRAFT_REVIEW', 'REFINE', 'DELIVERY'}


def objects(record):
    result = {}
    for kind in ('modules', 'sources', 'media', 'resources'):
        items = record.get(kind, [])
        if not isinstance(items, list):
            raise ValueError(f'{kind} must be a list')
        found = {}
        for item in items:
            ident = item.get('id', '')
            pattern = {'modules': r'M\d{2,}', 'sources': r'S[\w-]+', 'media': r'IMG-\d{2,}', 'resources': r'RES-\d{2,}'}[kind]
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


def source_ready(record, source):
    adopted = source.get('adoption') == 'adopted' and (
        approved(record, 'list', 'sources', source) or approved(record, 'draft', 'sources', source))
    # An attributed input is a claim ABOUT the supplied material, not independent proof of its claims.
    attributed = (source.get('kind') == 'input' and source.get('citation_mode') == 'attributed-input'
                  and source.get('reading') == 'checked' and bool(source.get('read_scope'))
                  and source.get('claim_scope') == 'attributed'
                  and bool(source.get('internal_note') or source.get('public_note')))
    return adopted and (source.get('verification') == 'verified' or attributed)


def module_mode(record, item, mode):
    if mode == 'draft' and record.get('task', {}).get('mixed_scope'):
        value = item.get('render_mode', 'draft')
        if value not in {'draft', 'refine'}:
            raise ValueError('mixed module render_mode must be draft/refine')
        return value
    return mode


def validate_editorial(item):
    fields = ('reader_question', 'key_message', 'content_layers', 'deduplication', 'relationship', 'visual_intent')
    if any(not item.get(k) for k in fields):
        raise ValueError(f'{item["id"]}: incomplete editorial decisions')
    layers = item['content_layers']; visual = item['visual_intent']
    if not isinstance(layers, dict) or not all(layers.get(k) for k in ('primary', 'support', 'evidence', 'conditions')):
        raise ValueError(f'{item["id"]}: content layers need primary/support/evidence/conditions (use explicit none when absent)')
    if not isinstance(visual, dict) or not all(visual.get(k) for k in ('focus', 'order', 'web', 'h5')):
        raise ValueError(f'{item["id"]}: visual focus/order/web/h5 required')


def validate_record(record, mode, module_ids):
    if mode not in {'draft', 'refine', 'final'}:
        raise ValueError('mode must be draft/refine/final')
    task = record.get('task', {})
    allowed = {'draft': {'DRAFT', 'DRAFT_REVIEW'}, 'refine': {'REFINE'}, 'final': {'DELIVERY'}}
    mixed_refine = mode == 'refine' and task.get('mixed_scope') and task.get('stage') in {'DRAFT','DRAFT_REVIEW'}
    if task.get('stage') not in allowed[mode] and not mixed_refine:
        raise ValueError(f'phase does not allow {mode}: {task.get("stage")}')
    data = objects(record)
    if not module_ids or len(module_ids) != len(set(module_ids)):
        raise ValueError('nonempty unique module scope required')
    for ident in module_ids:
        item = data['modules'].get(ident)
        if mixed_refine and item and item.get('render_mode') != 'refine':
            raise ValueError(f'{ident}: generation/refine scope is not declared refined')
        if not item or item.get('removed'):
            raise ValueError(f'unknown/removed module {ident}')
        if not approved(record, 'list', 'modules', item):
            raise ValueError(f'{ident}: missing exact list approval')
        effective = module_mode(record, item, mode)
        if effective != 'draft' and not approved(record, 'draft', 'modules', item):
            raise ValueError(f'{ident}: missing exact draft approval')
        if task.get('editorial_contract') == 1:
            validate_editorial(item)
        for sid in item.get('sources', []):
            if sid not in data['sources']:
                raise ValueError(f'{ident}: unknown source {sid}')
            if data['sources'][sid].get('kind') not in {'input','web'}:
                raise ValueError(f'{sid}: source kind must be input/web')
        for mid in item.get('media', []):
            if mid not in data['media'] or data['media'][mid].get('module') != ident:
                raise ValueError(f'{ident}: invalid media association {mid}')
        for rid in item.get('resources', []):
            resource = data['resources'].get(rid)
            if not resource or resource.get('module') != ident:
                raise ValueError(f'{ident}: invalid resource association {rid}')
            if resource.get('status') not in {'pending', 'unavailable', 'omitted'}:
                raise ValueError(f'{rid}: only honest unavailable/omitted video notices are supported; real video delivery needs a separately audited resource package')
            if resource.get('status') == 'omitted' and not approved(record, 'omit', 'resources', resource):
                raise ValueError(f'{rid}: resource omission needs explicit evidence')
            if mode == 'final' and resource.get('status') != 'omitted':
                if not (resource.get('status') == 'unavailable' and resource.get('resolution') == 'retain-notice'
                        and resource.get('public_note') and approved(record, 'retain', 'resources', resource)):
                    raise ValueError(f'{rid}: unresolved resource prevents final')
        if mode == 'final':
            for sid in item.get('sources', []):
                source = data['sources'][sid]
                if not source_ready(record, source):
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
    orders = [data['modules'][i].get('order') for i in module_ids]
    if any(not isinstance(o, int) for o in orders) or orders != sorted(set(orders)):
        raise ValueError('module DOM order differs from recorded unique order')
    if task.get('mixed_scope') and mode == 'draft':
        active = {m['id'] for m in data['modules'].values() if not m.get('removed')}
        if set(module_ids) != active:
            raise ValueError('mixed-scope validation requires the complete active page')
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
