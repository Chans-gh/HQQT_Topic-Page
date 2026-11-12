#!/usr/bin/env python3
"""Combine an authored fragment with the locked shell. Never generates images."""
import argparse, hashlib, json, re, sys
from html import escape
from pathlib import Path
from html_support import ROOT, Fragment, Node, blocks, image_data, TARGETS
from record import validate_record, approved, generation_allowed, generation_plan, source_ready, module_mode, execution_allowed


def node(html):
    return Fragment(html).root.children


def validate_anchors(modules, data):
    """Reject lost/ambiguous IDs before reading or encoding any business media."""
    from urllib.parse import unquote
    shell = (ROOT/'assets/templates/public-shell.html').read_text(encoding='utf-8')
    reserved = set(re.findall(r'\bid="([^"]+)"', shell))
    canonical = {m.attrs['data-module-id'] for m in modules}
    media_ids = {i for m in modules for i in data['modules'][m.attrs['data-module-id']].get('media', [])
                 if data['media'][i].get('status') != 'omitted'}
    claimed = set(canonical) | media_ids | reserved
    for module in modules:
        ident = module.attrs['data-module-id']
        if 'id' in module.attrs and module.attrs['id'] != ident:
            raise ValueError(f'{ident}: author id={module.attrs["id"]!r} would be lost; use id={ident!r} and update its links')
        for n in module.walk():
            value = n.attrs.get('id')
            if value is None or n is module:
                continue
            if not value or re.search(r'\s', value) or value in claimed:
                raise ValueError(f'{ident}: duplicate/reserved/invalid author id {value!r}')
            if 'data-media-id' in n.attrs or 'data-resource-id' in n.attrs:
                raise ValueError(f'{ident}: generated media/resource slot must not carry an author id')
            claimed.add(value)
    for module in modules:
        for n in module.walk():
            href = n.attrs.get('href', '')
            if href.startswith('#') and unquote(href[1:]) not in claimed | TARGETS:
                raise ValueError(f'{module.attrs["data-module-id"]}: unresolved author anchor {href!r}; use a module or existing inner id')


def render_media(item, record, mode, task_dir, asset_audit=None, asset_cache=None):
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
            if mode == 'draft' or not generation_allowed(record,item):
                raise ValueError(f'{ident}: generated asset outside authorized refine scope')
        path = Path(item['local_path'])
        if not path.is_absolute():path = task_dir/path
        uri = asset_cache.image(path) if asset_cache else image_data(path)
        role = item['role']
        css = 'qt-t-person-slot' if role == 'person' else 'qt-t-media'
        if not isinstance(item.get('alt'), str):
            raise ValueError(f'{ident}: explicit reader-facing alt required (empty only for decorative images)')
        if role == 'screenshot' and not item['alt'].strip():
            raise ValueError(f'{ident}: evidence screenshot needs descriptive alt')
        caption = item.get('caption', '')
        if not isinstance(caption, str):raise ValueError(f'{ident}: caption must be reader-facing text')
        img = f'<img src="{uri}" alt="{escape(item["alt"],quote=True)}" decoding="async">'
        if role == 'screenshot':
            original=''
            if item.get('original_path'):
                p=Path(item['original_path']);p=p if p.is_absolute() else task_dir/p
                original_uri = asset_cache.image(p) if asset_cache else image_data(p)
                if original_uri != uri:
                    original=f' data-qt-original-src="{original_uri}"'
            if item.get('focus_region') is not None:
                original += f' data-qt-focus-region="{escape(json.dumps(item["focus_region"]),quote=True)}" data-qt-focus-note="{escape(item["focus_note"],quote=True)}"'
            img=f'<button class="qt-t-zoom" type="button" data-qt-zoom{original} aria-label="放大：{escape(item["alt"],quote=True)}">{img}</button>'
        caption_html = f'<figcaption>{escape(caption)}</figcaption>' if caption.strip() else ''
        background=f' data-media-background="{escape(item["background"],quote=True)}"' if item.get('background') else ''
        row = next((r for r in (asset_audit or {}).get('assets', []) if r['id'] == item['id']), {})
        metrics = f' data-media-bytes="{row.get("bytes", path.stat().st_size)}"'
        bounds = row.get('subject_region')
        if not bounds and row.get('png', {}).get('visible_bounds'):
            png = row['png']; x0,y0,x1,y1 = png['visible_bounds']
            bounds = [x0/png['width'], y0/png['height'], (x1+1)/png['width'], (y1+1)/png['height']]
        if bounds:
            metrics += f' data-qt-subject-bounds="{escape(json.dumps(bounds), quote=True)}"'
        return f'<figure id="{ident}" data-media-id="{ident}" class="{css}" data-media-role="{escape(role)}"{background}{metrics}>{img}{caption_html}</figure>'
    if mode == 'final':raise ValueError(f'{ident}: unresolved image prevents final')
    plan = {'input':'复用输入（待取得）','generate':'已获准生成（当前未生成）' if generation_allowed(record,item) else '拟生成（授权范围待确认）','select':'待选择'}[item['plan']]
    return f'<figure id="{ident}" data-media-id="{ident}" class="qt-t-placeholder"><strong>{ident} · {desc}</strong><p>模块：{escape(item["module"])}；角色：{escape(item["role"])}；来源方案：{plan}</p><p>构图/安全区：{escape(item["composition"])}</p><p>Web/H5：{escape(item["responsive"])}</p><figcaption>素材尚未到位；当前是说明占位，不是已生成图片。</figcaption></figure>'


