#!/usr/bin/env python3
"""Generate locked official-header regions from their canonical source assets."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def render(shell):
    header = ROOT/'assets/header'
    logo = 'data:image/svg+xml;base64,'+base64.b64encode((header/'logo-02.svg').read_bytes()).decode('ascii')
    avatar = 'data:image/svg+xml;base64,'+base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 50 50"><rect width="50" height="50" rx="25" fill="#eafaf4"/><circle cx="25" cy="18" r="9" fill="#09b879"/><path d="M9 45a16 16 0 0 1 32 0" fill="#09b879"/></svg>').decode('ascii')
    markup=(header/'official-header.html').read_text(encoding='utf-8').replace('QT_OFFICIAL_LOGO_DATA',logo).replace('QT_DEFAULT_AVATAR_DATA',avatar)
    shell=re.sub(r'(?s)(<!-- QT_SHARED_HEADER_START -->).*?(<!-- QT_SHARED_HEADER_END -->)',lambda m:m[1]+'\n'+markup+m[2],shell)
    style='\n'.join((header/name).read_text(encoding='utf-8') for name in ['official-header.css','header-adapter.css'])
    scripts='<script id="qt-header-jquery">'+(ROOT/'assets/vendor/jquery-1.11.3.min.js').read_text(encoding='utf-8').replace('</script','<\\/script')+'</script>\n'
    scripts+='<script id="qt-official-header-script">'+(header/'official-header.js').read_text(encoding='utf-8')+'</script>'
    for kind,content,shared in [('STYLE','<style id="qt-official-header-style">'+style+'</style>','STYLE'),('SCRIPT',scripts,'SCRIPT')]:
        start,end='<!-- QT_OFFICIAL_'+kind+'_START -->','<!-- QT_OFFICIAL_'+kind+'_END -->'
        region=start+'\n'+content+'\n'+end
        if start in shell:shell=re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda _:region,shell,flags=re.S)
        else:shell=shell.replace('<!-- QT_SHARED_'+shared+'_END -->',region+'\n<!-- QT_SHARED_'+shared+'_END -->')
    return shell


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=ROOT/'assets/templates/public-shell.html';old=path.read_text(encoding='utf-8');new=render(old)
    if args.check:
        if old!=new:raise SystemExit('Generated shell differs; run scripts/build_shell.py')
        print('Official header generated regions match source assets')
    else:
        path.write_text(new,encoding='utf-8')
        from html_support import blocks
        manifest=ROOT/'assets/provenance.json';data=json.loads(manifest.read_text(encoding='utf-8'))
        for item in data['assets']:
            if item['file'].startswith(('assets/header/','assets/vendor/')) or item['file']=='assets/templates/public-shell.html':
                item['sha256']=hashlib.sha256((ROOT/item['file']).read_bytes()).hexdigest()
        data['public_blocks_sha256']={key:hashlib.sha256(value.encode('utf-8')).hexdigest() for key,value in blocks(new).items()}
        manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Updated official header regions and provenance fingerprints')

if __name__=='__main__':main()
