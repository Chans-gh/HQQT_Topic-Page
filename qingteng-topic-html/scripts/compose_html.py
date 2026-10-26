#!/usr/bin/env python3
"""Combine an authored fragment with the locked shell. Never generates images."""
import argparse, json, re, sys
from html import escape
from pathlib import Path
from html_support import ROOT, Fragment, Node, blocks, image_data
from record import validate_record, approved, generation_plan


def node(html):
    return Fragment(html).root.children


def render_media(item, record, mode, task_dir):
    ident = escape(item['id']); desc = escape(item.get('purpose',''))
    required = ('purpose','role','composition','responsive','plan','module')
    if any(not item.get(k) for k in required):
        raise ValueError(f'{ident}: incomplete image plan')
    ready = item.get('status') in {'available','complete'} and item.get('local_path')
    if ready:
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
        img = f'<img src="{uri}" alt="{escape(item.get("alt",item["purpose"]),quote=True)}">'
        if role == 'screenshot':img=f'<button class="qt-t-zoom" type="button" data-qt-zoom aria-label="放大：{desc}">{img}</button>'
        return f'<figure id="{ident}" data-media-id="{ident}" class="{css}" data-media-role="{escape(role)}">{img}<figcaption>{escape(item.get("caption",item["purpose"]))}</figcaption></figure>'
    if mode == 'final':raise ValueError(f'{ident}: unresolved image prevents final')
    plan = {'input':'复用输入（待取得）','generate':'确认后生成（当前未生成）','select':'待选择'}[item['plan']]
    return f'<figure id="{ident}" data-media-id="{ident}" class="qt-t-placeholder"><strong>{ident} · {desc}</strong><p>模块：{escape(item["module"])}；角色：{escape(item["role"])}；来源方案：{plan}</p><p>构图/安全区：{escape(item["composition"])}</p><p>Web/H5：{escape(item["responsive"])}</p><figcaption>待提供或待确认的素材占位；不是已生成图片。</figcaption></figure>'


def compose(record, body, mode, task_dir):
    parsed = Fragment(body)
    modules = [c for c in parsed.root.children if isinstance(c,Node)]
    if any(isinstance(c,str) and c.strip() for c in parsed.root.children):raise ValueError('all body content must belong to modules')
    ids = [m.attrs.get('data-module-id') for m in modules]
    data = validate_record(record,mode,ids)
    all_nodes = list(parsed.root.walk())
    if any(n.attrs.get('data-module-id') not in ids for n in all_nodes if 'data-module-id' in n.attrs):
        raise ValueError('nested unknown module')
    if sum('data-module-id' in n.attrs for n in all_nodes) != len(ids):raise ValueError('nested/duplicate module IDs')
    review = []
    for m in modules:
        ident=m.attrs['data-module-id'];item=data['modules'][ident]
        if m.tag not in {'section','article','header'}:raise ValueError('module root must be section/article/header')
        m.attrs['id']=ident
        for n in list(m.walk()):
            if 'data-source-id' in n.attrs:
                raise ValueError('source citations are generated from module.sources; do not hand author duplicate state')
        media_nodes=[n for n in m.walk() if 'data-media-id' in n.attrs]
        expected={mid for mid in item.get('media',[]) if data['media'][mid].get('status')!='omitted'}
        if {n.attrs['data-media-id'] for n in media_nodes} != expected or len(media_nodes)!=len(expected):
            raise ValueError(f'{ident}: media slots must match non-omitted record media exactly')
        for n in media_nodes:
            if n.children:raise ValueError('media slot must be empty; composer supplies media/placeholder')
            media=data['media'][n.attrs['data-media-id']]
            rendered=Fragment(render_media(media,record,mode,task_dir)).root.children[0]
            n.tag,n.attrs,n.children=rendered.tag,rendered.attrs,rendered.children
            if media.get('status') not in {'available','complete'}:
                review.append((media['id'],'待提供',media['purpose']))
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
            if mode=='final' and (not adopted or source['verification']!='verified'):
                raise ValueError(f'{sid}: unresolved source prevents final')
            verification={'verified':'已查证','unverified':'未查证','unverifiable':'无法核实'}[source['verification']]
            adoption={'pending':'待确认采用','adopted':'已采用','rejected':'不采用'}[source['adoption']]
            label=escape(source.get('title',sid));url=source.get('url','')
            if url:
                if not re.match(r'^https?://[^\s]+$',url):raise ValueError('source URL must be http(s)')
                label=f'<a href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
            state='' if mode=='final' else f' · {verification} / {adoption}'
            m.children+=node(f'<p class="qt-small" data-source-id="{sid}">{sid} · {label}{state} · {escape(source.get("supports",""))}</p>')
            if not adopted:review.append((ident,'待确认',f'{sid} {adoption}'))
        if mode!='final':
            state='已确认' if approved(record,'draft','modules',item) and not item.get('issues') else ('需调整' if item.get('issues') else '待确认')
            m.children+=node(f'<p class="qt-small" data-fact-state>{ident} · {state}</p>')
            details=escape(item.get('purpose',''))+'；'+escape('；'.join(item.get('points',[])))
            issues='；'.join(item.get('issues',[])) or '核对实际文案、结构与相关素材方案。'
            m.children+=node(f'<details data-review-only><summary>查看 {ident} 策划批注</summary><p>{details}</p><p>{escape(issues)}</p></details>')
            if state!='已确认':review.append((ident,state,issues))
    if mode=='final':
        for n in parsed.root.walk():
            if any(k in n.attrs for k in ('data-review-only','data-review-index','data-fact-state','data-experiment')) or 'qt-t-placeholder' in (n.attrs.get('class') or '').split():
                raise ValueError('remove review/experiment UI from authored fragment before final')
    controls=''
    if mode!='final':
        entries=''.join(f'<li><a href="#{escape(i)}">{escape(i)} · {escape(s)} · {escape(t)}</a></li>' for i,s,t in review)
        controls=f'<aside id="qt-review-controls" class="qt-surface qt-text-group"><h2>初稿审阅</h2><p>清单 {escape(record["task"]["list_version"])} → 初稿 {escape(record["task"]["draft_version"])}。开关只控制显示，不提交确认。</p><button type="button" class="qt-btn qt-btn-secondary" data-qt-review-toggle aria-pressed="true">隐藏策划批注与索引</button><div data-review-only data-review-index><p>{len(review)} 项待审阅；正式确认请在对话中指出版本和范围。</p><ul>{entries}</ul></div></aside>'
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
