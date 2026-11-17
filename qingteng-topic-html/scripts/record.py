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


def execution_allowed(record, action, kind, item):
    """Permission to finish scoped work, distinct from a review of rendered output."""
    revision = item.get('draft_revision') if kind == 'modules' else item.get('revision')
    for entry in record.get('execution_authorizations', []):
        evidence = entry.get('evidence', {})
        if (entry.get('version') == item.get('draft_version')
                and item.get('draft_version') and revision
                and isinstance(entry.get('actions'), list) and action in entry['actions']
                and entry.get('scope', {}).get(kind, {}).get(item['id']) == revision
                and evidence.get('actor') == 'user' and evidence.get('locator')
                and evidence.get('text', '').strip()):
            return True
    return False


def refine_allowed(record, kind, item):
    return approved(record, 'draft', kind, item) or execution_allowed(record, 'refine', kind, item)


def generation_allowed(record, item):
    return refine_allowed(record, 'media', item) and (
        approved(record, 'generate', 'media', item) or execution_allowed(record, 'generate', 'media', item))


def validate_asset_review(record, mode, module_ids):
    if not record.get('task', {}).get('production_contract') or mode == 'draft':
        return
    review = record['task'].get('asset_review', {})
    if not isinstance(review, dict):
        raise ValueError('asset assessment must be an object')
    if (review.get('decision') not in {'none', 'reuse', 'generate', 'mixed'}
            or not isinstance(review.get('rationale'), str) or not review['rationale'].strip()):
        raise ValueError('production requires an explicit asset assessment, including an intentional no-image decision')
    if not isinstance(review.get('gaps'), list):
        raise ValueError('asset assessment requires a gaps list')
    if mode == 'final' and review['gaps']:
        raise ValueError('unresolved asset assessment gaps prevent final')
    active_ids = {m['id'] for m in record.get('modules', []) if not m.get('removed')}
    active = [m for m in record.get('media', []) if m.get('module') in active_ids and m.get('status') != 'omitted']
    plans = {m.get('plan') for m in active}
    expected = {'none': set(), 'reuse': {'input'}, 'generate': {'generate'}, 'mixed': {'input', 'generate'}}[review['decision']]
    if plans != expected:
        raise ValueError('asset assessment differs from the active image plans')


def source_ready(record, source):
    adopted = source.get('adoption') == 'adopted' and (
        approved(record, 'list', 'sources', source) or approved(record, 'draft', 'sources', source)
        or execution_allowed(record, 'refine', 'sources', source))
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


def validate_record(record, mode, module_ids, task_dir=None):
    if mode not in {'draft', 'refine', 'final'}:
        raise ValueError('mode must be draft/refine/final')
    task = record.get('task', {})
    if 'delivery_contract' in task and (type(task['delivery_contract']) is not int or task['delivery_contract']!=1):
        raise ValueError('delivery_contract must be 1 when supplied')
    allowed = {'draft': {'DRAFT', 'DRAFT_REVIEW'}, 'refine': {'REFINE'}, 'final': {'DELIVERY'}}
    mixed_refine = mode == 'refine' and task.get('mixed_scope') and task.get('stage') in {'DRAFT','DRAFT_REVIEW'}
    if task.get('stage') not in allowed[mode] and not mixed_refine:
        raise ValueError(f'phase does not allow {mode}: {task.get("stage")}')
    from input_sources import validate_inputs
    validate_inputs(record, require_read=True, task_dir=task_dir)
    data = objects(record)
    from page_modes import validate_page_mode
    validate_page_mode(
        record,
        data['modules'],
        lambda item: approved(record, 'list', 'modules', item),
        require_selected=True,
        task_dir=task_dir,
    )
    if not module_ids or len(module_ids) != len(set(module_ids)):
        raise ValueError('nonempty unique module scope required')
    from requirements import validate_requirements
    validate_requirements(record, task_dir, mode, module_ids)
    validate_asset_review(record, mode, module_ids)
    for ident in module_ids:
        item = data['modules'].get(ident)
        if mixed_refine and item and item.get('render_mode') != 'refine':
            raise ValueError(f'{ident}: generation/refine scope is not declared refined')
        if not item or item.get('removed'):
            raise ValueError(f'unknown/removed module {ident}')
        if not (approved(record, 'list', 'modules', item) or execution_allowed(record, 'refine', 'modules', item)):
            raise ValueError(f'{ident}: missing exact list review or scoped execution authorization')
        effective = module_mode(record, item, mode)
        if effective != 'draft' and not refine_allowed(record, 'modules', item):
            raise ValueError(f'{ident}: missing exact draft review or scoped execution authorization')
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
                    if not generation_allowed(record, media):
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
    from production import validate_production
    validate_production(record, mode, module_ids)
    return data


