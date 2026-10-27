#!/usr/bin/env python3
"""Combine an authored fragment with the locked shell. Never generates images."""
import argparse, hashlib, json, re, sys
from html import escape
from pathlib import Path
from html_support import ROOT, Fragment, Node, blocks, image_data
from record import validate_record, approved, generation_plan, source_ready, module_mode


def node(html):
    return Fragment(html).root.children


def render_media(item, record, mode, task_dir):
    ident = escape(item['id']); desc = escape(item.get('purpose',''))
    required = ('purpose','role','composition','responsive','plan','module')
    if any(not item.get(k) for k in required):
        raise ValueError(f'{ident}: incomplete image plan')
    ready = item.get('status') in {'available','complete'} and item.get('local_path')
    if ready:
        if item.get('plan') not in {'input','generate'}:raise ValueError(f'{ident}: available asset still needs an authorized source plan')
        if item['plan'] == 'input' and not approved(record,'reuse','media',item):
            raise ValueError(f'{ident}: input reuse requires exact instruction evidence')
        if item['plan'] == 'generate':
            if mode == 'draft' or not (approved(record,'generate','media',item) and approved(record,'draft','media',item)):
                raise ValueError(f'{ident}: generated asset outside authorized refine scope')
        path = Path(item['local_path'])
        if not path.is_absolute():path = task_dir/path
        uri = image_data(path)
        role = item['role']
        css = 'qt-t-person-slot' if role == 'person' else 'qt-t-media'
        if not isinstance(item.get('alt'), str):
            raise ValueError(f'{ident}: explicit reader-facing alt required (empty only for decorative images)')
        if role == 'screenshot' and not item['alt'].strip():
            raise ValueError(f'{ident}: evidence screenshot needs descriptive alt')
        caption = item.get('caption', '')
        if not isinstance(caption, str):raise ValueError(f'{ident}: caption must be reader-facing text')
        img = f'<img src="{uri}" alt="{escape(item["alt"],quote=True)}" decoding="async">'
        if role == 'screenshot':img=f'<button class="qt-t-zoom" type="button" data-qt-zoom aria-label="放大：{escape(item["alt"],quote=True)}">{img}</button>'
        caption_html = f'<figcaption>{escape(caption)}</figcaption>' if caption.strip() else ''
        return f'<figure id="{ident}" data-media-id="{ident}" class="{css}" data-media-role="{escape(role)}">{img}{caption_html}</figure>'
    if mode == 'final':raise ValueError(f'{ident}: unresolved image prevents final')
    plan = {'input':'复用输入（待取得）','generate':'确认后生成（当前未生成）','select':'待选择'}[item['plan']]
    return f'<figure id="{ident}" data-media-id="{ident}" class="qt-t-placeholder"><strong>{ident} · {desc}</strong><p>模块：{escape(item["module"])}；角色：{escape(item["role"])}；来源方案：{plan}</p><p>构图/安全区：{escape(item["composition"])}</p><p>Web/H5：{escape(item["responsive"])}</p><figcaption>待提供或待确认的素材占位；不是已生成图片。</figcaption></figure>'


