#!/usr/bin/env python3
"""Validate catalog/original-document strategy and source-page mappings without rendering documents."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / 'assets' / 'document-viewer.json'


def catalog():
    data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    if data.get('schema') != 'qt-document-strategies/1' or not isinstance(data.get('strategies'), list):
        raise ValueError('invalid document strategy catalog')
    strategies = {item.get('id'): item for item in data['strategies']}
    if not strategies or len(strategies) != len(data['strategies']):
        raise ValueError('duplicate/empty document strategy catalog')
    return data, strategies


def _strings(value, label, nonempty=False):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{label} must be a list of nonempty strings')
    if nonempty and not value:
        raise ValueError(f'{label} must not be empty')


def validate_document_viewer(record, media_lookup=None, module_lookup=None, list_approved=None, require_decided=False):
    task = record.get('task', {})
    contract = task.get('document_viewer_contract')
    if contract is None:
        return {'status': 'legacy', 'strategy': None, 'documents': len(record.get('source_documents', []))}
    if type(contract) is not int or contract != 1:
        raise ValueError('document_viewer_contract must be 1 when supplied')
    _, strategies = catalog()
    decision = task.get('document_strategy')
    if not isinstance(decision, dict) or decision.get('schema') != 'qt-document-strategy/1':
        raise ValueError('task.document_strategy must use qt-document-strategy/1')
    status, mode = decision.get('status'), decision.get('mode')
    if status not in {'pending', 'selected', 'not-applicable'}:
        raise ValueError('invalid document strategy status')
    if not isinstance(decision.get('rationale', ''), str):
        raise ValueError('document strategy rationale must be text')
    scope = decision.get('documents')
    if not isinstance(scope, list) or len(scope) != len(set(scope)):
        raise ValueError('document strategy documents must be a unique list')
    if status == 'pending' and (mode or scope or decision.get('rationale')):
        raise ValueError('pending document strategy must not contain a decision')
    if status == 'not-applicable' and (mode or scope or not decision.get('rationale', '').strip()):
        raise ValueError('not-applicable strategy needs a rationale and empty mode/scope')
    if status == 'selected' and (mode not in strategies or not decision.get('rationale', '').strip()):
        raise ValueError('selected document strategy needs a known mode and rationale')
    if require_decided and status == 'pending':
        raise ValueError('decide document strategy before composing HTML')
    page_mode = task.get('page_mode', {}).get('selection', {}).get('mode')
    if require_decided and page_mode == 'catalog' and status != 'selected':
        raise ValueError('catalog page mode requires an explicit document strategy')

    documents = record.get('source_documents')
    if not isinstance(documents, list):
        raise ValueError('source_documents must be a list')
    inputs = {item.get('id') for item in record.get('inputs', []) if isinstance(item, dict)}
    found, page_ids = {}, set()
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError('each source document must be an object')
        ident = document.get('id', '')
        if not re.fullmatch(r'DOC-\d{2,}', ident) or ident in found:
            raise ValueError(f'invalid/duplicate source document ID: {ident}')
        found[ident] = document
        if document.get('schema') != 'qt-source-document/1':
            raise ValueError(f'{ident}: invalid schema')
        if not isinstance(document.get('revision'), int) or isinstance(document.get('revision'), bool) or document['revision'] < 1:
            raise ValueError(f'{ident}: positive revision required')
        if not str(document.get('title', '')).strip() or not re.fullmatch(r'M\d{2,}', document.get('module', '')):
            raise ValueError(f'{ident}: title and module are required')
        input_ids = document.get('input_ids')
        _strings(input_ids, f'{ident}.input_ids', nonempty=True)
        if any(input_id not in inputs for input_id in input_ids):
            raise ValueError(f'{ident}: unknown input reference')
        _strings(document.get('unread_scope'), f'{ident}.unread_scope')
        module = module_lookup.get(document['module']) if module_lookup is not None else None
        if module_lookup is not None and (not module or module.get('removed')):
            raise ValueError(f'{ident}: unknown/removed module')
        if list_approved and not list_approved(module):
            raise ValueError(f'{ident}: viewer module must be list-approved')
        pages = document.get('pages')
        if not isinstance(pages, list):
            raise ValueError(f'{ident}: pages must be a list')
        numbers = set()
        for page in pages:
            page_id = page.get('id', '') if isinstance(page, dict) else ''
            if not re.fullmatch(re.escape(ident) + r'-P\d{2,}', page_id) or page_id in page_ids:
                raise ValueError(f'{ident}: invalid/duplicate page ID {page_id}')
            page_ids.add(page_id)
            number = page.get('number')
            if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number in numbers:
                raise ValueError(f'{page_id}: positive unique page number required')
            numbers.add(number)
            if page.get('status') not in {'available', 'unavailable'} or not str(page.get('source_locator', '')).strip():
                raise ValueError(f'{page_id}: status and source_locator are required')
            media_id = page.get('media')
            if page['status'] == 'available':
                if not re.fullmatch(r'IMG-\d{2,}', str(media_id or '')):
                    raise ValueError(f'{page_id}: available page requires media')
                if media_lookup is not None:
                    media = media_lookup.get(media_id)
                    if not media or media.get('module') != document['module'] or media_id not in module.get('media', []):
                        raise ValueError(f'{page_id}: page media must belong to viewer module')
            elif media_id:
                raise ValueError(f'{page_id}: unavailable page cannot claim media')
    if any(ident not in found for ident in scope):
        raise ValueError('document strategy references an unknown source document')
    if status == 'selected' and strategies[mode]['requires_page_images']:
        if not scope or any(not found[ident].get('pages') for ident in scope):
            raise ValueError(f'{mode} requires scoped source documents with pages')
        if any(not any(page.get('status') == 'available' for page in found[ident]['pages']) for ident in scope):
            raise ValueError(f'{mode} requires at least one available page per scoped document')
    return {'status': status, 'strategy': mode or None, 'documents': len(documents), 'pages': len(page_ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--record', required=True, type=Path)
    validate.add_argument('--allow-pending', action='store_true')
    route = sub.add_parser('route')
    route.add_argument('--strategy', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'route':
            _, strategies = catalog()
            if args.strategy not in strategies:
                raise ValueError('unknown document strategy: ' + args.strategy)
            result = {'strategy': strategies[args.strategy], 'notice': 'Static presentation guidance only; no source document was read or rendered.'}
        else:
            record = json.loads(args.record.read_text(encoding='utf-8'))
            from record import approved, objects
            items = objects(record)
            result = validate_document_viewer(
                record,
                items['media'],
                items['modules'],
                lambda item: approved(record, 'list', 'modules', item),
                require_decided=not args.allow_pending,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
