#!/usr/bin/env python3
"""Synthetic first-run test outside the Skill; browser mode checks official online services."""
import argparse
import copy
import hashlib
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
    module.update(reader_question='安装后能否独立组合与拒绝越权？',key_message='安装文件可独立运行',
                  content_layers={'primary':'首次运行检查','support':'模板和依赖','evidence':'合成本地自检结果','conditions':'不代表业务验收'},
                  deduplication='仅一个自检模块，无重复',relationship='核对与完成条件',
                  visual_intent={'focus':'完成条件','order':'说明→核对','web':'紧凑资料','h5':'正文先读'})
    page_mode={'schema':'qt-page-mode/1','status':'selected','method':'user',
               'state':{'purpose':'验证安装后的独立组合与权限拒绝','audience':'Skill维护者','next_action':'核对自检结果',
                        'material_types':['合成文本'],'evidence_shapes':['核对项'],'content_scale':'单模块合成自检','constraints':['不代表业务验收']},
               'recommendation':{'primary':'report','alternative':'operations','reasons':['以核对结果和边界为主'],
                                 'risks':['合成材料不能代表真实专题语义质量'],'confidence':None,'probabilities':{}},
               'selection':{'status':'selected','mode':'report','evidence':{'actor':'user','locator':'synthetic fixture','text':'仅本地无副作用安装测试使用报告阅读模式'}}}
    record = {'task':{'id':'synthetic-install-check','title':'安装验收 · 合成示例','stage':'DRAFT',
                      'density':'reference','editorial_contract':1,'input_contract':1,'page_mode_contract':1,'page_mode':page_mode,
                      'document_viewer_contract':1,'document_strategy':{'schema':'qt-document-strategy/1','status':'not-applicable','mode':'','rationale':'合成安装检查没有原稿材料','documents':[]},
                      'list_version':'C01','draft_version':'D01'},
              'inputs':[{'id':'A01','schema':'qt-input-source/1','revision':1,'kind':'text','locator':'synthetic fixture','original_name':'',
                         'extraction':{'status':'complete','method':'direct','read_scope':['合成测试主题全文'],'unread_scope':[],
                                       'structure_loss':[],'media_status':'not-applicable','attachments':[],'errors':[]}}],
              'modules':[module],'sources':[],'media':[],'source_documents':[],
              'direction_previews':[],
              'approvals':[{'stage':'list','version':'C01','scope':{'modules':{'M01':1}},
                            'evidence':{'actor':'user','locator':'synthetic fixture, not real business consent','text':'仅授权本地无副作用安装测试'}}]}
    body = '<header data-module-id="M01" class="qt-t-paper qt-t-stack"><h1>安装验收 · 合成示例</h1><p>中文、路径空格与公共模板检查；没有真实业务或图片生成。</p><h2>完成条件</h2><p>页面可独立打开，拒绝越过清单确认。</p></header>'
    source={'id':'S-INPUT-01','revision':1,'list_version':'C01','draft_version':'D01','kind':'input','title':'合成自检说明',
            'verification':'unverified','adoption':'adopted','citation_mode':'attributed-input','reading':'checked',
            'read_scope':'本地合成说明全文','claim_scope':'attributed','public_note':'据合成自检说明；不代表独立业务事实核验。'}
    record['sources']=[source];module['sources']=['S-INPUT-01'];record['approvals'][0]['scope']['sources']={'S-INPUT-01':1}
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
    pending_mode = copy.deepcopy(record)
    pending_mode['task']['page_mode'] = {'schema':'qt-page-mode/1','status':'pending','method':'pending',
        'state':{'purpose':'','audience':'','next_action':'','material_types':[],'evidence_shapes':[],'content_scale':'','constraints':[]},
        'recommendation':{'primary':'','alternative':'','reasons':[],'risks':[],'confidence':None,'probabilities':{}},
        'selection':{'status':'pending','mode':'','evidence':{}}}
    pending_path = out/'pending-mode.json'; pending_path.write_text(json.dumps(pending_mode, ensure_ascii=False), encoding='utf-8')
    execute('pending-page-mode-denied', [sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(pending_path),
                                         '--body',str(body_path),'--out',str(out/'must-not-route.html')], expected=1)
    checks.append({'id':'pending-mode-output-absent','status':'pass' if not (out/'must-not-route.html').exists() else 'fail'})
    pending_input = copy.deepcopy(record); pending_input['inputs'][0]['extraction']={'status':'not-run','method':'pending','read_scope':[],
        'unread_scope':['尚未读取合成输入'],'structure_loss':[],'media_status':'unread','attachments':[],'errors':[]}
    pending_input_path = out/'pending-input.json'; pending_input_path.write_text(json.dumps(pending_input, ensure_ascii=False), encoding='utf-8')
    execute('pending-input-denied', [sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(pending_input_path),
                                     '--body',str(body_path),'--out',str(out/'must-not-read.html')], expected=1)
    checks.append({'id':'pending-input-output-absent','status':'pass' if not (out/'must-not-read.html').exists() else 'fail'})
    pending_document = copy.deepcopy(record); pending_document['task']['document_strategy']={'schema':'qt-document-strategy/1','status':'pending','mode':'','rationale':'','documents':[]}
    pending_document_path = out/'pending-document.json'; pending_document_path.write_text(json.dumps(pending_document, ensure_ascii=False), encoding='utf-8')
    execute('pending-document-strategy-denied', [sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(pending_document_path),
                                               '--body',str(body_path),'--out',str(out/'must-not-view.html')], expected=1)
    checks.append({'id':'pending-document-output-absent','status':'pass' if not (out/'must-not-view.html').exists() else 'fail'})
    legacy = copy.deepcopy(record); legacy['task'].pop('page_mode_contract'); legacy['task'].pop('page_mode'); legacy['task'].pop('input_contract'); legacy['task'].pop('document_viewer_contract'); legacy['task'].pop('document_strategy')
    legacy['inputs']=[{'id':'A01','kind':'text','locator':'synthetic fixture','read_scope':'合成全文','unread_scope':'无'}]
    legacy_path = out/'legacy-record.json'; legacy_path.write_text(json.dumps(legacy, ensure_ascii=False), encoding='utf-8')
    execute('legacy-record-compatible', [sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(legacy_path),
                                         '--body',str(body_path),'--out',str(out/'legacy-draft.html')])
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
    final_static_report = out/'final-static-report.json'
    execute('final-static', [sys.executable,str(ROOT/'scripts/check_html.py'),str(out/'final.html'),
                             '--record',str(record_path),'--mode','final','--report',str(final_static_report)])
    final_static = json.loads(final_static_report.read_text(encoding='utf-8')) if final_static_report.is_file() else {}
    exact_sha = hashlib.sha256((out/'final.html').read_bytes()).hexdigest() if (out/'final.html').is_file() else ''
    checks.append({'id':'exact-file-byte-identity','status':'pass' if final_static.get('html_sha256')==exact_sha else 'fail'})
    execute('incomplete-candidate-not-deliverable', [sys.executable,str(ROOT/'scripts/check_html.py'),str(out/'final.html'),
                                                     '--record',str(record_path),'--mode','final','--require-complete'], expected=1)
    version=json.loads((ROOT/'assets/provenance.json').read_text(encoding='utf-8'))['version']
    final_html=(out/'final.html').read_text(encoding='utf-8') if (out/'final.html').is_file() else ''
    checks.append({'id':'current-composer-identity','status':'pass' if f'content="qingteng-topic-html/{version}"' in final_html and 'data-qt-mode="final"' in final_html else 'fail'})
    stale=out/'stale-artifact.html'
    stale.write_text(final_html.replace(f'qingteng-topic-html/{version}','qingteng-topic-html/0.0.0',1),encoding='utf-8')
    execute('stale-composer-identity-denied',[sys.executable,str(ROOT/'scripts/check_html.py'),str(stale),
                                             '--record',str(record_path),'--mode','final'],expected=1)
    missing=out/'missing-local-asset.html'
    missing.write_text(final_html.replace('</main>','<img src="assets/missing.png" alt="缺失素材"></main>',1),encoding='utf-8')
    execute('relative-final-asset-denied',[sys.executable,str(ROOT/'scripts/check_html.py'),str(missing),
                                          '--record',str(record_path),'--mode','final'],expected=1)
    custom=out/'custom-video.html'
    custom.write_text(body.replace('</header>','<aside class="custom-video-notice">视频待提供，当前不可播放。</aside></header>'),encoding='utf-8')
    execute('custom-resource-final-denied',[sys.executable,str(ROOT/'scripts/compose_html.py'),'--record',str(record_path),
                                           '--body',str(custom),'--mode','final','--out',str(out/'must-not-final.html')],expected=1)
    checks.append({'id':'resource-denied-output-absent','status':'pass' if not (out/'must-not-final.html').exists() else 'fail'})
    # Only the independent HTML is copied into this otherwise empty folder.
    standalone = out/'empty folder'; standalone.mkdir()
    if (out/'final.html').exists(): shutil.copy2(out/'final.html', standalone/'专题页.html')
    execute('standalone-final-static',[sys.executable,str(ROOT/'scripts/check_html.py'),str(standalone/'专题页.html'),
                                      '--record',str(record_path),'--mode','final'])
    if browser:
        node = shutil.which('node')
        if not node:
            checks.append({'id':'official-header-browser','status':'fail','detail':'Node.js >=20 required; run doctor.py --browser'})
        else:
            execute('official-header-browser', [node,str(ROOT/'scripts/check_browser.mjs'),str(standalone/'专题页.html'),str(out/'browser')])
    return {'skill_version':json.loads((ROOT/'assets/provenance.json').read_text(encoding='utf-8'))['version'],'status':'fail' if any(c['status']=='fail' for c in checks) else 'pass', 'checks':checks,
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
