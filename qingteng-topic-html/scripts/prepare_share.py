#!/usr/bin/env python3
"""Build the share-ready copy for the Qingshui share service. Never uploads.

The service rejects <iframe>/SVG-unlisted content and its CLI image whitelist
(PNG/JPEG/GIF/WebP) refuses to download remote SVG, so before `qingshui share`:
1. inline remote images referenced by CSS url()/img src/style attributes as
   data URIs (SVG kept as data:image/svg+xml, sanitized server-side);
2. remove real <iframe> elements outside scripts (the official search layer);
3. unwrap topic zoom buttons around images, because the service removes button
   elements and may otherwise remove their descendant image as well.

Python 3.9+ standard library only. Downloads remote images only.
"""
import argparse
import base64
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIME = {'svg': 'image/svg+xml', 'png': 'image/png', 'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
URL_RE = re.compile(r"""url\(\s*(['"]?)(https?://[^)'"\s]+)\1\s*\)""")
IMG_RE = re.compile(r"""(<img\b[^>]*?\bsrc=)(['"])(https?://[^'"\s]+)\2""")
STYLE_ATTR_RE = re.compile(r"""(style=\s*['"][^'"]*?url\(\s*['"]?)(https?://[^)'"\s]+)""")
IFRAME_RE = re.compile(r'<iframe\b[^>]*>[\s\S]*?</iframe\s*>|<iframe\b[^>]*/?>')
SCRIPT_SPLIT = re.compile(r'(<script\b[^>]*>[\s\S]*?</script\s*>)')
STYLE_BLOCK_RE = re.compile(r'(<style\b[^>]*>)([\s\S]*?)(</style\s*>)', re.IGNORECASE)
SCROLL_BEHAVIOR_RE = re.compile(r'(?<![-\w])scroll-behavior\s*:\s*[^;}]+;?', re.IGNORECASE)
ZOOM_BUTTON_RE = re.compile(
    r"""<button\b(?=[^>]*\bdata-qt-zoom\b)(?:"[^"]*"|'[^']*'|[^>])*>"""
    r"""\s*(<img\b(?:"[^"]*"|'[^']*'|[^>])*>)\s*</button\s*>""",
    re.IGNORECASE,
)


def fetch(url, cache):
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (share-prep)'})
        raw = urllib.request.urlopen(req, timeout=20).read()
    except Exception as exc:
        cache[url] = ('FAIL', str(exc))
        return cache[url]
    ext = url.split('?', 1)[0].rsplit('.', 1)[-1].lower()
    mime = MIME.get(ext)
    if not mime:
        cache[url] = ('UNKNOWN-EXT', ext)
        return cache[url]
    cache[url] = ('OK', 'data:%s;base64,%s' % (mime, base64.b64encode(raw).decode('ascii')))
    return cache[url]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='delivered single-file HTML')
    parser.add_argument('--out', required=True, help='share-ready copy to create')
    parser.add_argument('--report', help='optional JSON report path')
    args = parser.parse_args()
    src, dst = Path(args.input), Path(args.out)
    if not src.is_file():
        raise SystemExit('ERROR: input not found: %s' % src)
    if src.resolve() == dst.resolve():
        raise SystemExit('ERROR: --out must differ from --input')
    if dst.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit('ERROR: refusing to write into the Skill directory')
    html = src.read_text(encoding='utf-8')
    stats = {'input': str(src), 'output': str(dst), 'inlined': 0, 'iframes_removed': 0,
             'zoom_buttons_unwrapped': 0,
             'css_declarations_removed': [],
             'downloads_failed': [], 'left_remote': [], 'blockers': []}
    cache = {}

    def swap(m):
        url = m.group(m.lastindex)
        status, payload = fetch(url, cache)
        if status != 'OK':
            if status == 'FAIL':
                stats['downloads_failed'].append('%s (%s)' % (url, payload))
            else:
                stats['left_remote'].append('%s (%s: %s)' % (url, status, payload))
            return m.group(0)
        stats['inlined'] += 1
        return m.group(0).replace(url, payload, 1)

    def clean(segment):
        def unwrap_zoom(match):
            stats['zoom_buttons_unwrapped'] += 1
            return match.group(1)

        segment = ZOOM_BUTTON_RE.sub(unwrap_zoom, segment)
        before = len(IFRAME_RE.findall(segment))
        stats['iframes_removed'] += before
        segment = IFRAME_RE.sub('', segment)
        segment = URL_RE.sub(swap, segment)
        segment = IMG_RE.sub(swap, segment)
        segment = STYLE_ATTR_RE.sub(swap, segment)

        def clean_style(match):
            css = match.group(2)
            count = len(SCROLL_BEHAVIOR_RE.findall(css))
            if count:
                stats['css_declarations_removed'].extend(['scroll-behavior'] * count)
                css = SCROLL_BEHAVIOR_RE.sub('', css)
            return match.group(1) + css + match.group(3)

        # Qingshui's CSS sanitizer treats the standards-based property name as
        # the legacy IE `behavior:` property. Scrolling still works without the
        # optional smooth-scroll hint, so remove it only from the share copy.
        segment = STYLE_BLOCK_RE.sub(clean_style, segment)
        return segment

    parts = SCRIPT_SPLIT.split(html)
    for idx in range(0, len(parts), 2):
        parts[idx] = clean(parts[idx])
    out = ''.join(parts)

    outside = SCRIPT_SPLIT.sub('', out)
    for _, url in URL_RE.findall(outside):
        stats['blockers'].append('external CSS ref: %s' % url)
    if stats['blockers']:
        stats['notice'] = 'Server rejects external CSS refs; resolve blockers, rerun prep, then share.'
    dst.write_text(out, encoding='utf-8')
    stats['bytes'] = {'input': src.stat().st_size, 'output': dst.stat().st_size}
    report = json.dumps(stats, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(report + '\n', encoding='utf-8')
    print(report)
    sys.exit(2 if stats['blockers'] else 0)


if __name__ == '__main__':
    main()
