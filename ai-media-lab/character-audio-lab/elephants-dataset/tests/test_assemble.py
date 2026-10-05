import array,copy,json,math,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import assemble as a
from dataset import write_wav
class MultiSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.wav=self.root/'source.wav';write_wav(self.wav,array.array('h',(int(1500*math.sin(i/2*2*math.pi*220/48000)) for i in range(12*48000*2))))
        self.base={'sample_rate':48000,'target_speaker':'A','sources':{'a':{'path':str(self.wav),'sha256':a.sha256(self.wav),'kind':'authored_role_labelled_production_wav','role':'A'},'m':{'path':str(self.wav),'sha256':a.sha256(self.wav),'kind':'movie_mix'},'s':{'path':str(self.wav),'sha256':a.sha256(self.wav),'kind':'contextual_separated_vocals','model_provenance':{'model':'synthetic identity test, no real separation'}}},'segments':[{'id':'u1','speaker':'A','author':{'source_id':'a','start_frame':0,'end_frame':3*48000},'movie':{'source_id':'m','start_frame':2*48000,'end_frame':5*48000},'separated':{'source_id':'s','start_frame':2*48000,'end_frame':5*48000},'speech_regions':[{'start_frame':4800,'end_frame':2*48000}],'alignment':{'accepted':True,'method':'synthetic offset'},'machine_qc_pass':True,'overlap_status':'unknown'}]}
    def tearDown(self):self.tmp.cleanup()
    def run_build(self,data=None):
        p=self.root/'config.json';p.write_text(json.dumps(data or self.base));return a.build(p,self.root/'out')
    def test_three_variants_not_triple_voice(self):
        m=self.run_build();self.assertEqual(len(m['clips']),3)
        self.assertEqual(m['statistics']['deduplicated_voice_units']['author_unique_source_seconds'],3)
        self.assertAlmostEqual(m['statistics']['deduplicated_voice_units']['machine_estimated_voice_seconds'],1.9)
        self.assertEqual(m['statistics']['clean/raw']['padding_seconds'],2)
        self.assertFalse(m['training_ready'])
    def test_separate_files_have_distinct_timebases(self):
        x=copy.deepcopy(self.base);x['sources']['a2']=dict(x['sources']['a']);x['sources']['a2']['path']=str(self.root/'other.wav');write_wav(Path(x['sources']['a2']['path']),array.array('h',(int(1000*math.sin(i/2*2*math.pi*330/48000)) for i in range(12*48000*2))));x['sources']['a2']['sha256']=a.sha256(x['sources']['a2']['path'])
        s=copy.deepcopy(x['segments'][0]);s['id']='u2';s['author']['source_id']='a2';s.pop('movie');s.pop('separated');x['segments'].append(s)
        m=self.run_build(x);self.assertEqual(m['statistics']['deduplicated_voice_units']['author_unique_source_seconds'],6)
    def test_overlapping_source_rejected(self):
        x=copy.deepcopy(self.base);s=copy.deepcopy(x['segments'][0]);s['id']='duplicate';x['segments'].append(s)
        with self.assertRaisesRegex(ValueError,'Overlapping'):self.run_build(x)
    def test_same_bytes_different_ids_do_not_duplicate_voice(self):
        x=copy.deepcopy(self.base);x['sources']['a2']=dict(x['sources']['a'])
        s=copy.deepcopy(x['segments'][0]);s['id']='u2';s['author']['source_id']='a2';s.pop('movie');s.pop('separated');x['segments'].append(s)
        with self.assertRaisesRegex(ValueError,'Overlapping'):self.run_build(x)
    def test_lossless_movie_source_supported(self):
        import subprocess
        x=copy.deepcopy(self.base);flac=self.root/'movie.flac'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.wav),str(flac)],check=True)
        x['sources']['m']['path']=str(flac);x['sources']['m']['sha256']=a.sha256(flac)
        m=self.run_build(x);self.assertEqual(m['sources']['m']['audio']['codec'],'flac')
    def test_output_qa_and_optimized_tamper_detection(self):
        import subprocess
        self.run_build();script=Path(a.__file__).with_name('verify.py')
        result=subprocess.run([sys.executable,'-O',str(script),str(self.root/'out')],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
        p=self.root/'out/clean/raw/author_0000.wav'
        with p.open('ab') as f:f.write(b'changed')
        result=subprocess.run([sys.executable,'-O',str(script),str(self.root/'out')],capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('hash mismatch',result.stderr)
    def test_symlink_source_is_rejected(self):
        x=copy.deepcopy(self.base);link=self.root/'link.wav';link.symlink_to(self.wav);x['sources']['a']['path']=str(link)
        with self.assertRaisesRegex(ValueError,'Symlink'):self.run_build(x)
    def test_wrong_authored_role_cannot_be_relabelled(self):
        x=copy.deepcopy(self.base);x['sources']['a']['role']='B'
        with self.assertRaisesRegex(ValueError,'No admitted'):self.run_build(x)
    def test_source_hash_guard(self):
        x=copy.deepcopy(self.base);x['sources']['a']['sha256']='bad'
        with self.assertRaisesRegex(ValueError,'hash'):self.run_build(x)
    def test_alignment_mismatch(self):
        x=copy.deepcopy(self.base);x['segments'][0]['movie']['end_frame']+=1
        with self.assertRaisesRegex(ValueError,'exact length'):self.run_build(x)
    def test_long_utterance_rejected_without_speech_cut(self):
        x=copy.deepcopy(self.base);x['segments'][0]['author']['end_frame']=11*48000
        with self.assertRaisesRegex(ValueError,'natural-pause'):self.run_build(x)
    def test_known_overlap_excluded(self):
        x=copy.deepcopy(self.base);x['segments'][0]['overlap_status']='known_cross_role_overlap'
        with self.assertRaisesRegex(ValueError,'No admitted'):self.run_build(x)
    def test_rename_overwrite_guard(self):
        self.run_build()
        with self.assertRaisesRegex(ValueError,'no overwrite'):self.run_build()
    def test_missing_separator_not_faked(self):
        x=copy.deepcopy(self.base);x['segments'][0].pop('separated');m=self.run_build(x)
        self.assertEqual(m['statistics']['noisy/voice_only']['clip_count'],0)
        self.assertEqual(list((self.root/'out/noisy/voice_only').iterdir()),[])
if __name__=='__main__':unittest.main()
