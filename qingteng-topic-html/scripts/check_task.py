#!/usr/bin/env python3
"""Compose and check one immutable task round with self-contained inputs. Never generates."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

from html_support import ROOT
from record import task_bundle
from compose_html import compose
from production import audit_assets, AssetCache
from check_html import inspect, merge_browser, finish_report


def check_task(record_path, body_path, out, mode='final', css_path=None, browser=False, offline=False, review_path=None,
               profile='full', widths=None, modules=None, asset_cache_path=None, export=False):
    started = perf_counter(); timings = {}
    if profile not in {'preview', 'full'} or (profile == 'full' and modules):
        raise ValueError('full profile covers all modules; selection is preview-only')
    record_path = Path(record_path).resolve(); task = record_path.parent; out = Path(out).resolve()
    if record_path.name != 'record.json':
        raise ValueError('use the canonical record.json filename for self-contained rounds')
    if out.exists() or out.is_relative_to(ROOT) or out == task or out.is_relative_to(task):
        raise ValueError('round output must be new and outside the source task and Skill; use a sibling runs directory')
    paths = [record_path, Path(body_path).resolve()] + ([Path(css_path).resolve()] if css_path else [])
    if any(not p.is_file() or not p.is_relative_to(task) for p in paths):
        raise ValueError('record/body/CSS must be saved files within the source task')
    names = [str(p.relative_to(task)) for p in paths]
    out.mkdir(parents=True)
    bundle = task_bundle(task, out / 'inputs', names)
    timings['snapshot_ms'] = (perf_counter()-started)*1000
    (out / 'record-original.json').write_bytes(record_path.read_bytes())
    saved = out / 'inputs'; record = json.loads((saved / 'record.json').read_text(encoding='utf-8'))
    report = {'status': 'fail', 'production_status': 'fail', 'completion_status': 'not-run', 'errors': [],
              'business_information': {'status': 'unknown', 'reason': 'composition has not completed'},
              'user_acceptance': {'status': 'unknown', 'reason': 'exact-artifact user decision not supplied'}}
    try:
        cache = AssetCache(asset_cache_path); phase = perf_counter()
        html = compose(record, (saved / names[1]).read_text(encoding='utf-8'), mode, saved,
                       (saved / names[2]).read_text(encoding='utf-8') if css_path else '', asset_cache=cache)
        timings['compose_ms'] = (perf_counter()-phase)*1000; phase = perf_counter()
        (out / 'page.html').write_text(html, encoding='utf-8')
        assets = audit_assets(record, saved, mode, cache=cache)
        (out / 'assets.json').write_text(json.dumps(assets, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        timings['asset_recheck_ms'] = (perf_counter()-phase)*1000
        if export:
            from export_media import export_media
            export_media(out/'page.html', out/'media-export')
        review = None
        if review_path:
            review_path = Path(review_path).resolve(); review = json.loads(review_path.read_text(encoding='utf-8'))
            for shot in review.get('layers', {}).get('visual', {}).get('screenshots', []):
                p = Path(shot['path']); p = p if p.is_absolute() else review_path.parent / p
                raw = p.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
                if sha != shot['sha256']:
                    raise ValueError('supplied review screenshot SHA mismatch')
                relative = 'review-assets/' + sha + p.suffix.lower()
                (out / relative).parent.mkdir(exist_ok=True); (out / relative).write_bytes(raw)
                shot['path'] = relative
            (out / 'manual-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report = inspect(html, mode, record, review, out, saved)
        if browser:
            phase = perf_counter()
            node = shutil.which('node')
            if not node:
                raise ValueError('Node is unavailable; no browser execution was performed')
            command = [node, str(ROOT / 'scripts/check_browser.mjs'), str(out / 'page.html'), str(out / 'browser')]
            command += ['--profile', profile]
            if widths:
                command += ['--widths', ','.join(map(str,widths))]
            if modules:
                command += ['--modules', ','.join(modules)]
            if offline:
                command.append('--offline')
            result = subprocess.run(command, capture_output=True, text=True)
            (out / 'browser-command.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
            browser_report = out / 'browser/report.json'
            if not browser_report.is_file():
                raise ValueError('browser command did not create its report')
            merge_browser(report, json.loads(browser_report.read_text(encoding='utf-8')), browser_report.parent)
            timings['browser_ms'] = (perf_counter()-phase)*1000
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report['errors'].append(str(exc)); report['status'] = 'fail'; report['completion_status'] = 'fail'
    if 'layers' in report:
        finish_report(report)
    report['run_profile'] = profile
    if profile == 'preview' and report.get('completion_status') != 'fail':
        report['completion_status'] = 'not-run'
    timings['total_ms'] = (perf_counter()-started)*1000
    report['production_metrics'] = {'timings': timings,
        'snapshot_bytes': sum(p.stat().st_size for p in saved.rglob('*') if p.is_file()),
        'html_bytes': (out/'page.html').stat().st_size if (out/'page.html').is_file() else 0,
        'cache': {'png_hits': cache.hits, 'png_misses': cache.misses} if 'cache' in locals() else None,
        'scope': 'Byte inspection cache only; current HTML/browser and human decisions are never reused.'}
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'schema': 'qt-check-round/1', 'mode': mode, 'inputs': 'inputs/snapshot.json',
                'html_sha256': report.get('html_sha256'), 'input_files': len(bundle['files']),
                'files': {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in out.rglob('*') if p.is_file()},
                'notice': 'One saved round; executor reviews and user approval are distinct. No generator invoked.'}
    (out / 'round.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--record', type=Path, required=True); p.add_argument('--body', type=Path, required=True)
    p.add_argument('--subject-css', type=Path); p.add_argument('--mode', choices=['draft', 'refine', 'final'], default='final')
    p.add_argument('--out-dir', type=Path, required=True); p.add_argument('--browser', action='store_true')
    p.add_argument('--offline', action='store_true'); p.add_argument('--review', type=Path)
    p.add_argument('--profile', choices=['preview','full'], default='full')
    p.add_argument('--widths', type=int, nargs='+'); p.add_argument('--modules', nargs='+')
    p.add_argument('--asset-cache', type=Path); p.add_argument('--export-media', action='store_true')
    a = p.parse_args()
    if a.offline and not a.browser:
        p.error('--offline requires --browser')
    try:
        result = check_task(a.record, a.body, a.out_dir, a.mode, a.subject_css, a.browser, a.offline, a.review,
                            a.profile, a.widths, a.modules, a.asset_cache, a.export_media)
    except (ValueError, OSError) as exc:
        p.exit(1, 'ERROR: ' + str(exc) + '\n')
    print(json.dumps({k: result.get(k) for k in ('status', 'production_status', 'asset_fulfillment', 'business_information', 'user_acceptance', 'completion_status', 'html_sha256', 'errors')}, ensure_ascii=False))
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    raise SystemExit(main())
