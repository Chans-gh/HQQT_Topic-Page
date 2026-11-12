#!/usr/bin/env python3
"""Export existing inline display/original media without resizing or fabricating assets."""
import argparse,base64,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
from html_support import ROOT


def export_media(html_path, out):
    html_path=Path(html_path).resolve();out=Path(out).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError('media export must be a new directory outside the Skill')
    class Media(HTMLParser):
        def __init__(self):
            super().__init__();self.current=None;self.items=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='figure' and a.get('data-media-id'):
                self.current={'id':a['data-media-id']};self.items.append(self.current)
            if self.current and tag=='img':self.current['display']=a.get('src','')
            if self.current and a.get('data-qt-original-src'):self.current['original']=a['data-qt-original-src']
        def handle_endtag(self,tag):
            if tag=='figure':self.current=None
    parser=Media();parser.feed(html_path.read_text(encoding='utf-8'));files={};items=[]
    suffixes={'png':'.png','jpeg':'.jpg','gif':'.gif','webp':'.webp','svg+xml':'.svg'}
    for item in parser.items:
        row={'id':item['id']}
        for role in ('display','original'):
            uri=item.get(role)
            if not uri:continue
            m=re.fullmatch(r'data:image/(png|jpeg|gif|webp|svg\+xml);base64,([A-Za-z0-9+/=]+)',uri)
            if not m:raise ValueError(item['id']+': unsupported non-inline media')
            raw=base64.b64decode(m[2],validate=True);sha=hashlib.sha256(raw).hexdigest();name=sha+suffixes[m[1]]
            files[name]=raw;row[role]={'file':name,'sha256':sha,'bytes':len(raw)}
        if 'display' in row:
            row.setdefault('original',row['display']);items.append(row)
    out.mkdir(parents=True)
    for name,raw in files.items():(out/name).write_bytes(raw)
    report={'html_sha256':hashlib.sha256(html_path.read_bytes()).hexdigest(),'items':items,'unique_files':len(files),'total_bytes':sum(map(len,files.values())),'scope':'Exact existing inline assets; no crop, recompression, generation or approval implied.'}
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path);p.add_argument('--out-dir',type=Path,required=True);a=p.parse_args()
    try:result=export_media(a.html,a.out_dir)
    except (ValueError,OSError) as e:p.exit(1,'ERROR: '+str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
