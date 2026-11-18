#!/usr/bin/env python3
"""Validate multi-format input inventory and honest read scopes; never parses or fetches content."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / 'assets' / 'input-sources.json'


def catalog():
    data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    if data.get('schema') != 'qt-input-adapters/1' or not isinstance(data.get('adapters'), list):
        raise ValueError('invalid input adapter catalog')
    adapters = {item.get('kind'): item for item in data['adapters']}
    if not adapters or len(adapters) != len(data['adapters']):
        raise ValueError('duplicate/empty input adapter catalog')
    return data, adapters


def _strings(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{label} must be a list of nonempty strings')


def _sha(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError(f'{label} requires lowercase sha256')


def validate_inputs(record, require_read=False, task_dir=None):
    task = record.get('task', {})
    contract = task.get('input_contract')
    if contract is None:
        return {'status': 'legacy', 'inputs': len(record.get('inputs', []))}
    if type(contract) is not int or contract != 1:
        raise ValueError('input_contract must be 1 when supplied')
    data, adapters = catalog()
    inputs = record.get('inputs')
    if not isinstance(inputs, list):
        raise ValueError('inputs must be a list')
    if require_read and not inputs:
        raise ValueError('at least one recorded input is required before composing HTML')
    found = set()
    summary = {status: 0 for status in data['statuses']}
    base = Path(task_dir).resolve() if task_dir else None
    for item in inputs:
        if not isinstance(item, dict):
            raise ValueError('each input must be an object')
        ident = item.get('id', '')
        if not re.fullmatch(r'A\d{2,}', ident) or ident in found:
            raise ValueError(f'invalid/duplicate input ID: {ident}')
        found.add(ident)
        if item.get('schema') != 'qt-input-source/1' or item.get('kind') not in adapters:
            raise ValueError(f'{ident}: invalid schema/kind')
        if not isinstance(item.get('revision'), int) or isinstance(item.get('revision'), bool) or item['revision'] < 1:
            raise ValueError(f'{ident}: positive revision required')
        if not isinstance(item.get('locator'), str) or not item['locator'].strip():
            raise ValueError(f'{ident}: locator is required')
        if not isinstance(item.get('original_name', ''), str):
            raise ValueError(f'{ident}: original_name must be text')
        extraction = item.get('extraction')
        if not isinstance(extraction, dict):
            raise ValueError(f'{ident}: extraction object is required')
        status, method = extraction.get('status'), extraction.get('method')
        if status not in data['statuses'] or method not in data['methods']:
            raise ValueError(f'{ident}: invalid extraction status/method')
        if method == 'pending' and status != 'not-run':
            raise ValueError(f'{ident}: pending method is only valid before reading')
        if method != 'pending' and method not in adapters[item['kind']]['methods']:
            raise ValueError(f'{ident}: {method} is not declared for {item["kind"]}')
        for key in ('read_scope', 'unread_scope', 'structure_loss', 'errors'):
            _strings(extraction.get(key), f'{ident}.extraction.{key}')
        if extraction.get('media_status') not in data['media_statuses']:
            raise ValueError(f'{ident}: invalid media_status')
        read_scope, unread_scope, errors = (extraction[key] for key in ('read_scope', 'unread_scope', 'errors'))
        if status == 'complete' and (not read_scope or unread_scope or errors):
            raise ValueError(f'{ident}: complete means read scope present with no unread scope/errors')
        if status == 'partial' and (not read_scope or not unread_scope):
            raise ValueError(f'{ident}: partial requires both read and unread scope')
        if status == 'blocked' and (not unread_scope or not errors):
            raise ValueError(f'{ident}: blocked requires unread scope and errors')
        if status == 'not-run' and (method != 'pending' or read_scope or not unread_scope):
            raise ValueError(f'{ident}: not-run requires pending method, empty read scope and planned unread scope')
        if require_read and status == 'not-run':
            raise ValueError(f'{ident}: input reading has not run')
        attachments = extraction.get('attachments')
        if not isinstance(attachments, list):
            raise ValueError(f'{ident}: attachments must be a list')
        attachment_ids = set()
        for attachment in attachments:
            aid = attachment.get('id', '') if isinstance(attachment, dict) else ''
            if not re.fullmatch(re.escape(ident) + r'-ATT-\d{2,}', aid) or aid in attachment_ids:
                raise ValueError(f'{ident}: invalid/duplicate attachment ID {aid}')
            attachment_ids.add(aid)
            if attachment.get('status') not in data['attachment_statuses'] or not str(attachment.get('locator', '')).strip():
                raise ValueError(f'{aid}: status and locator are required')
        local = item.get('local_path')
        if local:
            _sha(item.get('sha256'), f'{ident}.sha256')
            if base:
                path = Path(local)
                path = path if path.is_absolute() else base / path
                path = path.resolve()
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError(f'{ident}: local input missing or SHA mismatch')
        elif item.get('sha256'):
            _sha(item['sha256'], f'{ident}.sha256')
        summary[status] += 1
    return {'status': 'validated', 'inputs': len(inputs), 'extraction': summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--record', required=True, type=Path)
    validate.add_argument('--allow-not-run', action='store_true')
    inventory = sub.add_parser('inventory')
    inventory.add_argument('--record', required=True, type=Path)
    route = sub.add_parser('route')
    route.add_argument('--kind', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'route':
            _, adapters = catalog()
            if args.kind not in adapters:
                raise ValueError('unknown input kind: ' + args.kind)
            result = {'adapter': adapters[args.kind], 'notice': 'Host routing guidance only; no parser or connector was called.'}
        else:
            record_path = args.record.resolve()
            record = json.loads(record_path.read_text(encoding='utf-8'))
            require_read = args.command == 'validate' and not args.allow_not_run
            result = validate_inputs(record, require_read=require_read, task_dir=record_path.parent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
