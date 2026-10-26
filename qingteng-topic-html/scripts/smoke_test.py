#!/usr/bin/env python3
"""Synthetic first-run test outside the Skill; browser mode checks official online services."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run_case(out, browser=False):
    checks = []
    module = {'id':'M01','order':1,'revision':1,'list_version':'C01','draft_revision':1,'draft_version':'D01',
              'title':'首次运行检查','purpose':'验证安装后的工具与素材路径','points':['真实读取本Skill自己的模板'],
              'sources':[],'media':[],'required':True,'issues':[]}
    record = {'task':{'id':'synthetic-install-check','title':'安装验收 · 合成示例','stage':'DRAFT',
                      'density':'reference','list_version':'C01','draft_version':'D01'},
              'inputs':[],'modules':[module],'sources':[],'media':[],
              'approvals':[{'stage':'list','version':'C01','scope':{'modules':{'M01':1}},
                            'evidence':{'actor':'user','locator':'synthetic fixture, not real business consent','text':'仅授权本地无副作用安装测试'}}]}
    body = '<header data-module-id="M01" class="qt-t-paper qt-t-stack"><h1>安装验收 · 合成示例</h1><p>中文、路径空格与公共模板检查；没有真实业务或图片生成。</p><h2>完成条件</h2><p>页面可独立打开，拒绝越过清单确认。</p></header>'
    record_path, body_path = out/'record.json', out/'正文片段.html'
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    body_path.write_text(body, encoding='utf-8')
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONIOENCODING':'utf-8'}
    def execute(label, command, expected=0):
        p = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=180)
        passed = p.returncode == expected
        checks.append({'id':label,'status':'pass' if passed else 'fail','exit_code':p.returncode,
                       'stdout':p.stdout[-2500:],'stderr':p.stderr[-1000:]})
        return passed
    command = [sys.executable, str(ROOT/'scripts/compose_html.py'), '--record', str(record_path), '--body', str(body_path)]
    execute('draft-compose', command+['--mode','draft','--out',str(out/'draft.html')])
    denied = copy.deepcopy(record); denied['approvals'] = []
    denied_path = out/'unapproved.json'; denied_path.write_text(json.dumps(denied, ensure_ascii=False), encoding='utf-8')
    execute('unapproved-scope-denied', [sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(denied_path),
                                      '--body',str(body_path),'--out',str(out/'must-not-exist.html')], expected=1)
    checks.append({'id':'denied-output-absent','status':'pass' if not (out/'must-not-exist.html').exists() else 'fail'})
    record['task']['stage'] = 'DELIVERY'
    record['approvals'].append({'stage':'draft','version':'D01','scope':{'modules':{'M01':1}},
                               'evidence':{'actor':'user','locator':'synthetic fixture','text':'仅本地最终组合测试'}})
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    execute('final-compose', command+['--mode','final','--out',str(out/'final.html')])
    execute('final-static', [sys.executable,str(ROOT/'scripts/check_html.py'),str(out/'final.html'),
                             '--record',str(record_path),'--mode','final'])
    # Only the independent HTML is copied into this otherwise empty folder.
    standalone = out/'empty folder'; standalone.mkdir()
    if (out/'final.html').exists(): shutil.copy2(out/'final.html', standalone/'专题页.html')
    if browser:
        node = shutil.which('node')
        if not node:
            checks.append({'id':'official-header-browser','status':'fail','detail':'Node.js >=20 required; run doctor.py --browser'})
        else:
            execute('official-header-browser', [node,str(ROOT/'scripts/check_browser.mjs'),str(standalone/'专题页.html'),str(out/'browser')])
    return {'status':'fail' if any(c['status']=='fail' for c in checks) else 'pass', 'checks':checks,
            'browser_requested':browser,'image_generation_calls':0,
            'limits':['Synthetic approval is not business consent','Not a real-device or semantic workflow certification']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New empty output directory outside the installed Skill')
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    try:
        if args.out:
            out = args.out.resolve()
            if out.is_relative_to(ROOT) or (out.exists() and any(out.iterdir())):
                raise ValueError('Output must be a new or empty directory outside the Skill')
            out.mkdir(parents=True, exist_ok=True)
            report = run_case(out, args.browser)
            (out/'smoke-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        else:
            with tempfile.TemporaryDirectory(prefix='qingteng-install-check-') as tmp:
                report = run_case(Path(tmp), args.browser)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report['status'] != 'pass'
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'status':'fail','error':str(exc)}, ensure_ascii=False)); return 1

if __name__ == '__main__':
    sys.exit(main())
