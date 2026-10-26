#!/usr/bin/env python3
"""Export this committed product only. Prepare by default; push is an explicit subcommand."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

PACKAGE = Path(__file__).resolve().parents[1]


def git(root, *args, data=None):
    p = subprocess.run(['git','-C',str(root),*args], input=data, capture_output=True, check=True)
    return p.stdout


def snapshot(expected_head, ref='HEAD'):
    root = Path(git(PACKAGE,'rev-parse','--show-toplevel').decode('utf-8').strip())
    config = json.loads((PACKAGE/'distribution.json').read_text(encoding='utf-8'))
    prefix = PACKAGE.relative_to(root).as_posix()
    branch = git(root,'branch','--show-current').decode('utf-8').strip()
    allowed_branch = config['branch'] if prefix=='.' else config['authoring_branch']
    if branch != allowed_branch:
        raise ValueError('Wrong authoring branch: '+branch)
    if git(root,'status','--porcelain'):
        raise ValueError('Working tree must be clean; commit the intended changes first')
    commit = git(root,'rev-parse',ref+'^{commit}').decode().strip()
    if commit != git(root,'rev-parse','HEAD').decode().strip():
        raise ValueError('Only the current committed HEAD may be exported')
    prefix = '' if prefix=='.' else prefix
    tree_ref = commit+(':'+prefix if prefix else '^{tree}')
    tree = git(root,'rev-parse',tree_ref).decode().strip()
    rows = git(root,'ls-tree','-rz',tree_ref).split(b'\0')
    entries = []
    for row in rows:
        if not row: continue
        meta, raw_path = row.split(b'\t',1)
        mode, kind, sha = meta.decode().split(' ')
        path = raw_path.decode('utf-8')
        parts = Path(path).parts
        if kind!='blob' or mode not in {'100644','100755'}:
            raise ValueError('Symlink/submodule is not distributable: '+path)
        if not any(path==a or (a.endswith('/') and path.startswith(a)) for a in config['allowed_roots']):
            raise ValueError('File is outside product allowlist: '+path)
        if any(x in {'..','.git','node_modules','__pycache__','dist','__MACOSX'} or x.startswith('._') for x in parts):
            raise ValueError('Generated or unsafe path: '+path)
        if any(x=='.env' or x.startswith('.env.') or x.endswith(('.pem','.key','.p12')) for x in parts):
            raise ValueError('Potential credential file: '+path)
        raw = git(root,'cat-file','blob',sha)
        entries.append({'path':path,'mode':mode,'type':'blob','sha':sha,
                        'content_base64':base64.b64encode(raw).decode('ascii')})
    paths = {x['path'] for x in entries}
    if not {'README.md','distribution.json',config['skill_directory']+'/SKILL.md'}.issubset(paths):
        raise ValueError('Missing distribution entrypoints')
    if not re.fullmatch(r'[0-9a-f]{40}',expected_head):
        raise ValueError('--expected-head must be the exact last audited remote commit SHA')
    return {'schema':'qingteng-github-export/1','repository':config['repository'],'branch':config['branch'],
            'expected_head':expected_head,'source_commit':commit,'source_tree':tree,
            'entries':entries,'note':'Git blobs only; no local branch history or governance files exported'}


def existing_token(root):
    for name in ('GH_TOKEN','GITHUB_TOKEN'):
        if os.environ.get(name): return os.environ[name]
    if shutil.which('gh'):
        p = subprocess.run(['gh','auth','token','--hostname','github.com'], capture_output=True, text=True)
        if p.returncode==0 and p.stdout.strip(): return p.stdout.strip()
    p = subprocess.run(['git','-C',str(root),'credential','fill'], input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True, env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
    values = dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    if values.get('password'): return values['password']
    raise ValueError('No existing GitHub credential. Use the Codex GitHub connector with the prepared manifest, or authenticate with an account already allowed to write this repository. Never paste tokens into chat.')


class Github:
    def __init__(self, repository, token):
        self.base = 'https://api.github.com/repos/'+repository
        self.headers = {'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'qingteng-skill-sync'}
    def call(self, method, route, payload=None):
        raw = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(self.base+route, data=raw, method=method,
                                     headers={**self.headers,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=45) as response: return json.load(response)
        except urllib.error.HTTPError as exc:
            try: message=json.load(exc).get('message','GitHub rejected request')
            except ValueError: message='GitHub rejected request'
            raise ValueError('GitHub HTTP '+str(exc.code)+': '+message+'. No credentials are printed. Check repository access or use the Codex connector.') from None


def publish(payload, api):
    branch = payload['branch']
    head = api.call('GET','/git/ref/heads/'+branch)['object']['sha']
    if head!=payload['expected_head']:
        raise ValueError('Remote head changed; audit remote changes before preparing another export')
    entries = []
    for item in payload['entries']:
        # Recheck the manifest's Git blob identity before transmission.
        raw = base64.b64decode(item['content_base64'],validate=True)
        sha = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if sha!=item['sha']: raise ValueError('Manifest blob checksum mismatch: '+item['path'])
        blob = api.call('POST','/git/blobs',{'encoding':'base64','content':item['content_base64']})
        if blob['sha']!=sha: raise ValueError('Remote blob mismatch: '+item['path'])
        entries.append({k:item[k] for k in ('path','mode','type','sha')})
    tree = api.call('POST','/git/trees',{'tree':entries})['sha']
    if tree!=payload['source_tree']: raise ValueError('Remote tree differs from the committed product')
    current = api.call('GET','/git/ref/heads/'+branch)['object']['sha']
    if current!=head: raise ValueError('Remote advanced while uploading; branch was not updated')
    message = '同步环球青藤专题页Skill已提交源文件\n\nSource commit: '+payload['source_commit']
    commit = api.call('POST','/git/commits',{'message':message,'tree':tree,'parents':[head]})['sha']
    api.call('PATCH','/git/refs/heads/'+branch,{'sha':commit,'force':False})
    actual = api.call('GET','/git/ref/heads/'+branch)['object']['sha']
    if actual!=commit: raise ValueError('Unable to confirm remote branch head')
    return {'repository':payload['repository'],'branch':branch,'commit':commit,
            'source_commit':payload['source_commit'],'tree':tree,'files':len(entries),'verified':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','push'])
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--out',type=Path,help='Manifest path outside the source repository')
    parser.add_argument('--ref',default='HEAD')
    args = parser.parse_args()
    payload = snapshot(args.expected_head,args.ref)
    if args.action=='prepare':
        if not args.out: parser.error('prepare requires --out')
        root = Path(git(PACKAGE,'rev-parse','--show-toplevel').decode().strip())
        if args.out.resolve().is_relative_to(root): raise ValueError('Export manifest must be outside the source repository')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':'prepared','manifest':str(args.out),'source_commit':payload['source_commit'],
                          'source_tree':payload['source_tree'],'files':len(payload['entries']),'network_calls':0},ensure_ascii=False))
    else:
        result = publish(payload,Github(payload['repository'],existing_token(PACKAGE)))
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.CalledProcessError,urllib.error.URLError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr);sys.exit(1)
