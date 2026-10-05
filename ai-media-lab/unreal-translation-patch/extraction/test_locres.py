import json
from pathlib import Path
import struct
import unittest
from locres import MAGIC, LocresError, Reader, parse
from verify_samples import verify


def integer(x): return struct.pack('<I', x)
def string(s):
    b = (s+'\0').encode('utf-16-le')
    return struct.pack('<i', -len(b)//2)+b


def fixture(version=3):
    # Synthetic only: independent layout bytes exercise unicode and duplicate identities/text.
    texts = ['你好，{PlayerName}！\n得分：{Score} 🎮', '同文', '同文']
    body = (integer(3) if version >= 2 else b'')+integer(1)
    body += (integer(123) if version >= 2 else b'')+string('測試')+integer(3)
    for i, text in enumerate(texts):
        body += (integer(456+i) if version >= 2 else b'')+string('key'+str(i))+integer(900+i)
        body += integer(i) if version else string(text)
    if not version: return body
    pool = integer(3)+b''.join(string(s)+(integer(1) if version >= 2 else b'') for s in texts)
    return MAGIC+bytes([version])+struct.pack('<q',25+len(body))+body+pool


class ExtractionTests(unittest.TestCase):
    def test_real_resources_exact_reference(self):
        r = verify()
        self.assertEqual((r['total_resources'],r['total_entries']), (5,17))

    def test_unicode_placeholders_duplicates_versions(self):
        for version in range(4):
            with self.subTest(version=version):
                entries = parse(fixture(version))['entries']
                self.assertEqual(len(entries), 3)
                self.assertEqual(entries[0]['text'], '你好，{PlayerName}！\n得分：{Score} 🎮')
                self.assertEqual(entries[1]['text'], entries[2]['text'])
                self.assertNotEqual(entries[1]['key'],entries[2]['key'])
                self.assertEqual(json.loads(json.dumps(entries, ensure_ascii=False).encode('utf-8')) , entries)

    def test_every_truncation_rejected(self):
        for version in range(4):
            data=fixture(version)
            for cut in range(len(data)):
                with self.subTest(version=version, cut=cut):
                    with self.assertRaises(LocresError): parse(data[:cut])

    def test_negative_or_out_of_bounds_offset(self):
        for offset in (-1, 0, 24, 10**9):
            data=bytearray(fixture());struct.pack_into('<q',data,17,offset)
            with self.assertRaises(LocresError):parse(data)

    def test_invalid_version_and_counts(self):
        data=bytearray(fixture());data[16]=99
        with self.assertRaises(LocresError):parse(data)
        data=bytearray(fixture());struct.pack_into('<I',data,25,999)
        with self.assertRaises(LocresError):parse(data)
        data=bytearray(fixture());struct.pack_into('<I',data,29,0xffffffff)
        with self.assertRaises(LocresError):parse(data)

    def test_bad_string_index(self):
        data=bytearray(fixture());r=Reader(data,33);r.num('I');r.string();r.num('I');r.num('I');r.string();r.num('I')
        struct.pack_into('<i',data,r.pos,-1)
        with self.assertRaises(LocresError):parse(data)

    def test_malformed_utf16_and_terminator(self):
        for raw in (struct.pack('<i',-2)+b'\x00\xd8\0\0', struct.pack('<i',2)+b'ab', struct.pack('<i',-2147483648)):
            with self.assertRaises(LocresError):Reader(raw).string()

    def test_empty_legacy(self):
        self.assertEqual(parse(integer(0))['entries'],[])

    def test_trailing_garbage(self):
        with self.assertRaises(LocresError):parse(fixture()+b'x')


if __name__ == '__main__': unittest.main()
