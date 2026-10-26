#!/usr/bin/env python3
"""Read-only dependency and asset checks. Never installs or generates images."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def diagnose(browser=False):
    checks = []
    def add(name, passed, detail, required=True):
        checks.append({'id': name, 'status': 'pass' if passed else ('fail' if required else 'optional-missing'), 'detail': detail})
    add('python', sys.version_info >= (3, 9), '.'.join(map(str, sys.version_info[:3])))
    required = ['SKILL.md', 'package.json', 'package-lock.json', 'assets/provenance.json',
                'assets/templates/public-shell.html', 'assets/components/catalog.json',
                'assets/components/patterns.html', 'assets/components/topic.css', 'assets/components/topic.js',
                'references/workflow.md', 'references/visual-spec.md', 'references/content-record.md']
    missing = [name for name in required if not (ROOT / name).is_file()]
    add('files', not missing, {'missing': missing})
    try:
        text = (ROOT/'SKILL.md').read_text(encoding='utf-8')
        add('entry', text.startswith('---\nname: qingteng-topic-html\n') and 'description:' in text, 'Skill metadata')
        manifest = json.loads((ROOT/'assets/provenance.json').read_text(encoding='utf-8'))
        invalid = [a['file'] for a in manifest['assets'] if hashlib.sha256((ROOT/a['file']).read_bytes()).hexdigest() != a['sha256']]
        for svg in (ROOT/'assets').rglob('*.svg'):
            ET.parse(svg)
        add('assets', not invalid, {'checked': len(manifest['assets']), 'invalid': invalid})
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        add('assets', False, str(exc))
    node, npm = shutil.which('node'), shutil.which('npm')
    add('npm', bool(npm), 'available' if npm else 'Install Node.js LTS with npm for browser checks', browser)
    if not node:
        add('node', False, 'Browser checks require Node.js >=20; core Python tools remain available', browser)
    else:
        version = subprocess.run([node, '--version'], capture_output=True, text=True, encoding='utf-8', timeout=10).stdout.strip()
        try:
            valid = int(version.lstrip('v').split('.')[0]) >= 20
        except ValueError:
            valid = False
        add('node', valid, version or 'Unable to read Node version', browser)
        if browser and valid:
            probe = r"""
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(process.cwd()+'/package.json');
let engine;
try {
 const spec=process.env.QT_PLAYWRIGHT_MODULE||require.resolve('playwright');
 const loaded=await import(pathToFileURL(spec).href);
 const {chromium}=loaded.chromium?loaded:loaded.default;
 engine=await chromium.launch({headless:true,...(process.env.QT_CHROMIUM_EXECUTABLE?{executablePath:process.env.QT_CHROMIUM_EXECUTABLE}:{})});
 console.log(JSON.stringify({status:'pass',browser:engine.version(),source:process.env.QT_PLAYWRIGHT_MODULE?'explicit-override':'skill-local'}));
} catch(e) { console.log(JSON.stringify({status:'fail',error:String(e),remedy:'Run npm ci --ignore-scripts in the Skill folder, then npx --no-install playwright install chromium'}));process.exitCode=1; }
finally { if(engine)await engine.close(); }
"""
            p = subprocess.run([node, '--input-type=module', '-e', probe], cwd=ROOT,
                               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
            try:
                result = json.loads(p.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                result = {'error': p.stderr[-1000:] or 'Probe did not return JSON'}
            add('chromium-launch', p.returncode == 0, result)
    return {'status': 'fail' if any(c['status']=='fail' for c in checks) else 'pass',
            'mode': 'browser' if browser else 'core', 'checks': checks,
            'note': 'Core checks do not require Node. Browser mode actually launches Chromium. No installation or image generation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true', help='Require and launch the browser verification runtime')
    args = parser.parse_args()
    try:
        report = diagnose(args.browser)
    except (OSError, subprocess.TimeoutExpired) as exc:
        report = {'status':'fail','error':str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report['status'] != 'pass'

if __name__ == '__main__':
    sys.exit(main())
