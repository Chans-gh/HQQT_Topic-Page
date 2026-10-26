#!/usr/bin/env python3
"""Static invariants; semantic truth, consent and visual quality remain human checks."""
import argparse, json, re, sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from html_support import ROOT, blocks, TARGETS
from record import validate_record


class Page(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.nodes=[];self.feed(html)
    def handle_starttag(self,tag,attrs):self.nodes.append((tag,dict(attrs)))
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)


def inspect(html,mode='draft',record=None):
    errors=[];warnings=[]
    try:
        if blocks(html)!=blocks((ROOT/'assets/templates/public-shell.html').read_text(encoding="utf-8")):errors.append('shared blocks differ from locked shell')
    except ValueError as exc:errors.append(str(exc))
    page=Page(html);ids=[a['id'] for _,a in page.nodes if a.get('id')]
    duplicates=[i for i,n in Counter(ids).items() if n>1]
    if duplicates:errors.append('duplicate IDs: '+','.join(duplicates))
    modules=[a['data-module-id'] for _,a in page.nodes if 'data-module-id' in a]
    if not modules:errors.append('no module IDs')
    if record:
        try:
            data=validate_record(record,mode,modules)
            expected_media=[mid for ident in modules for mid in data['modules'][ident].get('media',[]) if data['media'][mid].get('status')!='omitted']
            actual_media=[a['data-media-id'] for _,a in page.nodes if 'data-media-id' in a]
            if Counter(expected_media)!=Counter(actual_media):errors.append('media scope/count differs from record')
            expected_sources={sid for ident in modules for sid in data['modules'][ident].get('sources',[])}
            actual_sources={a['data-source-id'] for _,a in page.nodes if 'data-source-id' in a}
            if expected_sources!=actual_sources:errors.append('source scope differs from record')
        except (ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    if sum(t=='h1' for t,_ in page.nodes)!=1:errors.append('exactly one h1 required')
    if not any(t=='meta' and a.get('name')=='viewport' and 'width=device-width' in a.get('content','') and 'initial-scale=1' in a.get('content','') for t,a in page.nodes):errors.append('viewport missing')
    seen_targets={a.get('data-qt-target') for _,a in page.nodes if 'data-qt-target' in a}
    if seen_targets != TARGETS-{'search','login'}:errors.append('footer prototype target set changed')
    if ids.count('qt-official-header')!=1:errors.append('exactly one official Qingteng header required')
    # Only the byte-locked public blocks may use the official online services.
    # A modified shared block already fails above; authored body resources remain restricted.
    subject=html
    try:
        for value in blocks(html).values():subject=subject.replace(value,'')
    except ValueError:pass
    subject_nodes=Page(subject).nodes
    for tag,a in page.nodes:
        for k,v in a.items():
            if k.startswith('on'):errors.append('inline event handler forbidden')
            if k in {'href','src','poster'} and v and re.match(r'\s*(?:javascript|vbscript):',v,re.I):errors.append('executable URL forbidden')
        if tag=='a' and a.get('href','').startswith('#'):
            dest=a['href'][1:].split('?',1)[0]
            if dest not in ids and dest not in TARGETS:errors.append('unresolved anchor: '+dest)
        if tag=='img' and 'alt' not in a:errors.append('image alt missing')
        if tag=='video' and ('autoplay' in a or 'controls' not in a):errors.append('video needs real controls and no autoplay')
        if mode=='final' and (any(k in a for k in ('data-review-only','data-review-index','data-qt-review-toggle','data-fact-state','data-experiment')) or 'qt-t-placeholder' in a.get('class','').split()):
            errors.append('final contains review/placeholder UI')
    for tag,a in subject_nodes:
        if tag in {'iframe','object','embed','base'}:errors.append(f'unsupported subject runtime tag: {tag}')
        if tag=='link':errors.append('external subject stylesheet/link runtime dependency')
        for k,v in a.items():
            if k in {'src','poster','srcset'} and v and not v.startswith('data:image/'):
                errors.append(f'non-embedded subject runtime resource: {tag}.{k}')
            if k=='style' and v and re.search(r'url\(\s*[\'"]?(?:https?:|//|file:)|@import',v,re.I):
                errors.append('external subject inline CSS dependency')
            if tag!='a' and k in {'href','xlink:href'} and v and not v.startswith(('#','data:image/')):
                errors.append('external subject SVG/resource reference')
    styles='\n'.join(re.findall(r'<style[^>]*>(.*?)</style>',subject,re.S))
    if re.search(r'\.qt-(?:site-header|site-footer|placeholder-dialog)\b|qt-official-header|\.hqqt-new-head|\.header-fix',styles):errors.append('subject CSS overrides public structure')
    if re.search(r'@import|url\(\s*[\'"]?(?:https?:|//|file:)',styles,re.I):errors.append('external CSS dependency')
    if re.search(r'overflow-x\s*:\s*hidden|(?:html|body)\s*\{[^}]*overflow\s*:\s*hidden',styles,re.I):errors.append('overflow hiding masks layout')
    if re.search(r'(?:/Users/|file:///|[A-Z]:\\\\)',html):errors.append('local absolute path leaked')
    if 'html-content-layout' in html:errors.append('legacy dependency/reference leaked into page')
    if re.search(r'(?:fetch\s*\(|XMLHttpRequest|WebSocket\s*\(|https?://[^\s"<>]+\.js)', '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',subject,re.S))):errors.append('unexpected subject network runtime')
    if mode=='final':
        public=''.join(blocks(html).values()) if not errors else ''
        subject=html.replace(public,'') if public else html
        # Script may contain selector names; final DOM above is authoritative.
        if 'application/json' in html:warnings.append('check embedded JSON contains no private records')
    warnings.append('Consent authenticity, factual support, content relationships and visual composition need executor review.')
    return {'status':'fail' if errors else 'pass','mode':mode,'modules':modules,'errors':list(dict.fromkeys(errors)),
            'warnings':warnings,'not_run':['browser rendering','real device','semantic/user-evidence review']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path)
    p.add_argument('--mode',choices=['draft','refine','final'],default='draft');p.add_argument('--record',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args()
    if a.report and (a.report.resolve().is_relative_to(ROOT) or a.report.resolve() in {a.html.resolve(), a.record.resolve() if a.record else a.html.resolve()}):p.error('report must be outside skill and must not overwrite inputs')
    report=inspect(a.html.read_text(encoding="utf-8"),a.mode,json.loads(a.record.read_text(encoding="utf-8")) if a.record else None)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if a.report:a.report.write_text(text+'\n', encoding="utf-8")
    print(text);return bool(report['errors'])
if __name__=='__main__':sys.exit(main())
