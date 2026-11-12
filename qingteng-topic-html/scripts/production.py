"""Recoverable production decisions and byte-level media checks, not semantic approval."""
from pathlib import Path
import hashlib
import struct
import zlib
import json


class AssetCache:
    """Optional local byte-inspection cache. Never stores approval or semantic results."""
    def __init__(self, directory=None):
        self.directory = Path(directory).resolve() if directory else None
        if self.directory:
            from html_support import ROOT
            if self.directory.is_relative_to(ROOT):
                raise ValueError('asset cache must be outside the Skill')
            self.directory.mkdir(parents=True, exist_ok=True)
        self.inspector = digest(__file__)
        self.memory = {}; self.images = {}; self.hits = 0; self.misses = 0

    def image(self, path):
        from html_support import image_data
        key = digest(path)
        if key not in self.images:
            self.images[key] = image_data(path)
        return self.images[key]

    def png(self, path, image_sha):
        key = image_sha + '-' + self.inspector
        if key in self.memory:
            self.hits += 1
            return self.memory[key]
        cached = self.directory / (key + '.json') if self.directory else None
        if cached and cached.is_file():
            try:
                data = json.loads(cached.read_text(encoding='utf-8')); result = data['result']
                payload = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
                if (data['image_sha256'] == image_sha and data['inspector_sha256'] == self.inspector
                        and data['payload_sha256'] == hashlib.sha256(payload).hexdigest()
                        and result['width'] > 0 and result['height'] > 0
                        and isinstance(result['has_transparency'], bool)):
                    self.memory[key] = result; self.hits += 1; return result
            except (ValueError, TypeError, KeyError, OSError):
                pass  # Corrupt/stale entries are recomputed, never accepted as a pass.
        result = inspect_png(path); self.memory[key] = result; self.misses += 1
        if cached:
            payload = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
            data = {'image_sha256': image_sha, 'inspector_sha256': self.inspector,
                    'payload_sha256': hashlib.sha256(payload).hexdigest(), 'result': result}
            import tempfile, os
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.directory, delete=False) as f:
                json.dump(data, f); name = f.name
            os.replace(name, cached)
        return result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_png(path):
    """Decode PNG scanlines using stdlib. Report real alpha, not just an alpha-capable header.

    Non-interlaced PNG, standard legal color/bit-depth combinations, all five filters.
    Unsupported interlace is explicit, never accepted as evidence of transparency.
    """
    raw = Path(path).read_bytes()
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('transparent assets require actual PNG encoding')
    offset = 8; chunks = []; ended = False
    while offset + 12 <= len(raw):
        size = struct.unpack('>I', raw[offset:offset + 4])[0]
        tag = raw[offset + 4:offset + 8]; end = offset + 8 + size
        if end + 4 > len(raw):
            raise ValueError('truncated PNG chunk')
        data = raw[offset + 8:end]
        if zlib.crc32(tag + data) & 0xffffffff != struct.unpack('>I', raw[end:end + 4])[0]:
            raise ValueError('PNG CRC mismatch')
        chunks.append((tag, data)); offset = end + 4
        if tag == b'IEND':
            ended = True; break
    if not ended or not chunks or chunks[0][0] != b'IHDR' or len(chunks[0][1]) != 13:
        raise ValueError('invalid PNG structure')
    w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunks[0][1])
    legal = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    if not w or not h or w * h > 48000000 or depth not in legal.get(color, set()):
        raise ValueError('unsupported PNG dimensions/color/depth')
    if compression or filtering or interlace:
        raise ValueError('PNG interlace/encoding not supported for alpha verification; export a non-interlaced PNG')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = (w * channels * depth + 7) // 8
    bpp = max(1, (channels * depth + 7) // 8)
    trns = next((d for t, d in chunks if t == b'tRNS'), b'')
    palette = next((d for t, d in chunks if t == b'PLTE'), b'')
    if color == 3 and (not palette or len(palette) % 3 or len(palette) // 3 > 1 << depth or len(trns) > len(palette) // 3):
        raise ValueError('invalid indexed PNG palette/transparency')
    if color in {4, 6} and trns:
        raise ValueError('PNG alpha channel cannot also contain a transparency key')
    compressed = b''.join(d for t, d in chunks if t == b'IDAT')
    decoder = zlib.decompressobj(); expected = (stride + 1) * h
    try:
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error as exc:
        raise ValueError('invalid PNG image stream') from exc
    if len(pixels) != expected or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
        raise ValueError('PNG scanline length mismatch')
    transparent = partial = visible = border_clear = border_total = 0
    bounds = [w, h, -1, -1]; previous = bytearray(stride)
    maximum = (1 << depth) - 1
    def sample(row, index):
        if depth == 16:
            return row[index * 2] * 256 + row[index * 2 + 1]
        if depth == 8:
            return row[index]
        return (row[index * depth // 8] >> (8 - depth - index * depth % 8)) & maximum
    def paeth(a, b, c):
        p = a + b - c; distances = [abs(p - a), abs(p - b), abs(p - c)]
        return [a, b, c][distances.index(min(distances))]
    for y in range(h):
        start = y * (stride + 1); kind = pixels[start]
        if kind > 4:
            raise ValueError('invalid PNG filter')
        row = bytearray(pixels[start + 1:start + 1 + stride])
        for i in range(stride):
            a = row[i - bpp] if i >= bpp else 0; b = previous[i]
            c = previous[i - bpp] if i >= bpp else 0
            predictor = (0, a, b, (a + b) // 2, paeth(a, b, c))[kind]
            row[i] = (row[i] + predictor) & 255
        for x in range(w):
            values = [sample(row, x * channels + c) for c in range(channels)]
            if color in {4, 6}:
                alpha = values[-1] / maximum
            elif color == 3:
                if values[0] >= len(palette) // 3:
                    raise ValueError('PNG palette index out of range')
                alpha = trns[values[0]] / 255 if values[0] < len(trns) else 1
            elif trns and color in {0, 2}:
                if len(trns) != channels * 2:
                    raise ValueError('invalid PNG transparency key')
                key = list(struct.unpack('>' + 'H' * channels, trns))
                alpha = 0 if values == key else 1
            else:
                alpha = 1
            transparent += alpha == 0; partial += 0 < alpha < 1; visible += alpha > 0
            if alpha > 0:
                bounds = [min(bounds[0], x), min(bounds[1], y), max(bounds[2], x), max(bounds[3], y)]
            if x in {0, w - 1} or y in {0, h - 1}:
                border_total += 1; border_clear += alpha == 0
        previous = row
    return {'format': 'PNG', 'width': w, 'height': h, 'bit_depth': depth,
            'transparent_pixels': transparent, 'partial_alpha_pixels': partial,
            'visible_pixels': visible, 'visible_bounds': bounds if visible else None,
            'clear_border_fraction': border_clear / border_total,
            'has_transparency': bool(transparent and visible),
            'notice': 'Pixel alpha verified; subject, edge quality, safe margins and fake checkerboard require visual review.'}


def validate_production(record, mode, module_ids):
    """Check declared scopes/identities; human reviewers still verify the declarations."""
    if record.get('task', {}).get('production_contract', 0) < 2:
        return
    media = {m['id']: m for m in record.get('media', [])}
    for module in record.get('modules', []):
        if module['id'] not in module_ids:
            continue
        intent = module.get('asset_intent', {})
        ids = {i for i in module.get('media', []) if media[i].get('status') != 'omitted'}
        plans = {media[i].get('plan') for i in ids}
        expected = {'none': set(), 'reuse': {'input'}, 'generate': {'generate'}, 'mixed': {'input', 'generate'}}
        if (intent.get('decision') not in expected or expected[intent['decision']] != plans
                or set(intent.get('media', [])) != ids or not intent.get('rationale') or not intent.get('purpose')
                or not isinstance(intent.get('gaps'), list)):
            raise ValueError(module['id'] + ': per-module asset decision/coverage is incomplete')
        if mode == 'final' and intent['gaps']:
            raise ValueError(module['id'] + ': unresolved illustration/evidence gap')
        links = module.get('evidence_links', [])
        if not isinstance(links, list):
            raise ValueError(module['id'] + ': evidence_links must be a list')
        for link in links:
            linked = link.get('media', [])
            if (link.get('relation') not in {'independent', 'sequence', 'before-after', 'comparison'}
                    or not linked or len(linked) != len(set(linked)) or not set(linked) <= ids
                    or not link.get('claim') or not link.get('basis') or link.get('status') not in {'supported', 'unresolved'}):
                raise ValueError(module['id'] + ': incomplete evidence relationship')
            if link['relation'] != 'independent' and len(linked) < 2:
                raise ValueError(module['id'] + ': a connected/comparative relationship needs multiple evidence items')
            if mode == 'final' and link['status'] != 'supported':
                raise ValueError(module['id'] + ': unresolved evidence relationship')
            if link['status'] == 'supported' and link['relation'] in {'sequence', 'before-after'}:
                identities = [media[i].get('evidence_identity', {}) for i in linked]
                for field in ('subject', 'task', 'work'):
                    values = [a.get(field) for a in identities]
                    if any(not isinstance(v, str) or not v.strip() for v in values) or len(set(values)) != 1:
                        raise ValueError(module['id'] + ': connected evidence must identify the same subject/task/work; use independent examples if unsupported')
        evidence_ids = {i for i in ids if media[i].get('role') == 'screenshot'}
        if evidence_ids - {i for link in links for i in link.get('media', [])}:
            raise ValueError(module['id'] + ': evidence screenshot has no explicit claim/relationship')


def asset_paths(item, task_dir):
    """Media files needed for composition AND a self-contained task snapshot."""
    result = {}
    for field in ('local_path', 'original_path'):
        if item.get(field):
            p = Path(item[field]); result[field] = p if p.is_absolute() else Path(task_dir) / p
    return result


def audit_assets(record, task_dir, mode='final', cache=None):
    """Validate actual ready files. Generation counts describe records, not service calls."""
    from html_support import image_data
    strict = record.get('task', {}).get('production_contract', 0) >= 2
    result = []
    active = {m['id'] for m in record.get('modules', []) if not m.get('removed')}
    referenced = {i for m in record.get('modules', []) if m['id'] in active for i in m.get('media', [])}
    for item in record.get('media', []):
        if item.get('module') not in active or item['id'] not in referenced or item.get('status') not in {'available', 'complete'}:
            continue
        paths = asset_paths(item, task_dir)
        if 'local_path' not in paths:
            raise ValueError(item['id'] + ': available image file missing')
        p = paths['local_path']; encoded = cache.image(p) if cache else image_data(p)
        row = {'id': item['id'], 'plan': item['plan'], 'sha256': digest(p), 'bytes': p.stat().st_size}
        if item.get('subject_region') is not None:
            box = item['subject_region']
            if (not isinstance(box, list) or len(box) != 4 or not all(type(n) in (int,float) and 0 <= n <= 1 for n in box)
                    or not (box[0] < box[2] and box[1] < box[3]) or item.get('subject_sha256') != row['sha256']):
                raise ValueError(item['id'] + ': subject_region needs normalized display-image bounds bound to its current SHA')
            row['subject_region'] = box
        if item.get('focus_region') is not None:
            box = item['focus_region']
            if (item.get('role') != 'screenshot' or not isinstance(box, list) or len(box) != 4
                    or not all(type(n) in (int, float) and 0 <= n <= 1 for n in box)
                    or not (box[0] < box[2] and box[1] < box[3])
                    or not isinstance(item.get('focus_note'), str) or not item['focus_note'].strip()
                    or not item.get('caption', '').strip()):
                raise ValueError(item['id'] + ': focus_region requires screenshot, normalized original-image bounds, focus_note and a descriptive caption')
            row['focus_region'] = box
        if strict and item['plan'] == 'generate':
            if encoded.startswith('data:image/svg+xml;'):
                raise ValueError(item['id'] + ': generated illustration requires raster output; native SVG is not image generation')
            generation = item.get('generation', {})
            if not generation.get('provider') or not generation.get('prompt') or not generation.get('artifact_sha256'):
                raise ValueError(item['id'] + ': complete generated asset requires actual provider/prompt/file fingerprint')
            if generation['artifact_sha256'] != row['sha256']:
                raise ValueError(item['id'] + ': generated artifact SHA mismatch')
            row['provider'] = generation['provider']
            if item.get('background') not in {'transparent', 'opaque'}:
                raise ValueError(item['id'] + ': decide whether the generated image needs transparent or opaque background')
        if item.get('background') == 'transparent':
            row['png'] = cache.png(p, row['sha256']) if cache else inspect_png(p)
            if not row['png']['has_transparency']:
                raise ValueError(item['id'] + ': PNG must contain both fully transparent pixels and a visible subject')
        if 'original_path' in paths:
            original = paths['original_path']; cache.image(original) if cache else image_data(original)
            derivative = item.get('derivative', {})
            if (derivative.get('original_sha256') != digest(original)
                    or derivative.get('display_sha256') != row['sha256'] or not derivative.get('note')
                    or not isinstance(derivative.get('crop'), list) or len(derivative['crop']) != 4
                    or not all(isinstance(n, (int, float)) and 0 <= n <= 1 for n in derivative['crop'])
                    or not (derivative['crop'][0] < derivative['crop'][2] and derivative['crop'][1] < derivative['crop'][3])):
                raise ValueError(item['id'] + ': display derivative needs original/display SHA, normalized crop bounds and an edit note')
            if item.get('role') != 'screenshot':
                raise ValueError(item['id'] + ': original/display variants are for evidence screenshots')
            row['original_sha256'] = digest(original)
        result.append(row)
    return {'assets': result, 'task_generated_assets': sum(a['plan'] == 'generate' for a in result),
            'generation_scope': 'Ready generated assets declared in task records; not independent verification of provider calls.'}
