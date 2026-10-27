#!/usr/bin/env python3
"""Static invariants; semantic truth, consent and visual quality remain human checks."""
import argparse, hashlib, json, re, sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from html_support import ROOT, blocks, TARGETS
from record import validate_record


class Page(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.nodes=[];self.text=[];self.stack=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        self.nodes.append((tag,dict(attrs)))
        if tag not in {'img','meta','link','input','br','hr','source','wbr','embed','area','base','col','param','track'}:self.stack.append((tag,dict(attrs)))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:];break
    def handle_data(self,data):
        if not any(t in {'script','style'} or 'data-resource-id' in a for t,a in self.stack):self.text.append(data)
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)


def inspect(html,mode='draft',record=None,review=None,review_dir=None):
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
            if mode=='final':
                if actual_sources:errors.append('final contains internal source records')
            elif expected_sources!=actual_sources:errors.append('source scope differs from record')
            expected_resources=[rid for ident in modules for rid in data['modules'][ident].get('resources',[]) if data['resources'][rid].get('status')!='omitted']
            actual_resources=[a['data-resource-id'] for _,a in page.nodes if 'data-resource-id' in a]
            if Counter(expected_resources)!=Counter(actual_resources):errors.append('resource scope/count differs from record')
            if mode=='final':
                for _,a in page.nodes:
                    if 'data-resource-id' in a and a.get('data-resource-state')!='retained-unavailable':errors.append('resource DOM state differs from final decision')
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
        if mode=='final' and (tag,a) in subject_nodes and (any(k in a for k in ('data-review-only','data-review-index','data-qt-review-toggle','data-fact-state','data-experiment')) or any(re.search(r'placeholder|pending-resource',c,re.I) for c in a.get('class','').split()) or a.get('data-resource-state') in {'pending','unresolved'} or 'data-placeholder' in a):
            errors.append('final contains review/placeholder UI')
    if mode=='final':
        if any('data-source-id' in a or set(a.get('class','').split()) & {'qt-t-citations','qt-t-sources'} for _,a in subject_nodes):
            errors.append('final contains generated audit/source UI; write necessary reader-facing attribution in the body')
        if any('data-resource-id' in a for _,a in subject_nodes) and not record:errors.append('final resource decisions require record')
        text=' '.join(page.text)
        if re.search(r'(?:视频|资源|素材).{0,12}(?:待提供|待补|占位)|(?:待提供|待补).{0,8}(?:视频|资源|素材)',text):
            errors.append('unresolved resource text prevents final, regardless of class name')
        if any(t=='video' for t,_ in subject_nodes):errors.append('real video requires separately audited media-package delivery; not certified by single-file image checker')
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
    report={'status':'fail' if errors else 'pass','scope':'static invariants only','html_sha256':hashlib.sha256(html.encode()).hexdigest(),
            'layers':{k:{'status':'not-run','reason':'requires actual rendered/semantic or independent delivery review'} for k in ('content','visual','layout','function','delivery')},'mode':mode,'modules':modules,'errors':list(dict.fromkeys(errors)),
            'warnings':warnings,'not_run':['browser rendering','real device','automated semantic/user-evidence verification']}
    if review is not None:
        apply_review(report,review,review_dir)
    return report


def apply_review(report,review,review_dir):
    """Bind executor decisions to this artifact; never infer semantic quality from text patterns."""
    try:
        if review.get('html_sha256')!=report['html_sha256']:
            raise ValueError('review belongs to a different HTML version')
        layers=review.get('layers',{})
        for name in ('content','visual'):
            layer=layers.get(name,{'status':'not-run'})
            status=layer.get('status')
            if status not in {'pass','fail','not-run'}:raise ValueError(f'{name}: invalid review status')
            if status=='pass':
                evidence=layer.get('evidence',{})
                if not layer.get('scope') or not isinstance(evidence,dict) or set(evidence)!=set(report['modules']) or not all(isinstance(v,str) and v.strip() for v in evidence.values()):
                    raise ValueError(f'{name}: pass needs scope and evidence for every rendered module')
                if name=='visual':
                    shots=layer.get('screenshots',[])
                    if not shots or review_dir is None:raise ValueError('visual: pass needs verifiable screenshot files')
                    for shot in shots:
                        path=Path(review_dir)/shot['path']
                        if hashlib.sha256(path.read_bytes()).hexdigest()!=shot['sha256']:
                            raise ValueError('visual: screenshot SHA mismatch')
            report['layers'][name]=layer
            if status=='fail':report['errors'].append(f'{name} review failed')
        report['scope']='static invariants plus version-bound executor review; review authenticity and judgment are not automated'
    except (ValueError,KeyError,TypeError,AttributeError,OSError) as exc:
        # An invalid report must never leave either semantic layer marked pass.
        for name in ('content','visual'):report['layers'][name]={'status':'not-run','reason':'invalid review evidence'}
        report['errors'].append(str(exc))
    report['status']='fail' if report['errors'] else 'pass'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path)
    p.add_argument('--mode',choices=['draft','refine','final'],default='draft');p.add_argument('--record',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--review',type=Path,help='Optional executor content/visual review JSON bound to HTML and screenshot SHA')
    a=p.parse_args()
    if a.report and (a.report.resolve().is_relative_to(ROOT) or a.report.resolve() in {p.resolve() for p in (a.html,a.record,a.review) if p}):p.error('report must be outside skill and must not overwrite inputs')
    report=inspect(a.html.read_text(encoding="utf-8"),a.mode,json.loads(a.record.read_text(encoding="utf-8")) if a.record else None,
                   json.loads(a.review.read_text(encoding='utf-8')) if a.review else None,a.review.parent if a.review else None)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if a.report:a.report.write_text(text+'\n', encoding="utf-8")
    print(text);return bool(report['errors'])
if __name__=='__main__':sys.exit(main())
