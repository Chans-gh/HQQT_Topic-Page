"""HTML fragment and resource helpers; not a general rendering framework."""
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import base64, mimetypes, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SHARED = ('HEADER', 'FOOTER', 'STYLE', 'SCRIPT', 'DIALOG')
TARGETS = {'home','search','learning','login','course-yijian','course-economist','course-safety',
           'live','books','about','contact','brand-story','consult','after-sales','help'}
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


def blocks(html):
    result = {}
    for name in SHARED:
        pattern = rf'<!-- QT_SHARED_{name}_START -->.*?<!-- QT_SHARED_{name}_END -->'
        matches = re.findall(pattern, html, re.S)
        if len(matches) != 1:
            raise ValueError(f'exactly one shared {name} required')
        result[name] = matches[0]
    return result


def json_text(value):
    import json
    return json.dumps(value, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def image_data(path):
    path = Path(path)
    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in {'image/png','image/jpeg','image/webp','image/svg+xml','image/gif'}:
        raise ValueError('unsupported image format')
    if mime == 'image/svg+xml':
        root = ET.fromstring(raw)
        for node in root.iter():
            if node.tag.rsplit('}',1)[-1] in {'script','foreignObject'}:
                raise ValueError('active SVG content forbidden')
            if node.tag.rsplit('}',1)[-1] == 'style' and re.search(r'@import|url\s*\(|expression\s*\(|javascript:', ''.join(node.itertext()), re.I):
                raise ValueError('active/external SVG stylesheet forbidden')
            for key, value in node.attrib.items():
                key = key.rsplit('}',1)[-1].lower()
                if key.startswith('on') or (key in {'href','src'} and not value.startswith('#')) or 'url(' in value.lower():
                    raise ValueError('external/active SVG resource forbidden')
    return f'data:{mime};base64,' + base64.b64encode(raw).decode()


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def render(self):
        if self.tag == '_root':
            return ''.join(c.render() if isinstance(c, Node) else escape(c) for c in self.children)
        attrs = ''.join(' '+escape(k,quote=True)+(f'="{escape(str(v),quote=True)}"' if v is not None else '') for k,v in self.attrs.items())
        content = ''.join(c.render() if isinstance(c, Node) else escape(c) for c in self.children)
        return f'<{self.tag}{attrs}>' + ('' if self.tag in VOID else content+f'</{self.tag}>')

    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.walk()


class Fragment(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node('_root'); self.stack = [self.root]
        self.feed(html); self.close()
        if len(self.stack) != 1:
            raise ValueError('unclosed fragment elements')

    def handle_starttag(self, tag, attrs):
        if tag in {'script','style','iframe','object','embed','base','link','meta','html','head','body','main'}:
            raise ValueError(f'forbidden fragment tag: {tag}')
        if len(attrs) != len(dict(attrs)):
            raise ValueError('duplicate attributes')
        for k,v in attrs:
            if k.startswith('on') or k in {'style','srcdoc','srcset','formaction','action'}:
                raise ValueError(f'unsafe fragment attribute: {k}')
            if k in {'href','src','poster'} and v:
                value = re.sub(r'[\x00-\x20]+','',v).lower()
                if not (value.startswith(('#','https://','http://','data:image/'))):
                    raise ValueError(f'unsafe URL in {k}')
        n = Node(tag,dict(attrs)); self.stack[-1].children.append(n)
        if tag not in VOID:self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag,attrs)
        if tag not in VOID:self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError(f'unbalanced fragment: {tag}')
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def handle_comment(self, data):
        if 'QT_SHARED_' in data:raise ValueError('shared markers forbidden in body')