def generation_plan(record, module_ids, task_dir=None):
    """Pure output only. Never calls any generator or updates approvals/status."""
    data = validate_record(record, 'refine', module_ids, task_dir)
    eligible, blocked = [], []
    current_media = {mid for ident in module_ids for mid in data['modules'][ident].get('media', [])}
    for item in data['media'].values():
        if item['id'] not in current_media or item.get('module') not in module_ids or item.get('plan') != 'generate':
            continue
        if item.get('status') in {'complete', 'omitted'}:
            continue
        if generation_allowed(record, item):
            eligible.append(item['id'])
        else:
            blocked.append(item['id'])
    return {'eligible': eligible, 'blocked': blocked,
            'notice': 'Record check only; executor must verify actual user evidence. No calls executed.'}


def task_bundle(source, out, paths):
    """Copy explicit task inputs and referenced media into a new self-contained directory."""
    import hashlib, json
    from pathlib import Path
    source=Path(source).resolve();out=Path(out).resolve()
    from html_support import ROOT
    if out.is_relative_to(ROOT) or out==source or out.is_relative_to(source):
        raise ValueError('bundle output must be new, outside source task and Skill')
    if out.exists():raise ValueError('bundle output already exists')
    selected={}
    for name in paths:
        if Path(name).is_absolute() or '..' in Path(name).parts or name=='snapshot.json':raise ValueError('unsafe task path')
        f=source/name
        if not f.is_file() or not f.resolve().is_relative_to(source):raise ValueError('missing or unsafe task input: '+name)
        selected[name]=f.read_bytes()
    if 'record.json' not in selected:raise ValueError('record.json is required')
    record=json.loads(selected['record.json'])
    if record.get('task', {}).get('requirements_contract') is not None:
        brief = source / 'requirements.json'
        if not brief.is_file():
            raise ValueError('independent requirements.json is missing')
        selected['requirements.json'] = brief.read_bytes()
    for item in record.get('inputs', []):
        local = item.get('local_path')
        if not local:
            continue
        asset = Path(local)
        asset = asset if asset.is_absolute() else source / asset
        asset = asset.resolve()
        if not asset.is_file():
            raise ValueError('missing task input file: ' + str(local))
        raw = asset.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
        if item.get('sha256') != sha:
            raise ValueError('task input SHA mismatch: ' + item.get('id', ''))
        dest = 'inputs/' + sha + asset.suffix.lower()
        selected[dest] = raw; item['local_path'] = dest
    from production import asset_paths
    for item in record.get('media',[]):
        for field,media in asset_paths(item,source).items():
            raw=media.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            dest='media/'+sha+media.suffix.lower()
            selected[dest]=raw;item[field]=dest
    for preview in record.get('direction_previews', []):
        if preview.get('status') not in {'rendered', 'selected', 'rejected'}:
            continue
        name = preview.get('artifact', '')
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or '..' in Path(name).parts or Path(name).suffix.lower() not in {'.html', '.htm'}):
            raise ValueError('unsafe direction preview path')
        artifact = source / name
        if not artifact.is_file() or not artifact.resolve().is_relative_to(source):
            raise ValueError('missing direction preview artifact: '+name)
        raw = artifact.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
        if preview.get('html_sha256') != sha:
            raise ValueError('direction preview SHA mismatch: '+preview.get('id', ''))
        dest = 'previews/' + sha + artifact.suffix.lower()
        selected[dest] = raw; preview['artifact'] = dest
    selected['record.json']=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
    manifest={'schema':'qt-task-snapshot/1','files':{k:hashlib.sha256(v).hexdigest() for k,v in selected.items()},
              'notice':'Exact task files/source inputs/media/previews; approvals retained, not created. Does not freeze the Skill runtime.'}
    out.mkdir(parents=True)
    for name,raw in selected.items():
        f=out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
    (out/'snapshot.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    import argparse, hashlib, json
    from pathlib import Path
    from html_support import ROOT
    p=argparse.ArgumentParser(description='Initialize tasks, snapshot inputs/media, restore verified snapshots into new directories; never approves or generates.')
    sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--out',required=True,type=Path);init.add_argument('--id',required=True);init.add_argument('--title',required=True)
    snap=sub.add_parser('snapshot');snap.add_argument('task',type=Path);snap.add_argument('--out',required=True,type=Path)
    snap.add_argument('--files',nargs='+',default=['record.json','body.html'],help='Task-relative paths; always include record.json, body, custom CSS and current HTML as applicable')
    restore=sub.add_parser('restore');restore.add_argument('snapshot',type=Path);restore.add_argument('--out',required=True,type=Path)
    a=p.parse_args();out=a.out.resolve()
    if out.is_relative_to(ROOT) or out.exists():p.error('output must be a new directory outside Skill; never overwrites')
    try:
        if a.command=='init':
            out.mkdir(parents=True)
            record={'task':{'id':a.id,'title':a.title,'stage':'INTAKE','density':'explain','editorial_contract':1,'production_contract':2,'delivery_contract':1,'requirements_contract':1,'input_contract':1,'page_mode_contract':1,'page_mode':{'schema':'qt-page-mode/1','status':'pending','method':'pending','state':{'purpose':'','audience':'','next_action':'','material_types':[],'evidence_shapes':[],'content_scale':'','constraints':[]},'recommendation':{'primary':'','alternative':'','reasons':[],'risks':[],'confidence':None,'probabilities':{}},'selection':{'status':'pending','mode':'','evidence':{}}},'inputs':[],'modules':[],'sources':[],'media':[],'resources':[],'direction_previews':[],'approvals':[],'execution_authorizations':[],'feedback':[]}
            brief={'schema':'qt-requirements/1','review':{'status':'pending','context':[],'note':''},'assets':[]}
            raw=(json.dumps(brief,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            (out/'requirements.json').write_bytes(raw)
            record['task']['requirements_sha256']=hashlib.sha256(raw).hexdigest()
            record['requirement_bindings']={}
            (out/'record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (out/'body.html').write_text('<!-- Author modules after actual list confirmation; init grants no approvals. -->\n',encoding='utf-8')
            result={'stage':'INTAKE','approvals_created':0}
        elif a.command=='snapshot':result=task_bundle(a.task,out,a.files)
        else:
            folder=a.snapshot.resolve();manifest=json.loads((folder/'snapshot.json').read_text(encoding='utf-8'))
            if manifest.get('schema')!='qt-task-snapshot/1' or not manifest.get('files'):raise ValueError('invalid snapshot manifest')
            for name,sha in manifest['files'].items():
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('unsafe snapshot path')
                f=folder/name
                if not f.resolve().is_relative_to(folder) or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:raise ValueError('snapshot path/SHA mismatch: '+name)
            saved=json.loads((folder/'record.json').read_text(encoding='utf-8'))
            for item in saved.get('inputs', []):
                asset = item.get('local_path')
                if asset and (Path(asset).is_absolute() or asset not in manifest['files']):
                    raise ValueError('snapshot source input is not self-contained')
            for item in saved.get('media',[]):
                for field in ('local_path','original_path'):
                    asset=item.get(field)
                    if asset and (Path(asset).is_absolute() or asset not in manifest['files']):raise ValueError('snapshot media is not self-contained')
            for preview in saved.get('direction_previews', []):
                artifact = preview.get('artifact')
                if artifact and (Path(artifact).is_absolute() or artifact not in manifest['files']):
                    raise ValueError('snapshot direction preview is not self-contained')
            result=task_bundle(folder,out,list(manifest['files']))
        print(json.dumps({'output':str(out),**result},ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(1,'ERROR: '+str(e)+'\n')

if __name__=='__main__':main()