def compose(record, body, mode, task_dir):
    migration=record.get('task',{}).get('shell_migration')
    if migration:
        version=json.loads((ROOT/'assets/provenance.json').read_text(encoding='utf-8'))['version']
        if not all(migration.get(k) for k in ('from','to','snapshot','snapshot_sha256','checks')) or migration['to']!=version:
            raise ValueError('shell migration requires from/to/current version, snapshot SHA and impact checks')
        snapshot=Path(migration['snapshot'])
        if not snapshot.is_absolute():snapshot=task_dir/snapshot
        if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=migration['snapshot_sha256']:
            raise ValueError('shell migration snapshot SHA mismatch')
    parsed = Fragment(body)
    modules = [c for c in parsed.root.children if isinstance(c,Node)]
    if any(isinstance(c,str) and c.strip() for c in parsed.root.children):raise ValueError('all body content must belong to modules')
    ids = [m.attrs.get('data-module-id') for m in modules]
    data = validate_record(record,mode,ids)
    all_nodes = list(parsed.root.walk())
    if any(n.attrs.get('data-module-id') not in ids for n in all_nodes if 'data-module-id' in n.attrs):
        raise ValueError('nested unknown module')
    if sum('data-module-id' in n.attrs for n in all_nodes) != len(ids):raise ValueError('nested/duplicate module IDs')
    review = []; used_sources = {}
    for m in modules:
        ident=m.attrs['data-module-id'];item=data['modules'][ident]
        effective=module_mode(record,item,mode)
        if m.tag not in {'section','article','header'}:raise ValueError('module root must be section/article/header')
        m.attrs['id']=ident
        for n in list(m.walk()):
            if 'data-source-id' in n.attrs:
                raise ValueError('source records belong to the generated review area; author necessary public attribution as normal body text')
        media_nodes=[n for n in m.walk() if 'data-media-id' in n.attrs]
        expected={mid for mid in item.get('media',[]) if data['media'][mid].get('status')!='omitted'}
        if {n.attrs['data-media-id'] for n in media_nodes} != expected or len(media_nodes)!=len(expected):
            raise ValueError(f'{ident}: media slots must match non-omitted record media exactly')
        for n in media_nodes:
            if n.children:raise ValueError('media slot must be empty; composer supplies media/placeholder')
            media=data['media'][n.attrs['data-media-id']]
            rendered=Fragment(render_media(media,record,effective,task_dir)).root.children[0]
            n.tag,n.attrs,n.children=rendered.tag,rendered.attrs,rendered.children
            if media.get('status') not in {'available','complete'}:
                review.append((media['id'],'待提供',media['purpose']))
        resource_nodes=[n for n in m.walk() if 'data-resource-id' in n.attrs]
        expected_resources={rid for rid in item.get('resources',[]) if data['resources'][rid].get('status')!='omitted'}
        if {n.attrs['data-resource-id'] for n in resource_nodes}!=expected_resources or len(resource_nodes)!=len(expected_resources):
            raise ValueError(f'{ident}: resource slots must match record exactly')
        for n in resource_nodes:
            if n.children:raise ValueError('resource slot must be empty')
            resource=data['resources'][n.attrs['data-resource-id']]
            retained=mode=='final' and resource.get('resolution')=='retain-notice'
            n.tag='aside';n.attrs.update({'class':'qt-t-resource-notice','data-resource-state':'retained-unavailable' if retained else 'pending'})
            n.children=node(f'<p>{escape(resource.get("public_note") or "视频资源未取得，当前不可播放；未读取音画。")}</p>')
            if not retained:review.append((ident,'待提供',resource.get('title','视频资源')))
        for sid in item.get('sources',[]):
            source=data['sources'][sid]
            if source.get('verification') not in {'unverified','verified','unverifiable'} or source.get('adoption') not in {'pending','adopted','rejected'}:
                raise ValueError(f'{sid}: separate verification/adoption required')
            if source['adoption']=='rejected':raise ValueError(f'{sid}: rejected source still in module')
            if source.get('kind')=='web' and not all(source.get(k) for k in ('url','publisher','accessed','supports')):
                raise ValueError(f'{sid}: missing web source evidence')
            adopted=source['adoption']=='adopted'
            if adopted and not (approved(record,'list','sources',source) or approved(record,'draft','sources',source)):
                raise ValueError(f'{sid}: adopted requires recorded exact scope')
            if mode=='final' and not source_ready(record,source):raise ValueError(f'{sid}: unresolved source prevents final')
            used_sources[sid]=source
            if not adopted:review.append((ident,'待确认',f'{sid} 待确认采用'))
        if mode!='final':
            state='已确认' if approved(record,'draft','modules',item) and not item.get('issues') else ('需调整' if item.get('issues') else '待确认')
            if item.get('issues'):
                m.children+=node(f'<p class="qt-t-key" data-fact-state>未决事项：{escape("；".join(item["issues"]))}</p>')
            issues='；'.join(item.get('issues',[])) or '核对实际文案、结构与相关素材方案。'

            if state!='已确认':review.append((ident,state,issues))
    if mode=='final':
        for n in parsed.root.walk():
            if any(k in n.attrs for k in ('data-review-only','data-review-index','data-fact-state','data-experiment')) or 'qt-t-placeholder' in (n.attrs.get('class') or '').split():
                raise ValueError('remove review/experiment UI from authored fragment before final')
    source_review=''
    if mode!='final' and used_sources:
        entries=[]
        for sid,source in used_sources.items():
            label=escape(source.get('title',sid));url=source.get('url','')
            if url:
                if not re.match(r'^https?://[^\s]+$',url):raise ValueError('source URL must be http(s)')
                label=f'<a href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
            note=source.get('internal_note') or source.get('public_note') or ''
            details='；'.join(str(s) for s in (source.get('supports'),note) if s)
            entries.append(f'<li data-source-id="{escape(sid)}">{escape(sid)} · {label} · {escape(details)} · {escape(source["verification"])} / {escape(source["adoption"])}</li>')
        source_review='<details data-review-only><summary>内部来源核对</summary><ul>'+''.join(entries)+'</ul></details>'
    controls=''
    if mode!='final':
        entries=''.join(f'<li><a href="#{escape(i)}">{escape(i)} · {escape(s)} · {escape(t)}</a></li>' for i,s,t in review)
        notes=''
        for i in ids:
            module=data['modules'][i]
            state='需调整' if module.get('issues') else ('已确认' if approved(record,'draft','modules',module) else '待确认')
            message=module.get('key_message') or module.get('purpose','')
            notes+=f'<li>{escape(i)} · {state} · {module_mode(record,module,mode)} · {escape(message)}</li>'
        status='局部修订完成 · 其余范围待审阅' if record['task'].get('mixed_scope') else ('精修待审阅' if mode=='refine' else '初稿待审阅')
        controls=f'<aside id="qt-review-controls" class="qt-surface qt-text-group"><p class="qt-t-lead">{status}</p><button type="button" class="qt-btn qt-btn-secondary" data-qt-review-toggle aria-pressed="true">隐藏策划批注与索引</button><details data-review-only data-review-index><summary>{len(review)} 项待审阅 · 清单 {escape(record["task"]["list_version"])} / 初稿 {escape(record["task"]["draft_version"])}</summary><p>显示开关不提交确认；请在对话说明版本与范围。</p><ul>{entries}</ul><ul>{notes}</ul></details>{source_review}</aside>'
    content=f'<main class="qt-wrap qt-page qt-t-topic" data-density="{escape(record["task"].get("density","explain"),quote=True)}">{controls}{parsed.root.render()}</main>'
    shell=(ROOT/'assets/templates/public-shell.html').read_text(encoding="utf-8")
    expected=blocks(shell)
    result=re.sub(r'<!-- QT_PAGE_CONTENT_START -->.*?<!-- QT_PAGE_CONTENT_END -->',lambda _:f'<!-- QT_PAGE_CONTENT_START -->{content}<!-- QT_PAGE_CONTENT_END -->',shell,flags=re.S)
    result=re.sub(r'<title>.*?</title>',lambda _:f'<title>{escape(record["task"]["title"])}</title>',result,count=1,flags=re.S)
    css=(ROOT/'assets/components/topic.css').read_text(encoding="utf-8");js=(ROOT/'assets/components/topic.js').read_text(encoding="utf-8")
    result=result.replace('</head>',f'<style id="qt-topic-style">{css}</style></head>')
    result=result.replace('</body>',f'<script id="qt-topic-script">{js}</script></body>')
    assert blocks(result)==expected
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',required=True,type=Path)
    parser.add_argument('--body',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--mode',choices=['draft','refine','final'],default='draft')
    parser.add_argument('--generation-plan',action='store_true',help='Print eligible IDs only; no side effects')
    parser.add_argument('--modules',nargs='+',help='Scope for generation-plan only')
    args=parser.parse_args()
    record=json.loads(args.record.read_text(encoding="utf-8"))
    if args.generation_plan:
        if args.mode!='refine' or not args.modules:parser.error('plan needs --mode refine --modules')
        print(json.dumps(generation_plan(record,args.modules),ensure_ascii=False,indent=2));return
    if not args.body or not args.out:parser.error('--body and --out required')
    if args.out.resolve().is_relative_to(ROOT):raise ValueError('output must be outside skill')
    if args.out.resolve() in {args.body.resolve(),args.record.resolve()}:raise ValueError('output cannot overwrite inputs')
    result=compose(record,args.body.read_text(encoding="utf-8"),args.mode,args.record.resolve().parent)
    # Validate BEFORE any output write, preventing partial artifacts on failure.
    from check_html import inspect
    report=inspect(result,args.mode,record)
    if report['errors']:raise ValueError('; '.join(report['errors']))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(result, encoding="utf-8")
    print(json.dumps({'output':str(args.out),'mode':args.mode,'modules':report['modules'],'image_generation_calls':0},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
