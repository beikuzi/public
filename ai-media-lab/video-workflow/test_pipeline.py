"""Portable tests: synthesize local fixtures, require only FFmpeg and Pillow."""
import hashlib,json,pathlib,shutil,subprocess,sys,tempfile,unittest
from pipeline import norm,reserve_output
from quality_gates import assess
SCRIPT=pathlib.Path(__file__).with_name('pipeline.py').resolve()
class UnitTests(unittest.TestCase):
 def test_normalization(self): self.assertEqual(norm('ＡＢＣ，你 好!'),'abc你好')
 def test_no_silent_translation(self):self.assertNotEqual(norm('歡迎'),norm('欢迎'))
 def test_empty_blocks(self):self.assertEqual(assess('')['status'],'blocked')
 def test_repetition_blocks(self):self.assertIn('high_repetition_possible_hallucination',assess('可以嗎？'*13)['blocking_flags'])
 def test_nonempty_stays_unverified(self):self.assertEqual(assess('乘客您好，开往国家图书馆站方向的列车即将到站。')['status'],'unverified_requires_review')
 def test_refuse_nonempty_directory(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=pathlib.Path(tmp);(path/'evidence').write_text('preserve')
   with self.assertRaises(ValueError):reserve_output(path)
   self.assertEqual((path/'evidence').read_text(),'preserve')
@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg tools required')
class PortableIntegrationTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def fixture(self,name,seconds=2,offset=0):
  path=self.root/name;cmd=['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i','testsrc2=size=160x120:rate=5','-t',str(seconds),'-c:v','ffv1']
  if offset:cmd+=['-output_ts_offset',str(offset)]
  subprocess.run(cmd+[str(path)],check=True,capture_output=True);return path
 def invoke(self,video,out,*args):return subprocess.run([sys.executable,str(SCRIPT),str(video),'--output',str(out),*args],capture_output=True,text=True)
 def test_short_no_audio_has_initial_frame(self):
  video=self.fixture('synthetic_silent_2s.mkv');out=self.root/'run';r=self.invoke(video,out,'--offline')
  self.assertEqual(r.returncode,0,r.stderr);result=json.loads((out/'results.json').read_text());self.assertEqual(result['asr_status'],'unavailable_no_audio_track');self.assertEqual(result['uniform_count'],1);self.assertTrue((out/'contact_sheet.jpg').exists());self.assertFalse((out/'audio.wav').exists())
  index=json.loads((out/'frame_index.json').read_text());self.assertEqual(index[0]['source_pts_seconds'],0)
  manifest=json.loads((out/'run_manifest.json').read_text());self.assertEqual(manifest['source']['sha256'],hashlib.sha256(video.read_bytes()).hexdigest());self.assertEqual(manifest['pipeline_version'],'2.0.0');self.assertEqual(manifest['status'],'completed')
 def test_repeat_output_rejected_without_mutation(self):
  longer=self.fixture('synthetic_long12s.mkv',12);shorter=self.fixture('synthetic_short1s.mkv',1);out=self.root/'run'
  first=self.invoke(longer,out,'--frames-only');self.assertEqual(first.returncode,0,first.stderr)
  before={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()};second=self.invoke(shorter,out,'--frames-only');self.assertNotEqual(second.returncode,0);self.assertIn('new or empty directory',second.stderr)
  after={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()};self.assertEqual(before,after)
  index=json.loads((out/'frame_index.json').read_text());self.assertEqual([r['source_pts_seconds'] for r in index if r['kind']=='uniform'],[0,10])
 def test_source_pts_offset_preserved(self):
  video=self.fixture('synthetic_offset2s.mkv',2,2);out=self.root/'run';r=self.invoke(video,out,'--frames-only');self.assertEqual(r.returncode,0,r.stderr)
  row=json.loads((out/'frame_index.json').read_text())[0];self.assertEqual(row['source_pts_seconds'],2);self.assertEqual(row['video_relative_seconds'],0);self.assertIn('source_pts',row);self.assertEqual(row['source_time_base'],'1/1000')
if __name__=='__main__':unittest.main()
