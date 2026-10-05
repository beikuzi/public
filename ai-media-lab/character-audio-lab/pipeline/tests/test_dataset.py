import array, json, math, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dataset as d

class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.source=self.root/'source.wav'
        samples=array.array('h',(round(5000*math.sin(i/d.CHANNELS*2*math.pi*220/d.RATE)) for i in range(16*d.RATE*d.CHANNELS)))
        d.write_wav(self.source,samples)
    def tearDown(self): self.tmp.cleanup()
    def annotation(self,rows):
        path=self.root/'annotations.json'; path.write_text(json.dumps({'source_sha256':d.sha256(self.source),'timebase':'decoded_audio_seconds','target_speaker':'A','segments':rows})); return path
    def row(self,a,b,**kw):
        return dict(start=a,end=b,speaker='A',confidence=1,quality='clean',quality_evidence='Synthetic known source',overlap=False,**kw)
    def test_build_crop_stitch_padding(self):
        a=self.annotation([self.row(0,3),self.row(5,8),self.row(15.98,16)])
        m=d.build(a,self.source,self.root/'out')
        self.assertEqual(len(m['clips']),1)
        self.assertAlmostEqual(m['clips'][0]['source_interval_seconds'],6.02)
        self.assertAlmostEqual(m['clips'][0]['raw_audio']['duration_seconds'],6.26)
        self.assertEqual(m['clips'][0]['raw_audio']['channels'],2)
        self.assertEqual(m['clips'][0]['source_mappings'][-1]['end_sample'],16*d.RATE)
        self.assertEqual(m['separation']['status'],'not_run')
    def test_very_short_is_not_usable_voice(self):
        m=d.build(self.annotation([self.row(0,.01)]),self.source,self.root/'out')
        self.assertEqual(m['clips'][0]['raw_audio']['duration_seconds'],5)
        self.assertAlmostEqual(m['statistics']['clean']['trailing_padding_seconds'],4.99)
        self.assertIsNone(m['statistics']['clean']['usable_voice_seconds'])
    def test_long_utterance_quarantined(self):
        m=d.build(self.annotation([self.row(0,11)]),self.source,self.root/'out')
        self.assertFalse(m['clips']); self.assertIn('long_utterance',m['excluded'][0]['exclusion_reasons'][0])
    def test_overlap_and_low_confidence(self):
        b=self.row(2,3); b['speaker']='B'
        c=self.row(4,5); c['confidence']=.4
        m=d.build(self.annotation([self.row(1,2.5),b,c]),self.source,self.root/'out')
        self.assertFalse(m['clips']); self.assertEqual(len(m['excluded']),3)
    def test_batches_5_to_10(self):
        m=d.build(self.annotation([self.row(0,7),self.row(8,15)]),self.source,self.root/'out')
        self.assertEqual([c['raw_audio']['duration_seconds'] for c in m['clips']],[7,7])
    def test_invalid_end(self):
        with self.assertRaises(ValueError): d.build(self.annotation([self.row(15,17)]),self.source,self.root/'out')
    def test_overwrite_symlink_traversal(self):
        a=self.annotation([self.row(0,5)]); d.build(a,self.source,self.root/'out')
        with self.assertRaises(ValueError): d.build(a,self.source,self.root/'out')
        link=self.root/'link'; link.symlink_to(self.source)
        with self.assertRaises(ValueError): d.safe_path(link)
        with self.assertRaises(ValueError): d.safe_path(self.root/'sub'/'..'/'evil')
    def test_hash_binding(self):
        a=self.annotation([self.row(0,5)]); obj=json.loads(a.read_text()); obj['source_sha256']='bad'; a.write_text(json.dumps(obj))
        with self.assertRaises(ValueError): d.build(a,self.source,self.root/'out')
    def test_missing_model_no_fake_output(self):
        r=self.row(0,5); r['quality']='noisy'
        m=d.build(self.annotation([r]),self.source,self.root/'out')
        self.assertIsNone(m['clips'][0]['voice_only']); self.assertEqual(list((self.root/'out/noisy/voice_only').iterdir()),[])
    def test_import_separation_and_drift(self):
        r=self.row(0,5); r['quality']='noisy'; out=self.root/'out'; m=d.build(self.annotation([r]),self.source,out); c=m['clips'][0]
        proc=self.root/'model'; proc.mkdir(); dst=proc/'test.wav'; dst.write_bytes((out/c['raw_path']).read_bytes())
        report=self.root/'separation.json'; report.write_text(json.dumps({'outputs':[{'clip_id':c['clip_id'],'input_sha256':c['raw_sha256'],'output_path':str(dst),'model':'test identity fixture, not separator','model_version':'test','method':'synthetic pipeline integration','limitations':['no separation']}]}))
        result=d.import_separation(out,report,proc)
        self.assertEqual(result['statistics']['noisy']['processed_clip_count'],1)
        self.assertEqual(result['statistics']['noisy']['processed_file_duration_seconds'],5)
        with self.assertRaises(ValueError): d.import_separation(out,report,proc)
    def test_unknown_overlap_strict_and_provisional(self):
        r=self.row(0,5); r['overlap']=None; a=self.annotation([r])
        m=d.build(a,self.source,self.root/'strict'); self.assertFalse(m['clips'])
        p=d.build(a,self.source,self.root/'provisional',allow_unverified_overlap=True)
        self.assertTrue(p['provisional_unverified_overlap_allowed']); self.assertEqual(len(p['clips']),1)
    def test_float_separator_probe(self):
        import subprocess
        f=self.root/'float.wav'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.source),'-c:a','pcm_f32le',str(f)],check=True)
        self.assertEqual(d.wav_info(f)['duration_seconds'],16)
    def test_context_separation_before_assembly(self):
        r=self.row(1,4); r['quality']='noisy'; out=self.root/'out'
        m=d.build(self.annotation([r]),self.source,out); seg=m['clips'][0]['source_mappings'][0]
        report=self.root/'context.json'; report.write_text(json.dumps({'outputs':[{'segment_id':seg['id'],'source_sha256':m['source']['sha256'],'output_path':str(self.source),'output_source_start':0,'model':'synthetic identity fixture','model_version':'test','method':'test only','limitations':['not actual separation']}]}))
        result=d.assemble_separated_segments(out,report,self.root)
        self.assertEqual(result['clips'][0]['voice_only']['audio']['frames'],5*d.RATE)
        self.assertEqual(result['clips'][0]['voice_only']['provenance'][0]['trim_start_frame'],d.RATE)
        from verify import verify
        self.assertEqual(verify(out)['mechanical_status'],'passed')
    def test_explicit_review_quarantine(self):
        r=self.row(0,5); r['review_quarantine']=True
        m=d.build(self.annotation([r]),self.source,self.root/'out')
        self.assertFalse(m['clips']); self.assertIn('review_quarantine',m['excluded'][0]['exclusion_reasons'])
    def test_optimized_python_still_rejects_tampering(self):
        import subprocess
        out=self.root/'out'; m=d.build(self.annotation([self.row(0,5)]),self.source,out)
        raw=out/m['clips'][0]['raw_path']
        with raw.open('ab') as f: f.write(b'tampered')
        result=subprocess.run([sys.executable,'-O',str(Path(d.__file__).with_name('verify.py')),str(out)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0); self.assertIn('Raw file hash mismatch',result.stderr)
    def test_union(self): self.assertEqual(d.union_seconds([(0,3),(1,4),(6,7)]),5)
if __name__=='__main__': unittest.main()