def subject_css(text):
    """Small, intentionally bounded authoring interface, not a general CSS sanitizer."""
    clean=re.sub(r'/\*.*?\*/','',text,flags=re.S).strip()
    if re.search(r'[<@\\]|url\s*\(|(?:image-set|image|paint)\s*\(|(?:https?|file|data|javascript):|//|expression\s*\(|!important|behavior\s*:|-moz-binding',clean,re.I):
        raise ValueError('subject CSS: imports, resources, escapes, active CSS and !important are not supported')
    rules=re.findall(r'([^{}]+)\{([^{}]*)\}',clean)
    if re.sub(r'[^{}]+\{[^{}]*\}','',clean).strip() or (clean and not rules):raise ValueError('subject CSS: only flat qualified rules supported')
    for selectors,body in rules:
        for selector in selectors.split(','):
            selector=selector.strip()
            if not re.match(r'^\.qt-t-topic\s+\.qt-u-[a-z][a-z0-9-]*(?=[\s.:>+~]|$)',selector):
                raise ValueError('subject CSS: each selector must start .qt-t-topic .qt-u-<name>')
            if not re.fullmatch(r'[a-zA-Z0-9_ .:>+~()\-]+',selector) or re.search(r':(?:has|is|where|not|host|root|global)\b|\.qt-(?!u-|t-topic\b)',selector):
                raise ValueError('subject CSS: unsupported/public selector')
        for declaration in body.split(';'):
            if not declaration.strip():continue
            if ':' not in declaration:raise ValueError('subject CSS: invalid declaration')
            prop,value=map(str.strip,declaration.split(':',1))
            if not re.fullmatch(r'(?:[a-z][a-z-]*|--qt-u-[a-z0-9-]+)',prop) or not value or re.search(r'position\s*:\s*(?:fixed|sticky)|overflow-x\s*:\s*hidden',declaration,re.I):
                raise ValueError('subject CSS: unsupported declaration')
    return clean


