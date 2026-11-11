"""Replace reviewed prose spans while preserving markup and Daedric glyph bytes."""
import hashlib
import re


def prose_ranges(raw):
    cursor, daedric, stack = 0, False, []
    for match in re.finditer(rb'<[^>]*>', raw):
        if not daedric:
            yield cursor, match.start()
        token = match.group()
        if re.match(rb'<\s*/\s*font\b', token, re.I):
            daedric = stack.pop() if stack else False
        elif re.match(rb'<\s*font\b', token, re.I):
            stack.append(daedric)
            face = re.search(rb'\bface\s*=\s*[\'\"]?([^\s>\'\"]+)', token, re.I)
            if face:
                daedric = b'daedric' in face[1].lower()
        cursor = match.end()
    if not daedric:
        yield cursor, len(raw)


def rewrite(raw, patches):
    ranges = list(prose_ranges(raw))
    output, cursor = [], 0
    for patch in sorted(patches, key=lambda r: r['start']):
        start, end = patch['start'], patch['end']
        if not 0 <= cursor <= start < end <= len(raw):
            raise ValueError('Overlapping or invalid book span')
        if not any(a <= start < end <= b for a, b in ranges):
            raise ValueError('Book span changes markup or a Daedric glyph run')
        old, target = raw[start:end], patch['target']
        if hashlib.sha256(old).hexdigest() != patch['source_sha256']:
            raise ValueError('Book span source hash mismatch')
        if any(c in target for c in '<>\0') or b'\0' in old or not any('\uac00' <= c <= '\ud7a3' for c in target):
            raise ValueError('Invalid book prose target')
        updated = target.encode('utf-8')
        if re.findall(rb'\r\n|\r|\n', old) != re.findall(rb'\r\n|\r|\n', updated):
            raise ValueError('Book prose line breaks changed')
        output.extend([raw[cursor:start], updated])
        cursor = end
    updated = b''.join([*output, raw[cursor:]])
    try:
        updated.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError('Repaired book field is not complete UTF-8') from error
    return updated
