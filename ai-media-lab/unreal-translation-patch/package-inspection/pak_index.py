"""Bounded read-only PAK index inspection. Does NOT extract or decompress payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC = 0x5A6F12E1
MAX_INDEX_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 1_000_000


class PakError(ValueError):
    pass


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def take(self, n):
        if n < 0 or self.pos < 0 or n > len(self.data)-self.pos:
            raise PakError('truncated index or invalid field length')
        value = self.data[self.pos:self.pos+n]
        self.pos += n
        return value

    def num(self, fmt):
        return struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))[0]

    def count(self):
        n = self.num('I')
        if n > MAX_ENTRIES or n > (len(self.data)-self.pos)//4:
            raise PakError('impossible index count')
        return n

    def string(self):
        length = self.num('i')
        if length == 0:
            return ''
        wide = length < 0
        raw = self.take(abs(length)*(2 if wide else 1))
        term = b'\0\0' if wide else b'\0'
        if not raw.endswith(term):
            raise PakError('unterminated path FString')
        try:
            text = raw[:-len(term)].decode('utf-16-le' if wide else 'ascii')
        except UnicodeError as error:
            raise PakError('invalid/ambiguous path encoding') from error
        if '\0' in text:
            raise PakError('embedded NUL in path')
        return text

    def finish(self):
        if self.pos != len(self.data):
            raise PakError('trailing index bytes')


def encoded_entry(data, pos, compression_names, data_end):
    if not 0 <= pos <= len(data)-4:
        raise PakError('encoded entry offset outside table')
    r = Reader(data, pos)
    bits = r.num('I')
    compression = (bits >> 23) & 63
    encrypted = bool(bits & (1 << 22))
    block_count = (bits >> 6) & 65535
    block_size = bits & 63
    block_size = r.num('I') if block_size == 63 else block_size << 11
    offset = r.num('I' if bits & (1 << 31) else 'Q')
    uncompressed = r.num('I' if bits & (1 << 30) else 'Q')
    compressed = uncompressed if compression == 0 else r.num('I' if bits & (1 << 29) else 'Q')
    if compression > len(compression_names):
        raise PakError('unknown compression slot')
    header_size = 53 + (4+16*block_count if compression else 0)
    if offset > data_end or header_size + compressed > data_end-offset:
        raise PakError('entry payload bounds exceed data region')
    if compression == 0 and block_count:
        raise PakError('uncompressed entry has compression blocks')
    if compression and not block_count:
        raise PakError('compressed entry missing blocks')
    if block_count > 1 or (block_count and encrypted):
        # Consume and bound serialized block-length metadata without decoding bytes.
        sizes = [r.num('I') for _ in range(block_count)]
        if not encrypted and sum(sizes) != compressed:
            raise PakError('compressed block sizes mismatch')
    return {'offset': offset, 'compressed_bytes': compressed,
            'uncompressed_bytes': uncompressed, 'compression':
            'none' if compression == 0 else compression_names[compression-1],
            'encrypted_payload': encrypted, 'compression_blocks': block_count,
            'compression_block_size': block_size}


def inspect(path):
    path = Path(path)
    size = path.stat().st_size
    if size < 221:
        raise PakError('file too short for supported PAK footer')
    with path.open('rb') as file:
        file.seek(size-221)
        footer = file.read(221)
        flag = footer[16]
        magic, version = struct.unpack_from('<II', footer, 17)
        if magic != MAGIC or version not in (11, 12):
            raise PakError('unsupported footer layout; only standard v11/v12 footer recognized')
        if flag not in (0, 1):
            raise PakError('invalid encrypted-index flag')
        offset, index_size = struct.unpack_from('<QQ', footer, 25)
        footer_offset = size-221
        if offset > footer_offset or index_size > footer_offset-offset:
            raise PakError('index bounds exceed archive')
        report = {'format': 'unreal-pak-index-inspection', 'file': path.name,
                  'file_bytes': size, 'pak_version': version,
                  'encrypted_index': bool(flag), 'index_offset': offset,
                  'index_bytes': index_size, 'payloads_extracted': 0,
                  'text_extraction_validated': False}
        if flag:
            report['status'] = 'blocked_encrypted_index'
            return report
        if version != 11:
            report['status'] = 'unsupported_index_version'
            return report
        names = []
        for i in range(5):
            raw = footer[61+i*32:93+i*32].split(b'\0',1)[0]
            try:
                names.append(raw.decode('ascii'))
            except UnicodeError as error:
                raise PakError('invalid compression name') from error

        def checked_region(start, length, expected):
            if length > MAX_INDEX_BYTES or start > footer_offset or length > footer_offset-start:
                raise PakError('index region outside bounds or safety limit')
            file.seek(start)
            data = file.read(length)
            if len(data) != length or hashlib.sha1(data).digest() != expected:
                raise PakError('index SHA-1 mismatch')
            return data

        primary = checked_region(offset, index_size, footer[41:61])
        r = Reader(primary)
        mount = r.string()
        declared = r.num('I')
        if declared > MAX_ENTRIES:
            raise PakError('too many declared entries')
        seed = r.num('Q')
        indexes = {'primary': {'offset': offset, 'bytes': index_size, 'sha1_verified': True}}
        directory_data = None
        for kind in ('path_hash', 'directory'):
            present = r.num('I')
            if present not in (0,1):
                raise PakError('invalid optional-index flag')
            if present:
                start, length, digest = r.num('Q'), r.num('Q'), r.take(20)
                data = checked_region(start, length, digest)
                indexes[kind] = {'offset': start, 'bytes': length, 'sha1_verified': True}
                if kind == 'directory':
                    directory_data = data
        encoded = r.take(r.num('I'))
        nonencoded = r.num('I')
        if nonencoded:
            raise PakError('non-encoded entries unsupported; no partial report')
        r.finish()
        if directory_data is None:
            raise PakError('full directory index absent; cannot enumerate names')
        d = Reader(directory_data)
        entries = []
        names_seen = set()
        pruned = 0
        for _ in range(d.count()):
            directory = d.string()
            for _ in range(d.count()):
                name, entry_pos = d.string(), d.num('i')
                if entry_pos == -2147483648:
                    pruned += 1
                    continue
                if entry_pos < 0:
                    raise PakError('unsupported non-encoded entry reference')
                path_name = directory.lstrip('/')+name
                if path_name in names_seen:
                    raise PakError('duplicate directory-index path')
                names_seen.add(path_name)
                meta = encoded_entry(encoded, entry_pos, names, offset)
                if path_name.lower().endswith('.locres'):
                    entries.append({'path': path_name, **meta})
        d.finish()
        if len(names_seen)+pruned != declared:
            raise PakError('directory entry count differs from declared count')
        report.update(status='index_inspected_payloads_not_decoded', mount_point=mount,
                      declared_entry_count=declared, enumerated_entry_count=len(names_seen),
                      pruned_entries=pruned, index_regions=indexes,
                      locres_count=len(entries), locres=entries)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pak', type=Path)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.pak)
        result = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
        if args.json:
            # Exclusive create: never overwrite source or existing user output.
            with args.json.open('x', encoding='utf-8') as file:
                file.write(result)
        print(result, end='')
        return 0 if report['status'].startswith('index_inspected') else 3
    except (OSError, PakError) as error:
        print(f'PAK inspection failed: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__': sys.exit(main())
