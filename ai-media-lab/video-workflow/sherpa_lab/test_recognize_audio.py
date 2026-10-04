"""Portable tests: standard library plus FFmpeg; no models, network or real media required."""
import importlib.util,json,pathlib,shutil,subprocess,sys,tempfile,unittest
SCRIPT=pathlib.Path(__file__).with_name('recognize_audio.py').resolve()
spec=importlib.util.spec_from_file_location('sensevoice_cli',SCRIPT);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
class UnitTests(unittest.TestCase):
 def test_optional_reference(self):self.assertIsNone(cli.parse_args(['clip.mp3','--output','out']).reference)
 def test_null_accuracy_without_reference(self):
  r=cli.reference_score(None,'测试');self.assertIsNone(r['cer']);self.assertIsNone(r['edit_distance']);self.assertEqual(r['accuracy_status'],'unverified_no_reference')
 def test_empty_normalized_reference_rejected(self):
  for s in ['',' \n','，！']:
   with self.assertRaises(ValueError):cli.reference_score(s,'输出')
 def test_reference_normalization(self):self.assertEqual(cli.reference_score('Ａ，你 好!','a你好')['cer'],0)
 def test_reject_url_no_output(self):
  with tempfile.TemporaryDirectory() as t:
   out=pathlib.Path(t)/'out';r=subprocess.run([sys.executable,str(SCRIPT),'https://example.com/audio.wav','--output',str(out)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('local regular file',r.stderr);self.assertFalse(out.exists())
 def test_help_without_model_dependencies(self):
  r=subprocess.run([sys.executable,str(SCRIPT),'--help'],capture_output=True,text=True);self.assertEqual(r.returncode,0);self.assertIn('[reference]',r.stdout)
@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg tools required')
class ValidationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.model=self.root/'fake-model';self.model.mkdir()
  # These sentinel files are path-validation fixtures, never loaded as model weights.
  (self.model/'model.int8.onnx').write_text('not a model');(self.model/'tokens.txt').write_text('not tokens')
 def tearDown(self):self.tmp.cleanup()
 def audio(self,name='synthetic.wav'):
  p=self.root/name;subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=22050','-t','0.2',str(p)],check=True,capture_output=True);return p
 def test_mp3_probe_without_model_load(self):
  p=self.audio('synthetic.mp3');out=self.root/'out';r=cli.validate_request(p,None,out,self.model);self.assertEqual(r[-1]['codec_name'],'mp3');self.assertFalse(out.exists())
 def test_video_with_audio_probes_without_model_load(self):
  p=self.root/'synthetic_audio_video.mkv';subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=size=16x16:rate=2','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','0.5','-c:v','ffv1','-c:a','pcm_s16le',str(p)],check=True,capture_output=True);out=self.root/'out';r=cli.validate_request(p,None,out,self.model);self.assertEqual(r[-1]['codec_type'],'audio');self.assertFalse(out.exists())
 def test_missing_model_rejected_before_output(self):
  p=self.audio();out=self.root/'out'
  with self.assertRaisesRegex(ValueError,'Model asset'):cli.validate_request(p,None,out,self.root/'no-model')
  self.assertFalse(out.exists())
 def test_no_audio_rejected_before_output(self):
  p=self.root/'synthetic.mkv';subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=size=16x16:rate=2','-t','0.5','-c:v','ffv1',str(p)],check=True,capture_output=True);out=self.root/'out'
  with self.assertRaisesRegex(ValueError,'no audio track'):cli.validate_request(p,None,out,self.model)
  self.assertFalse(out.exists())
 def test_empty_reference_before_output(self):
  p=self.audio();ref=self.root/'empty.txt';ref.write_text(' \n，！');out=self.root/'out'
  with self.assertRaisesRegex(ValueError,'alphanumeric'):cli.validate_request(p,ref,out,self.model)
  self.assertFalse(out.exists())
 def test_existing_output_never_mutated(self):
  p=self.audio();out=self.root/'out';out.mkdir();(out/'sentinel').write_text('preserve')
  with self.assertRaisesRegex(ValueError,'new directory'):cli.validate_request(p,None,out,self.model)
  self.assertEqual((out/'sentinel').read_text(),'preserve')
 def test_symlink_output_rejected(self):
  p=self.audio();out=self.root/'out';out.symlink_to(self.root/'missing-target',target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'new directory'):cli.validate_request(p,None,out,self.model)
  self.assertFalse((self.root/'missing-target').exists())
 def test_shell_metacharacters_are_literal_path(self):
  p=self.audio('clip;touch SHOULD_NOT_EXIST.wav');out=self.root/'out';r=cli.validate_request(p,None,out,self.model);self.assertEqual(r[0],p.resolve());self.assertFalse((self.root/'SHOULD_NOT_EXIST.wav').exists());self.assertFalse(out.exists())
 def test_remote_manifest_protocol_is_blocked(self):
  p=self.root/'synthetic.m3u8';p.write_text('#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1,\nhttps://127.0.0.1:1/segment.ts\n#EXT-X-ENDLIST\n');out=self.root/'out'
  with self.assertRaises(ValueError):cli.validate_request(p,None,out,self.model)
  self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
