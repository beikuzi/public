"""Synthetic format/security tests, not a real-game benchmark."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from pak_index import inspect, PakError, Reader, MAGIC


def u32(n): return struct.pack('<I', n)
def u64(n): return struct.pack('<Q', n)
def fstr(s):
    b=s.encode('ascii')+b'\0'
    return u32(len(b))+b


def fixture(flag=0, version=11, declared=1, entry_pos=0, payload_offset=0):
    data=b'\0'*64
    directory=u32(1)+fstr('/Game/Localization/en/')+u32(1)+fstr('Game.locres')+struct.pack('<i',entry_pos)
    encoded=u32(0xc0000000)+u32(payload_offset)+u32(4)
    lead=fstr('../../../')+u32(declared)+u64(42)+u32(0)+u32(1)
    primary_size=len(lead)+36+4+len(encoded)+4
    primary=lead+u64(64+primary_size)+u64(len(directory))+hashlib.sha1(directory).digest()+u32(len(encoded))+encoded+u32(0)
    footer=b'\0'*16+bytes([flag])+u32(MAGIC)+u32(version)+u64(64)+u64(len(primary))+hashlib.sha1(primary).digest()+b'\0'*160
    return data+primary+directory+footer


class PakIndexTests(unittest.TestCase):
    def run_data(self, data):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sample.pak';p.write_bytes(data)
            return inspect(p)

    def test_valid_index_only(self):
        report=self.run_data(fixture())
        self.assertEqual(report['locres_count'],1)
        self.assertEqual(report['locres'][0]['compression'],'none')
        self.assertEqual(report['payloads_extracted'],0)
        self.assertFalse(report['text_extraction_validated'])

    def test_encrypted_stops_before_index_read(self):
        data=bytearray(fixture(flag=1));data[64]^=0xff
        self.assertEqual(self.run_data(data)['status'],'blocked_encrypted_index')

    def test_v12_footer_recognized_without_index_claim(self):
        self.assertEqual(self.run_data(fixture(version=12))['status'],'unsupported_index_version')

    def test_invalid_flag_and_version(self):
        for data in [fixture(flag=2),fixture(version=99)]:
            with self.assertRaises(PakError):self.run_data(data)

    def test_all_truncations(self):
        data=fixture()
        for n in range(len(data)):
            with self.subTest(cut=n):
                with self.assertRaises(PakError):self.run_data(data[:n])

    def test_primary_hash_rejects_tampering(self):
        data=bytearray(fixture());data[64]^=1
        with self.assertRaisesRegex(PakError,'SHA-1'):self.run_data(data)

    def test_directory_hash_rejects_tampering(self):
        data=bytearray(fixture());data[-222]^=1
        with self.assertRaisesRegex(PakError,'SHA-1'):self.run_data(data)

    def test_metadata_bounds_counts(self):
        for args in [{'declared':2},{'entry_pos':99999},{'entry_pos':-1},{'payload_offset':999}]:
            with self.subTest(args=args):
                with self.assertRaises(PakError):self.run_data(fixture(**args))

    def test_index_offset_and_size_bounds(self):
        for offset,size in [(10**12,1),(64,10**12)]:
            data=bytearray(fixture());struct.pack_into('<QQ',data,len(data)-221+25,offset,size)
            with self.assertRaises(PakError):self.run_data(data)

    def test_string_bounds_and_encoding(self):
        for data in [struct.pack('<i',-2147483648),u32(2)+b'xx',u32(2)+b'\xff\0']:
            with self.assertRaises(PakError):Reader(data).string()

    def test_replay_has_source_side_baseline(self):
        root=Path(__file__).resolve().parent
        baseline=json.loads((root/'expected-inspections.json').read_text())
        hashes=json.loads((root/'expected-paks.json').read_text())
        self.assertEqual(len(baseline),16)
        self.assertEqual({r['file'] for r in baseline},{r['file'] for r in hashes})
        self.assertTrue(all('/' not in r['file'] and '\\' not in r['file'] for r in baseline))
        self.assertTrue(all(r['payloads_extracted']==0 and not r['text_extraction_validated'] for r in baseline))
        replay=(root/'replay_local.py').read_text()
        self.assertIn("with_name('expected-inspections.json')",replay)
        self.assertNotIn("/'results'/",replay)

    def test_cli_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'sample.pak';p.write_bytes(fixture());out=root/'out.json';out.write_text('retain')
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('pak_index.py')),str(p),'--json',str(out)],capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(out.read_text(),'retain')


if __name__=='__main__':unittest.main()