def compose(record, body, mode, task_dir, css_text="", asset_cache=None):
    custom_css=subject_css(css_text)
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
    data = validate_record(record,mode,ids,task_dir)
    validate_anchors(modules, data)
    from production import audit_assets, AssetCache
    asset_cache = asset_cache or AssetCache()
    asset_audit = audit_assets(record,task_dir,mode,cache=asset_cache)
    all_nodes = list(parsed.root.walk())
    for n in all_nodes:
        if 'data-qt-icon' in n.attrs:
            name=n.attrs['data-qt-icon']
            if not re.fullmatch(r'[a-z][a-z-]*',name or ''):raise ValueError('invalid content icon name')
            icon=ROOT/f'assets/icons/content-{name}.svg'
            if not icon.is_file() or n.children:raise ValueError('unknown icon or nonempty content icon slot')
            n.attrs.update({'class':(n.attrs.get('class','')+' qt-t-icon').strip(),'aria-hidden':'true'})
            svg=Fragment(icon.read_text(encoding='utf-8')).root.children[0]
            svg.attrs.update({'aria-hidden':'true','focusable':'false'})
            n.children=[svg]
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
            rendered=Fragment(render_media(media,record,effective,task_dir,asset_audit,asset_cache)).root.children[0]
            n.tag,n.attrs,n.children=rendered.tag,rendered.attrs,rendered.children
            if media.get('status') not in {'available','complete'}:
                state='待制作' if media.get('plan')=='generate' and generation_allowed(record,media) else '待确认生成范围' if media.get('plan')=='generate' else '待提供'
                review.append((media['id'],state,media['purpose']))
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
            if adopted and not (approved(record,'list','sources',source) or approved(record,'draft','sources',source) or execution_allowed(record,'refine','sources',source)):
                raise ValueError(f'{sid}: adopted requires recorded exact scope')
            if mode=='final' and not source_ready(record,source):raise ValueError(f'{sid}: unresolved source prevents final')
            used_sources[sid]=source
            if not adopted:review.append((ident,'待确认',f'{sid} 待确认采用'))
        if mode!='final':
            state=('已确认' if approved(record,'draft','modules',item) else '获准直接制作，实际页面未审阅' if execution_allowed(record,'refine','modules',item) else '待确认') if not item.get('issues') else '需调整'
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
            state='需调整' if module.get('issues') else ('已确认' if approved(record,'draft','modules',module) else '获准直接制作，实际页面未审阅' if execution_allowed(record,'refine','modules',module) else '待确认')
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
    result=result.replace('</head>',f'<style id="qt-topic-style">{css}</style><style id="qt-subject-style">{custom_css}</style></head>')
    result=result.replace('</body>',f'<script id="qt-topic-script">{js}</script></body>')
    assert blocks(result)==expected
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',required=True,type=Path)
    parser.add_argument('--body',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--subject-css',type=Path,help='Scoped flat CSS: .qt-t-topic .qt-u-<name>; no imports/resources/public overrides')
    parser.add_argument('--mode',choices=['draft','refine','final'],default='draft')
    parser.add_argument('--generation-plan',action='store_true',help='Print eligible IDs only; no side effects')
    parser.add_argument('--modules',nargs='+',help='Scope for generation-plan only')
    args=parser.parse_args()
    record=json.loads(args.record.read_text(encoding="utf-8"))
    if args.generation_plan:
        if args.mode!='refine' or not args.modules:parser.error('plan needs --mode refine --modules')
        print(json.dumps(generation_plan(record,args.modules,args.record.resolve().parent),ensure_ascii=False,indent=2));return
    if not args.body or not args.out:parser.error('--body and --out required')
    if args.out.resolve().is_relative_to(ROOT):raise ValueError('output must be outside skill')
    if args.out.resolve() in {p.resolve() for p in (args.body,args.record,args.subject_css) if p}:raise ValueError('output cannot overwrite inputs')
    result=compose(record,args.body.read_text(encoding="utf-8"),args.mode,args.record.resolve().parent,args.subject_css.read_text(encoding='utf-8') if args.subject_css else '')
    # Validate BEFORE any output write, preventing partial artifacts on failure.
    from check_html import inspect
    report=inspect(result,args.mode,record)
    # A rejected page still needs a renderable candidate for fixing and re-reviewing.
    # Feedback remains a failing acceptance result; only structural errors block writing.
    structural=[e for e in report['errors'] if not e.startswith('unresolved user feedback:')]
    if structural:raise ValueError('; '.join(structural))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(result, encoding="utf-8")
    from production import audit_assets
    assets=audit_assets(record,args.record.resolve().parent,args.mode)
    print(json.dumps({'output':str(args.out),'mode':args.mode,'modules':report['modules'],'completion_status':report['completion_status'],'unresolved_feedback':report.get('unresolved_feedback',[]),'composer_generation_calls':0,'task_generated_assets':assets['task_generated_assets'],'generation_scope':assets['generation_scope']},ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
