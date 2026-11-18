#!/usr/bin/env python3
"""Validate page-mode recommendations and direction previews without mutation or AI calls."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / 'assets' / 'page-modes.json'
STATE_TEXT = ('purpose', 'audience', 'next_action', 'content_scale')
STATE_LISTS = ('material_types', 'evidence_shapes', 'constraints')
METHODS = {'pending', 'executor', 'typesafe', 'user'}
STATUSES = {'pending', 'recommended', 'selected'}
PREVIEW_STATUSES = {'planned', 'rendered', 'selected', 'rejected'}


def catalog():
    data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    if data.get('schema') != 'qt-page-modes/1' or not isinstance(data.get('modes'), list):
        raise ValueError('invalid page mode catalog')
    modes = {item.get('id'): item for item in data['modes']}
    if len(modes) != len(data['modes']) or not modes:
        raise ValueError('duplicate/empty page mode catalog')
    return data, modes


def _evidence(value, label):
    if not isinstance(value, dict) or value.get('actor') != 'user' or not value.get('locator') or not str(value.get('text', '')).strip():
        raise ValueError(f'{label} requires real user evidence')


def _sha(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError(f'{label} requires lowercase sha256')


def validate_page_mode(record, module_lookup=None, list_approved=None, require_selected=False, task_dir=None):
    task = record.get('task', {})
    contract = task.get('page_mode_contract')
    if contract is None:
        return {'status': 'legacy', 'selected': None, 'mapping': None}
    if type(contract) is not int or contract != 1:
        raise ValueError('page_mode_contract must be 1 when supplied')
    data, modes = catalog()
    page = task.get('page_mode')
    if not isinstance(page, dict) or page.get('schema') != 'qt-page-mode/1':
        raise ValueError('task.page_mode must use qt-page-mode/1')
    status = page.get('status')
    method = page.get('method')
    if status not in STATUSES or method not in METHODS:
        raise ValueError('invalid page mode status/method')
    state = page.get('state')
    recommendation = page.get('recommendation')
    selection = page.get('selection')
    if not isinstance(state, dict) or not isinstance(recommendation, dict) or not isinstance(selection, dict):
        raise ValueError('page mode state/recommendation/selection must be objects')

    if status != 'pending':
        if method == 'pending':
            raise ValueError('completed page mode recommendation needs a method')
        for key in STATE_TEXT:
            if not isinstance(state.get(key), str) or not state[key].strip():
                raise ValueError(f'page mode state.{key} is required')
        for key in STATE_LISTS:
            if not isinstance(state.get(key), list):
                raise ValueError(f'page mode state.{key} must be a list')
        primary = recommendation.get('primary')
        alternative = recommendation.get('alternative')
        if primary not in modes or (alternative and alternative not in modes) or alternative == primary:
            raise ValueError('invalid primary/alternative page mode')
        if not isinstance(recommendation.get('reasons'), list) or not recommendation['reasons']:
            raise ValueError('page mode recommendation needs reasons')
        if not isinstance(recommendation.get('risks'), list):
            raise ValueError('page mode recommendation needs a risks list')
        confidence = recommendation.get('confidence')
        if confidence is not None and (not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1):
            raise ValueError('page mode confidence must be null or 0..1')
        probabilities = recommendation.get('probabilities', {})
        if not isinstance(probabilities, dict) or any(k not in modes or not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1 for k, v in probabilities.items()):
            raise ValueError('page mode probabilities must map known modes to 0..1')
        if probabilities and (primary not in probabilities or abs(sum(probabilities.values()) - 1) > 0.02):
            raise ValueError('page mode probabilities must include primary and sum to about 1')
        if method == 'typesafe' and (confidence is None or not probabilities):
            raise ValueError('typesafe recommendations must retain confidence and probabilities')

    selected = selection.get('mode')
    selected_status = selection.get('status')
    if selected_status not in {'pending', 'selected'}:
        raise ValueError('page mode selection status must be pending/selected')
    if selected_status == 'selected':
        if selected not in modes:
            raise ValueError('selected page mode is unknown')
        _evidence(selection.get('evidence'), 'page mode selection')
        if status != 'selected':
            raise ValueError('task.page_mode.status must be selected after selection')
    elif selected:
        raise ValueError('pending page mode selection cannot name a mode')
    if require_selected and selected_status != 'selected':
        raise ValueError('select page mode before composing HTML')

    previews = record.get('direction_previews', [])
    if not isinstance(previews, list) or len(previews) > data.get('preview_policy', {}).get('max_directions', 2):
        raise ValueError('direction_previews must be a list with at most two entries')
    seen = set()
    base = Path(task_dir).resolve() if task_dir else None
    for preview in previews:
        ident = preview.get('id', '')
        if not re.fullmatch(r'PV-\d{2,}', ident) or ident in seen:
            raise ValueError(f'invalid/duplicate direction preview ID: {ident}')
        seen.add(ident)
        if preview.get('mode') not in modes or preview.get('status') not in PREVIEW_STATUSES:
            raise ValueError(f'{ident}: invalid mode/status')
        module_ids = preview.get('modules')
        if not isinstance(module_ids, list) or not module_ids or len(module_ids) != len(set(module_ids)):
            raise ValueError(f'{ident}: nonempty unique module scope required')
        if module_lookup is not None:
            for module_id in module_ids:
                item = module_lookup.get(module_id)
                if not item or item.get('removed'):
                    raise ValueError(f'{ident}: unknown/removed module {module_id}')
                if list_approved and not list_approved(item):
                    raise ValueError(f'{ident}: preview requires list-approved module {module_id}')
        if preview['status'] in {'rendered', 'selected', 'rejected'}:
            artifact = preview.get('artifact')
            _sha(preview.get('html_sha256'), f'{ident} artifact')
            if (not isinstance(artifact, str) or not artifact or Path(artifact).is_absolute()
                    or '..' in Path(artifact).parts or Path(artifact).suffix.lower() not in {'.html', '.htm'}):
                raise ValueError(f'{ident}: rendered preview needs a safe task-relative artifact')
            if base:
                path = (base / artifact).resolve()
                if not path.is_relative_to(base) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != preview['html_sha256']:
                    raise ValueError(f'{ident}: preview artifact missing or SHA mismatch')
        if preview['status'] in {'selected', 'rejected'}:
            _evidence(preview.get('evidence'), f'{ident} decision')
    mapping = modes.get(selected) if selected else None
    return {'status': status, 'selected': selected, 'mapping': mapping, 'previews': len(previews)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'brief'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--record', required=True, type=Path)
        cmd.add_argument('--allow-pending', action='store_true')
    args = parser.parse_args()
    try:
        record_path = args.record.resolve()
        record = json.loads(record_path.read_text(encoding='utf-8'))
        from record import approved, objects
        modules = objects(record)['modules']
        result = validate_page_mode(
            record,
            modules,
            lambda item: approved(record, 'list', 'modules', item),
            require_selected=not args.allow_pending,
            task_dir=record_path.parent,
        )
        if args.command == 'brief' and result.get('mapping'):
            result = {'selected': result['selected'], 'mapping': result['mapping'], 'notice': 'Static mapping only; recommendation and user selection remain separate evidence.'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
