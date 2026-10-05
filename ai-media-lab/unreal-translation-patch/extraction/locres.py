"""Read-only, bounded Unreal localization resource decoder. No game execution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC = bytes.fromhex('0e147475674a03fc4a15909dc3377f1b')
MAX_FILE = 128 * 1024 * 1024


class LocresError(ValueError):
    pass


class Reader:
    def __init__(self, data, start=0, end=None):
        self.data, self.pos, self.end = data, start, len(data) if end is None else end

    def take(self, n):
        if n < 0 or n > self.end - self.pos:
            raise LocresError(f'truncated or invalid length at offset {self.pos}: {n}')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def num(self, fmt):
        return struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))[0]

    def count(self):
        n = self.num('I')
        if n > (self.end-self.pos)//4:
            raise LocresError(f'impossible count {n} at offset {self.pos-4}')
        return n

    def string(self):
        n = self.num('i')
        if n == 0:
            return ''
        wide = n < 0
        raw = self.take(abs(n)*(2 if wide else 1))
        terminator = b'\0\0' if wide else b'\0'
        if not raw.endswith(terminator):
            raise LocresError('unterminated FString')
        try:
            # Serialized non-wide FString uses ANSI bytes; only ASCII is unambiguous.
            # Fail closed for high-bit ANSI rather than silently corrupting text.
            return raw[:-len(terminator)].decode('utf-16-le' if wide else 'ascii')
        except UnicodeError as error:
            raise LocresError(f'invalid or unsupported FString encoding: {error}') from error


def parse(data):
    if len(data) > MAX_FILE:
        raise LocresError('file exceeds 128 MiB safety limit')
    r = Reader(data)
    version = 0
    pool, refs, pool_offset = [], [], None
    if data.startswith(MAGIC):
        r.take(16)
        version = r.num('B')
        if version not in (1, 2, 3):
            raise LocresError(f'unsupported version {version}')
        pool_offset = r.num('q')
        if not r.pos <= pool_offset <= len(data)-4:
            raise LocresError('invalid string-pool offset')
        p = Reader(data, pool_offset)
        for _ in range(p.count()):
            pool.append(p.string())
            refs.append(p.num('i') if version >= 2 else None)
        if p.pos != len(data):
            raise LocresError('trailing bytes after string pool')
        r.end = pool_offset
    total = r.num('I') if version >= 2 else None
    entries = []
    used = [0] * len(pool)
    for _ in range(r.count()):
        ns_hash = r.num('I') if version >= 2 else None
        namespace = r.string()
        for _ in range(r.count()):
            key_hash = r.num('I') if version >= 2 else None
            key = r.string()
            source_hash = r.num('I')
            index = r.num('i') if version else None
            if version:
                if not 0 <= index < len(pool):
                    raise LocresError('string index outside pool')
                text = pool[index]
                used[index] += 1
            else:
                text = r.string()
            entries.append({'namespace': namespace, 'key': key,
                            'source_hash': source_hash, 'text': text,
                            'namespace_hash': ns_hash, 'key_hash': key_hash,
                            'string_index': index})
    if r.pos != r.end:
        raise LocresError('trailing bytes or key/pool boundary mismatch')
    if total is not None and total != len(entries):
        raise LocresError('declared entry count mismatch')
    if version >= 2 and any(ref != -1 and ref != actual for ref, actual in zip(refs, used)):
        raise LocresError('string reference count mismatch')
    return {'format': 'unreal-locres', 'version': version,
            'sha256': hashlib.sha256(data).hexdigest(), 'entry_count': len(entries),
            'entries': entries}


def read(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise LocresError('file exceeds 128 MiB safety limit')
    return parse(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--json', type=Path, required=True)
    parser.add_argument('--csv', type=Path)
    args = parser.parse_args()
    try:
        data = read(args.input)
        for out in (args.json, args.csv):
            if out and out.resolve() == args.input.resolve():
                raise LocresError('output must not overwrite input')
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        if args.csv:
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            with args.csv.open('w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['namespace', 'key', 'source_hash', 'text', 'namespace_hash', 'key_hash', 'string_index'])
                writer.writeheader()
                writer.writerows(data['entries'])
        print(f"Extracted {data['entry_count']} entries (locres version {data['version']}).")
    except (OSError, LocresError) as error:
        print(f'Extraction failed: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
