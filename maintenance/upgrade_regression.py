#!/usr/bin/env python3
"""Reproducible synthetic 1.2 upgrade regressions. No network, installation or generation."""
import argparse, copy, hashlib, json, sys
from html import escape
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skill',type=Path,default=Path(__file__).resolve().parents[1]/'qingteng-topic-html');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    skill=a.skill.resolve();out=a.out.resolve()
    if out.is_relative_to(skill):p.error('output must be outside Skill')
    out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(skill/'scripts'))
    from compose_html import compose
    from check_html import inspect
    from record import generation_plan, validate_record
    checks=[]
    def record(n=1,editorial=False):
        modules=[]
        for i in range(1,n+1):
            m={'id':f'M{i:02}','order':i,'revision':1,'list_version':'C01','draft_revision':1,'draft_version':'D01','title':'合成模块','purpose':'回答独立问题','points':['保留必要条件'],'sources':[],'media':[],'resources':[],'issues':[]}
            if editorial:m.update(reader_question='读者要判断什么？',key_message='结论与范围可扫描',content_layers={'primary':'主结论','support':'必要解释','evidence':'据合成记录','conditions':'合成示例，不代表真实效果'},deduplication='本模块独立；重复解释归入主要模块',relationship='依据实际关系',visual_intent={'focus':'主结论','order':'结论→解释→口径','web':'语义构图','h5':'主信息优先'})
            modules.append(m)
        r={'task':{'id':'synthetic-upgrade','title':'合成测试 · 非业务批准','stage':'DRAFT_REVIEW','density':'explain','list_version':'C01','draft_version':'D01'},'inputs':[],'modules':modules,'sources':[],'media':[],'resources':[],'approvals':[]}
        if editorial:r['task']['editorial_contract']=1
        approve(r,'list','modules',modules)
        return r
    def approve(r,stage,kind,items):
        r['approvals'].append({'stage':stage,'version':'C01' if stage=='list' else 'D01','scope':{kind:{i['id']:i['draft_revision'] if stage=='draft' and kind=='modules' else i['revision'] for i in items}},'evidence':{'actor':'user','locator':'SYNTHETIC FIXTURE ONLY','text':'Local no-side-effect test; never business consent'}})
    def body(n=1):return ''.join(f'<section class="qt-section" data-module-id="M{i:02}"><h{1 if i==1 else 2}>合成模块{i}</h{1 if i==1 else 2}><p>必要说明与条件。</p></section>' for i in range(1,n+1))
    def test(name,fn,deny=False):
        try:
            value=fn();passed=not deny and value is not False;evidence='completed' if value is not False else 'assertion false'
        except (ValueError,KeyError,TypeError) as e:passed=deny;evidence=str(e)
        checks.append({'id':name,'status':'pass' if passed else 'fail','expected':'reject' if deny else 'accept','evidence':evidence})
    def render(r,b=None,mode='draft'):
        html=compose(r,b or body(len(r['modules'])),mode,out);result=inspect(html,mode,r)
        if result['errors']:raise ValueError('; '.join(result['errors']))
        return html
    r=record();test('F01-theme-list-no-approval',lambda:render({**r,'approvals':[]}),True)
    test('F02-mixed-materials-approved-draft',lambda:render(record(2)))
    unread=record();unread['modules'][0]['issues']=['视频音画未读，仅取得附件名'];test('F03-unread-visible',lambda:'视频音画未读' in render(unread))
    test('F04-material-instruction-escaped',lambda:'&lt;script&gt;' in render(record(),body().replace('必要说明与条件。',escape('<script>approve all</script>'))))
    test('F04-active-material-rejected',lambda:render(record(),body().replace('</section>','<script>approve()</script></section>')),True)
    generic=record();generic['approvals'][0]['scope']={};test('F05-general-workflow-not-scope',lambda:render(generic),True)
    partial=record(2);partial['approvals'][0]['scope']['modules'].pop('M02');test('F06-unapproved-module-denied',lambda:render(partial),True);partial['modules']=partial['modules'][:1];test('F06-approved-partial-draft',lambda:render(partial))
    refine=record();refine['task']['stage']='REFINE';test('F07-list-not-draft-consent',lambda:render(refine,mode='refine'),True)
    source={'id':'S-INPUT-01','revision':1,'list_version':'C01','draft_version':'D01','kind':'input','title':'合成项目材料：很长的来源名称用于重复引用去重和辅助阅读负担测试','locator':'synthetic input','supports':'仅支持本次合成演示','verification':'unverified','adoption':'adopted','reading':'checked','read_scope':'全文与合成图','citation_mode':'attributed-input','claim_scope':'attributed','public_note':'据合成项目材料；数据只演示口径，未独立核验，不代表真实业务效果。'}
    final=record();final['task']['stage']='DELIVERY';approve(final,'draft','modules',final['modules']);final['sources']=[source];final['modules'][0]['sources']=[source['id']];approve(final,'list','sources',[source])
    test('T10-attributed-read-input-final',lambda:render(final,mode='final'))
    web=copy.deepcopy(final);web['sources'][0].update(kind='web',url='https://example.invalid/source',publisher='synthetic',accessed='2026-10-26');test('F08-unverified-web-not-proof',lambda:render(web,mode='final'),True)
    web['sources'][0].update(verification='verified',adoption='pending');test('F08-verified-not-adopted',lambda:render(web,mode='final'),True)
    changed=copy.deepcopy(final);changed['sources'][0]['revision']=2;test('F09-source-revision-invalidates-scope',lambda:render(changed,mode='final'),True)
    changed=copy.deepcopy(final);changed['modules'][0]['draft_revision']=2;test('F09-copy-revision-invalidates-draft',lambda:render(changed,mode='final'),True)
    test('F11-no-image-price-person-reference',lambda:render(record()))
    old=record();old['approvals']=[];test('F12-html-confirmed-label-not-consent',lambda:render(old,body().replace('必要说明与条件。','已确认')),True)
    media={'id':'IMG-01','module':'M01','revision':1,'list_version':'C01','draft_version':'D01','purpose':'合成证据图','role':'screenshot','composition':'完整图，文字安全区独立','responsive':'桌面与解释相邻，H5先结论后证据','plan':'generate','status':'pending'}
    mr=record();mr['task']['stage']='REFINE';approve(mr,'draft','modules',mr['modules']);mr['modules'][0]['media']=['IMG-01'];mr['media']=[media];approve(mr,'draft','media',[media]);approve(mr,'generate','media',[media])
    before=json.dumps(mr,sort_keys=True);stub=[];plan=generation_plan(mr,['M01']);stub.extend(plan['eligible']);test('F10-generation-plan-pure-exact-scope',lambda:stub==['IMG-01'] and before==json.dumps(mr,sort_keys=True))
    m2={**media,'id':'IMG-02'};mr['media'].append(m2);mr['modules'][0]['media'].append('IMG-02');test('F10-only-approved-image-eligible',lambda:generation_plan(mr,['M01'])=={'eligible':['IMG-01'],'blocked':['IMG-02'],'notice':generation_plan(mr,['M01'])['notice']})
    orphan={**media,'id':'IMG-99'};mr['media'].append(orphan);approve(mr,'draft','media',[orphan]);approve(mr,'generate','media',[orphan]);test('orphan-media-never-eligible',lambda:'IMG-99' not in generation_plan(mr,['M01'])['eligible'])
    mr['task']['stage']='DELIVERY';test('pending-media-final-denied',lambda:render(mr,body().replace('</section>','<div data-media-id="IMG-01"></div><div data-media-id="IMG-02"></div></section>'),'final'),True)
    mix=record(2);mix['task']['mixed_scope']=True;mix['modules'][0]['render_mode']='refine';approve(mix,'draft','modules',[mix['modules'][0]]);test('T11-mixed-whole-page-no-fake-approval',lambda:render(mix));bad=copy.deepcopy(mix);bad['modules'][1]['render_mode']='refine';test('mixed-unapproved-refine-denied',lambda:render(bad),True);test('mixed-incomplete-page-denied',lambda:render(mix,body()),True)
    mix['modules'][0]['media']=['IMG-01'];mix['media']=[copy.deepcopy(media)];approve(mix,'draft','media',mix['media']);approve(mix,'generate','media',mix['media'])
    test('mixed-generation-plan-approved-module-only',lambda:generation_plan(mix,['M01'])['eligible']==['IMG-01'])
    test('mixed-generation-unrefined-module-denied',lambda:generation_plan(mix,['M02']),True)
    snapshot=out/'synthetic-prior-snapshot.html';snapshot.write_text(render(record()),encoding='utf-8')
    migration=record();migration['task']['shell_migration']={'from':'synthetic-prior','to':'1.2.0','snapshot':str(snapshot),'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'checks':['public blocks','body styles','business scopes unchanged']}
    test('T11-shell-migration-preserves-approval',lambda:render(migration))
    migration['task']['shell_migration']['snapshot_sha256']='0'*64;test('T11-shell-snapshot-tamper-denied',lambda:render(migration),True)
    unresolved=copy.deepcopy(final);unresolved['modules'][0]['issues']=['关键统计未核对'];test('final-unresolved-fact-denied',lambda:render(unresolved,mode='final'),True)
    omitted=copy.deepcopy(final);omitted['media']=[{**media,'status':'omitted'}];omitted['modules'][0]['media']=['IMG-01'];test('image-omit-without-scope-denied',lambda:render(omitted,mode='final'),True);approve(omitted,'omit','media',omitted['media']);test('image-omit-exact-scope-final',lambda:render(omitted,mode='final'))
    test('T10-custom-video-class-denied',lambda:render(final,body().replace('</section>','<aside class="bespoke-video">视频待提供，当前不可播放</aside></section>'),'final'),True)
    test('T10-renamed-placeholder-denied',lambda:render(final,body().replace('</section>','<aside class="bespoke-placeholder">资源状态</aside></section>'),'final'),True)
    res={'id':'RES-01','module':'M01','revision':1,'list_version':'C01','draft_version':'D01','kind':'video','title':'附件演示','status':'pending','public_note':'视频未取得，当前不可播放；未读取音画。'}
    rr=copy.deepcopy(final);rr['resources']=[res];rr['modules'][0]['resources']=['RES-01'];rb=body().replace('</section>','<div data-resource-id="RES-01"></div></section>');test('T10-resource-record-pending-denied',lambda:render(rr,rb,'final'),True)
    rr['resources'][0].update(status='unavailable',resolution='retain-notice');test('T10-notice-without-decision-denied',lambda:render(rr,rb,'final'),True);approve(rr,'retain','resources',rr['resources']);test('T10-explicit-unavailable-notice-final',lambda:render(rr,rb,'final'));test('resource-DOM-omission-denied',lambda:render(rr,body(),'final'),True)
    test('editorial-missing-decisions-denied',lambda:render({**record(),'task':{**record()['task'],'editorial_contract':1}}),True)
    test('editorial-complete-decisions-accepted',lambda:render(record(editorial=True)))
    # Project-specific decision fixtures: these numbers are NOT a universal Skill policy.
    jobs=[{'name':'内容制作','min_k':6,'matching':True,'experience':'需1年','education':'大专','location':None},{'name':'内容助理','min_k':5.9,'matching':True},{'name':'销售主管','min_k':20,'matching':False}]
    selected=[j for j in jobs if j['min_k']>=6 and j['matching']];test('T16-project-salary-match-boundary',lambda:len(selected)==1 and selected[0]['experience']=='需1年' and selected[0]['location'] is None)
    (out/'project-constraints.json').write_text(json.dumps({'jobs':jobs,'selected':selected,'kos':'建议工作流，不是业务既有事实','video_read_scope':'仅文件名，未读音画','is_business_retest':False},ensure_ascii=False,indent=2))
    # Fresh authored synthetic complete page; no old task HTML, body, layout or approvals are read.
    page=record(9,True);page['task']['title']='把一次调研，变成可核对的内容作品 · 合成设计验证'
    titles=['从一次调研，做出可核对的内容作品','先解决三种真实阻碍','每个阶段，都留下可展示的成果','内容线：把选题推进到作品','运营线：从读者问题到内容回应','先看到变化，再核对证据','用范围解释数字，避免效果幻觉','看任务与门槛，再看薪资','带着作品与核对记录继续']
    for i,(m,t) in enumerate(zip(page['modules'],titles)):
        m['title']=t;m['key_message']=t;m['sources']=['S-INPUT-01']
        m['reader_question']=['这是什么，能做出什么？','我卡在哪里？','学习怎样转成可展示成果？','一个问题怎样推进成作品？','读者问题怎样形成运营回应？','发生了什么变化，凭什么可信？','这些数字的口径是什么？','岗位是否匹配，我差在哪里？','下一步怎样检查自己的作品？'][i]
        m['purpose']=m['reader_question']
        relationships=['主张与主题构图','并列诊断','阶段承接成果','生产顺序','建议的运营顺序','变化与证据','指标与口径','字段匹配','行动收束']
        web=['文案主图并列，行动在文案后','三项等宽，共用模块边界','阶段与成果在同行','动作链＋工具标注＋终点成果','独立建议链，与内容线连续','变化在前，三种证据同排','重点指标突出，支持项辅助','主判断带＋岗位条件字段','下一步说明与真实锚点']
        h5=['结论与行动优先，装饰图≤180px','逐项展开','每阶段动作后紧接成果','动作→说明→产物，链条纵向','建议身份可见，链条纵向','变化→证据→图注，原图可达','重点→范围→参与边界','条件完整，不藏经验学历与未知地点','说明后行动，不加报名信息']
        m['relationship']=relationships[i];m['visual_intent']={'focus':t,'order':'结论→必要解释→证据与条件','web':web[i],'h5':h5[i]}
        m['deduplication']='阶段与成果仅归M03；生产动作归M04/M05；证据口径归M06/M07，其他位置只引用，避免重复解释'
        m['content_layers']={'primary':t,'support':m['purpose'],'evidence':'合成项目材料及原生SVG示意，非真实业务','conditions':'合成练习；不推导录用、薪资保证或效果因果'}
    page['sources']=[source];approve(page,'list','sources',[source])
    # Small original SVG diagrams are synthetic test fixtures, not generated business media.
    diagrams={
        'cover-scene.svg': ('从问题到作品', [('问题','明确读者'),('结构','突出结论'),('作品','附核对记录')],800,480),
        'production-note.svg': ('产出与核对', [('作品','文案与画面'),('记录','来源与条件')],800,400),
        'evidence-wide.svg': ('合成作品结构', [('主结论','先被看见'),('支持','解释取舍'),('条件','范围明确')],800,420),
        'evidence-detail.svg': ('合成核对记录', [('来源','输入已核对'),('参与','个人与团队分开'),('范围','单次练习')],480,600)
    }
    for file,(title,parts,w,h) in diagrams.items():
        vertical=h>w;cells=''
        for i,(label,caption) in enumerate(parts):
            x=30 if vertical else 30+i*((w-60)/len(parts));y=100+i*140 if vertical else 125;cw=w-60 if vertical else (w-90)/len(parts)
            cells+=f'<rect x="{x}" y="{y}" width="{cw}" height="120" rx="16" fill="white"/><text x="{x+18}" y="{y+42}" font-size="24" fill="#07885F">{label}</text><text x="{x+18}" y="{y+78}" font-size="18" fill="#17221E">{caption}</text>'
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" rx="22" fill="#EAFAF4"/><text x="30" y="55" font-size="26" fill="#17221E">{title}</text>{cells}<text x="30" y="{h-25}" font-size="16" fill="#75817C">合成示意 · 不代表真实业务证据</text></svg>'
        if file=='production-note.svg':
            svg='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400"><rect x="85" y="40" width="400" height="255" rx="20" fill="#FFFFFF" stroke="#07885F" stroke-width="6"/><rect x="115" y="70" width="340" height="190" rx="16" fill="#EAFAF4"/><path d="M155 205L225 125L290 180L365 100L420 150" fill="none" stroke="#09B879" stroke-width="14"/><path d="M285 295v40h-75m75 0h75" fill="none" stroke="#07885F" stroke-width="8"/><rect x="510" y="105" width="195" height="230" rx="16" fill="#FFFFFF"/><path d="M540 160h130m-130 45h95m-95 45h115" stroke="#CDEEE1" stroke-width="12"/><path d="M635 295l25 25 40-50" stroke="#09B879" stroke-width="12" fill="none"/><text x="85" y="385" font-size="16" fill="#75817C">合成场景 · 作品与核对记录</text></svg>'
        (out/file).write_text(svg,encoding='utf-8')
    assets=[('M01','cover','cover-scene.svg','主题图：材料与作品共同构图'),('M04','illustration','production-note.svg','场景图：辅助生产链，非软件截图'),('M06','screenshot','document-demo.svg','竖版合成记录：完整口径'),('M06','screenshot','evidence-wide.svg','宽版合成作品：较长图注保留对照范围、贡献边界与核对条件'),('M06','screenshot','evidence-detail.svg','另一份独立合成文档，不冒充前后截图')]
    for idx,(module,role,file,caption) in enumerate(assets,1):
        im={**media,'id':f'IMG-{idx:02}','module':module,'role':role,'plan':'input','status':'available','local_path':str(out/file if file in diagrams else skill/'assets/examples'/file),'caption':caption,'alt':caption};page['media'].append(im);page['modules'][int(module[1:])-1]['media'].append(im['id'])
    approve(page,'reuse','media',page['media'])
    hero='<header class="qt-t-hero" data-module-id="M01"><div class="qt-t-stack"><p class="qt-t-eyebrow">合成设计验证 · 面向初次制作内容的学习者</p><h1>从一次调研，做出可核对的内容作品</h1><p>两条技能线、一组作品和一份核对记录。读者先看做成什么，再理解如何完成。</p><p class="qt-t-lead">作品可展示，条件可解释，证据可追溯。</p><a class="qt-btn qt-btn-primary" href="#M03">查看成长路径</a></div><div data-media-id="IMG-01"></div></header>'
    need='<section class="qt-section" data-module-id="M02"><h2>'+titles[1]+'</h2><div class="qt-t-group" data-qt-group>'+''.join(f'<article class="qt-t-card"><h3>{t}</h3><p>{v}</p></article>' for t,v in [('材料多，重点散','先回答读者的问题，再选择支持结论的材料。'),('会操作，缺产出','每个动作交给下一步一个可核对的成果。'),('有结果，缺边界','把统计范围和个人贡献放在证据旁。')])+'</div></section>'
    journey='<section class="qt-section" data-module-id="M03"><h2>'+titles[2]+'</h2><ol class="qt-t-journey">'+''.join(f'<li><div><h3>{t}</h3><p>{v}</p></div><div><h3>{o}</h3><p>{c}</p></div></li>' for t,v,o,c in [('理解任务','整理受众、问题和输入。','一页任务简报','说明哪些已知、哪些待核对。'),('做出作品','把选题推进成完整内容。','可展示的作品','附结构稿、修改与检查记录。'),('解释选择','用证据说明取舍。','作品说明与复盘','明确个人参与、范围和下一步。')])+'</ol></section>'
    def chain(mid,title,items):return f'<section class="qt-section" data-module-id="{mid}"><h2>{title}</h2><ol class="qt-t-production" data-qt-group>'+''.join(f'<li><h3>{t}</h3><p>{v}</p><span class="qt-t-tag">{tool}</span><p class="qt-t-output">{o}</p></li>' for t,v,tool,o in items)+'</ol>'
    production=chain('M04',titles[3],[('选定问题','从输入找出一个读者需要回答的问题。','调研/整理','任务简报'),('形成结构','让主结论、支持与条件各有位置。','提纲/改写','可审阅结构稿'),('完成作品','文字与画面共同表达，不用装饰代替解释。','编辑/排版','完整内容作品'),('核对交付','逐项检查来源、读者路径和边界。','核对清单','作品＋检查记录')])+'<div class="qt-t-scene"><div class="qt-t-stack"><h3>终点成果</h3><p>一份作品，附可复核的制作与检查记录。工具选择随任务变化。</p></div><div data-media-id="IMG-02"></div></div></section>'
    kos=chain('M05',titles[4],[('收集问题','记录读者反复询问的内容。','建议方法','问题清单'),('组织回应','选择一个问题给出有条件的回答。','建议方法','内容回应'),('检查反馈','核对反馈范围，修订下一轮。','建议方法','复盘记录')])+'<p>这是合成的KOS建议工作流，不代表真实项目已经提供的服务或效果。</p></section>'
    case='<section class="qt-section" data-module-id="M06"><h2>'+titles[5]+'</h2><div class="qt-t-change"><div><h3>起点：有素材，缺结构</h3><p>材料罗列，读者需读完才能理解产出。</p></div><div><h3>变化：主线与证据对应</h3><p>成果先被识别，再用可追溯记录解释取舍。</p></div></div><p>以下均为合成文档与示意作品，只验证完整呈现和图注对齐；不代表真实学生或效果。</p><div class="qt-t-group qt-t-media-group" data-qt-group><div data-media-id="IMG-03"></div><div data-media-id="IMG-04"></div><div data-media-id="IMG-05"></div></div></section>'
    metrics='<section class="qt-section" data-module-id="M07"><h2>'+titles[6]+'</h2><div class="qt-t-group" data-qt-group><article class="qt-t-card qt-t-featured"><h3>重点：核对覆盖</h3><p class="qt-t-metric">3 <span class="qt-t-unit">类证据</span></p><p>作品、结构稿、检查记录；合成验收维度。</p></article><article class="qt-t-card"><h3>时间范围</h3><p><strong>单次练习</strong></p><p>不与其他时段的统计相加。</p></article><article class="qt-t-card"><h3>参与边界</h3><p><strong>逐项记录</strong></p><p>个人贡献与团队/账号表现分别说明。</p></article></div></section>'
    jobshtml='<section class="qt-section" data-module-id="M08"><h2>'+titles[7]+'</h2><div class="qt-t-key"><h3>先核对职责匹配，再判断自己与岗位的差距</h3><p>本合成项目按薪资区间下限≥6K筛选，非应届起薪承诺，不推断市场总体比例。</p></div><div class="qt-t-paper qt-t-rows"><div class="qt-t-row"><div><h3>内容制作 · 合成例子</h3><p class="qt-t-lead">区间下限 6K</p></div><p>任务：组织材料并制作内容。经验：1年；学历：大专。</p><p>地点未提供，需另核对。低于6K或职责不匹配的例子不纳入。</p></div></div></section>'
    nextpage='<section class="qt-section" data-module-id="M09"><h2>'+titles[8]+'</h2><div class="qt-t-outcome"><h3>先检查一份作品</h3><p>能否说明读者问题、产出、来源与条件，再决定需要补哪项技能。</p><a class="qt-btn qt-btn-secondary" href="#M04">回看制作链</a></div><p>合成验证只说明设计与工具能力；不含价格、报名或录用保证。真实业务从零重测需重新读取材料并完成两次确认。</p></section>'
    full=hero+need+journey+production+kos+case+metrics+jobshtml+nextpage
    (out/'showcase-body.html').write_text(full,encoding='utf-8');(out/'showcase-record.json').write_text(json.dumps(page,ensure_ascii=False,indent=2),encoding='utf-8')
    draft=render(page,full);(out/'showcase-draft.html').write_text(draft,encoding='utf-8');approve(page,'draft','modules',page['modules']);page['task']['stage']='DELIVERY';html=render(page,full,'final');(out/'showcase-final.html').write_text(html,encoding='utf-8')
    test('T08-references-deduplicated',lambda:html.count('data-source-id=')==1 and html.count('class="qt-t-citations"')==9)
    test('final-no-review-DOM',lambda:not any(k in html.split('<main',1)[1].split('</main>',1)[0] for k in ['data-review-only','data-fact-state','data-qt-review-toggle']))
    (out/'showcase-final-record.json').write_text(json.dumps(page,ensure_ascii=False,indent=2),encoding='utf-8')
    reference=record(3,True);reference['task'].update(stage='DELIVERY',density='reference',title='合成资料页 · 材料核对');approve(reference,'draft','modules',reference['modules'])
    refbody='<header class="qt-t-stack" data-module-id="M01"><h1>材料核对：从来源到处理决定</h1><p>供重复查阅，不使用大Banner、人物或销售模块。</p><nav class="qt-t-route"><a href="#M02">查看字段</a><a href="#M03">判断缺项</a></nav></header><section class="qt-section" data-module-id="M02"><h2>同一份记录，逐项核对</h2><div class="qt-t-paper qt-t-rows"><div class="qt-t-row"><h3>实际读取</h3><p><strong>对象：</strong>材料全文</p><p><strong>范围：</strong>只记录实际可见信息</p></div><div class="qt-t-row"><h3>主张核验</h3><p><strong>对象：</strong>具体结论</p><p><strong>范围：</strong>支持证据与条件</p></div></div></section><section class="qt-section" data-module-id="M03"><h2>缺少关键项，就说明尚未完成</h2><div class="qt-t-key"><p>先继续独立可做的部分；必要结论不藏入附注。</p></div><div class="qt-t-fit qt-t-paper" data-qt-fit="prose" data-qt-align="compact"><p>局部短提示。</p></div></section>'
    (out/'reference-final.html').write_text(render(reference,refbody,'final'),encoding='utf-8');(out/'reference-record.json').write_text(json.dumps(reference,ensure_ascii=False,indent=2))
    # Keep the editorial before/after decisions inspectable, not a count of shortened sentences.
    decisions=[{'module':'M03','raw':'重复讲三阶段、三收获、作品清单。','decision':'合并到阶段→成果→核对记录；作品不再另起重复价值块。','copy':titles[2],'visual':'journey同一行连接动作与成果；H5相邻。'}, {'module':'M04','raw':'每项工具四五句操作，再在结尾补产出。','decision':'提取动作链，工具为辅，终点成果突出；必要操作保留。','copy':titles[3],'visual':'有序生产链＋工具标签＋终点成果带。'}, {'module':'M06','raw':'前/后/学校/字段等权罗列。','decision':'先呈现变化，再展示证据及贡献边界；不造效果。','copy':titles[5],'visual':'前后变化差异面积＋三图完整证据与共同图注基线。'}]
    (out/'editorial-decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2))
    result={'status':'fail' if any(c['status']=='fail' for c in checks) else 'pass','checks':checks,'image_generation_calls':0,'stub_requested_ids':stub,'is_business_retest':False,'not_run':['real project reread and fresh business approvals','real image generation','real video decode','independent agent evaluation']}
    (out/'regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[c for c in checks if c['status']=='fail']},ensure_ascii=False));return result['status']!='pass'
if __name__=='__main__':sys.exit(main())
