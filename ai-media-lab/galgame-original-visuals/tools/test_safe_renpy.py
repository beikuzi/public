"""Synthetic, asset-free standard-library security/regression tests."""
import json
import os
from pathlib import Path
import pickle
import stat
import tempfile
import unittest
import zlib
from safe_renpy import RPA3, UnsafeData, bounded_zlib, safe_name, safe_pickle, script_records


def archive(path, members, mutate=None):
    key=0xC001CAFE
    data=bytearray(b'RPA-3.0 0000000000000000 c001cafe\n')
    index={}
    for name,content in members.items():
        # Verify prefix accounting against total member length.
        prefix,body=content[:2],content[2:]
        index[name]=[(len(data)^key,len(content)^key,prefix.decode('latin1'))]
        data.extend(body)
    if mutate: mutate(index,key)
    offset=len(data)
    data[:34]=f'RPA-3.0 {offset:016x} {key:08x}\n'.encode()
    data.extend(zlib.compress(pickle.dumps(index,protocol=2)))
    path.write_bytes(data)
    return path


class SafePickleTests(unittest.TestCase):
    def test_primitive_roundtrip(self):
        value={'hello':[(4,9,'xy')], 'other':None, 'boolean':True}
        for protocol in (0,1,2,3,4):
            self.assertEqual(safe_pickle(pickle.dumps(value,protocol=protocol))[0],value)
    def test_reject_globals_and_execution(self):
        examples=[
            b'cos\nsystem\n.', # GLOBAL
            b'R.', # REDUCE
            b'b.', # BUILD
            b'\x81.', # NEWOBJ
            b'\x92.', # NEWOBJ_EX
            b'ibuiltins\nlist\n.', # INST
            b'o.', # OBJ
            b'Psecret\n.', # PERSID
            b'Q.', # BINPERSID
            b'\x82\x01.', # EXT1
            b'\x83\x01\x00.', # EXT2
            b'\x84\x01\x00\x00\x00.', # EXT4
            b'\x93.', # STACK_GLOBAL
            b'\x97.', # NEXT_BUFFER
        ]
        for payload in examples:
            with self.subTest(payload=payload),self.assertRaises(UnsafeData): safe_pickle(payload)
    def test_inert_mode_does_not_allow_arbitrary_global(self):
        with self.assertRaises(UnsafeData): safe_pickle(b'cos\nsystem\n.',inert_ast=True)
        with self.assertRaises(UnsafeData): safe_pickle(b'cbuiltins\neval\n.',inert_ast=True)
    def test_inert_renpy_class(self):
        payload=b'\x80\x02crenpy.ast\nSay\n)\x81}X\x04\x00\x00\x00whatX\x05\x00\x00\x00Hellosb.'
        root,nodes=safe_pickle(payload,inert_ast=True)
        self.assertEqual(root.state['what'],'Hello')
        self.assertEqual(root.symbol.name,'Say')
        self.assertEqual(len(nodes),1)
        with self.assertRaises(UnsafeData): safe_pickle(payload)
    def test_malformed_and_trailing(self):
        for payload in (b'',b'N',b'N.N',b'NN.',b'h\xff.',b'\x80\x02q\x01.',b'(N.'):
            with self.subTest(payload=payload),self.assertRaises(UnsafeData): safe_pickle(payload)
    def test_decompression_limit(self):
        with self.assertRaises(UnsafeData): bounded_zlib(zlib.compress(b'a'*10000),limit=100)
        with self.assertRaises(UnsafeData): bounded_zlib(zlib.compress(b'abc')[:-1])
        with self.assertRaises(UnsafeData): bounded_zlib(zlib.compress(b'abc')+b'extra')
        self.assertEqual(bounded_zlib(zlib.compress(b'abc')+b'x'*16,allow_digest=True),b'abc')


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_read_prefix_and_extract(self):
        p=archive(self.root/'a.rpa',{'images/a.png':b'example-image','sfx/a.ogg':b'audio'})
        a=RPA3(p)
        self.assertEqual(a.read('images/a.png'),b'example-image')
        output=a.extract(['images/a.png'],self.root/'out')
        self.assertEqual(Path(output[0]).read_bytes(),b'example-image')
        self.assertFalse((self.root/'out/sfx/a.ogg').exists())
        self.assertEqual(stat.S_IMODE(Path(output[0]).stat().st_mode),0o600)
        with self.assertRaises(FileExistsError): a.extract(['images/a.png'],self.root/'out')
    def test_no_global_in_index(self):
        p=self.root/'bad.rpa'; p.write_bytes(b'RPA-3.0 0000000000000022 00000000\n'+zlib.compress(b'cos\nsystem\n.'))
        with self.assertRaises(UnsafeData): RPA3(p)
    def test_code_is_opt_in_and_never_executed(self):
        p=archive(self.root/'a.rpa',{'script.py':b'raise Exception("must never execute")'})
        a=RPA3(p)
        with self.assertRaises(UnsafeData): a.extract(['script.py'],self.root/'out')
        a.extract(['script.py'],self.root/'out',allow_code=True)
        self.assertEqual((self.root/'out/script.py').read_bytes(),b'raise Exception("must never execute")')
        self.assertEqual(stat.S_IMODE((self.root/'out/script.py').stat().st_mode),0o600)
    def test_bad_paths(self):
        for name in ('../x','/x','a/../x','C:/x','a\\x','a//x','a/./x','a/','a\x00b','CON.txt','a/NUL','a.','a '):
            with self.subTest(name=name),self.assertRaises(UnsafeData): safe_name(name)
            p=archive(self.root/'bad.rpa',{name:b'data'})
            with self.assertRaises(UnsafeData): RPA3(p)
    def test_collision(self):
        for names in ({'A.png':b'aa','a.png':b'aa'},{'a':b'aa','a/b':b'aa'}):
            with self.assertRaises(UnsafeData): RPA3(archive(self.root/'a.rpa',names))
    def test_offset_outside_data(self):
        def mutate(i,k): i['a']=[(10000000^k,100^k,'')]
        with self.assertRaises(UnsafeData): RPA3(archive(self.root/'a.rpa',{'a':b'example'},mutate))
    def test_prefix_exceeds_length(self):
        def mutate(i,k): i['a']=[(34^k,1^k,'toolong')]
        with self.assertRaises(UnsafeData): RPA3(archive(self.root/'a.rpa',{'a':b'example'},mutate))
    def test_symlink_member_parent(self):
        a=RPA3(archive(self.root/'a.rpa',{'nested/a.png':b'example'}))
        (self.root/'out').mkdir(); (self.root/'outside').mkdir()
        (self.root/'out/nested').symlink_to(self.root/'outside',target_is_directory=True)
        with self.assertRaises(OSError): a.extract(['nested/a.png'],self.root/'out')
        self.assertFalse((self.root/'outside/a.png').exists())
    def test_symlink_destination(self):
        a=RPA3(archive(self.root/'a.rpa',{'a.png':b'example'}))
        (self.root/'outside').mkdir(); (self.root/'out').symlink_to(self.root/'outside',target_is_directory=True)
        with self.assertRaises(UnsafeData): a.extract(['a.png'],self.root/'out')
    def test_unknown_exact_name(self):
        a=RPA3(archive(self.root/'a.rpa',{'a.png':b'example'}))
        with self.assertRaises(UnsafeData): a.extract(['*.png'],self.root/'out')
        with self.assertRaises(UnsafeData): a.extract([],self.root/'out')

if __name__=='__main__': unittest.main()
