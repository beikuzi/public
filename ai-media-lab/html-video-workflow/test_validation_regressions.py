import hashlib,json,pathlib,shutil,subprocess,tempfile,unittest
from unittest.mock import patch
import render,validate
from safe_io import write_text
ROOT=pathlib.Path(__file__).parent

class OutputEscapeRegressions(unittest.TestCase):
 def test_marker_symlink_does_not_mutate_external_sentinel(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);project=base/'project';project.mkdir();out=project/'owned';out.mkdir()
   sentinel=base/'sentinel.json';original='{"owner":"html-video-workflow","important":"preserve"}';sentinel.write_text(original)
   (out/render.MARKER).symlink_to(sentinel)
   with patch.object(render,'ROOT',project),self.assertRaises(ValueError):render.prepare_output('owned',True)
   self.assertEqual(sentinel.read_text(),original)
 def test_all_generated_symlinks_rejected_before_marker_write(self):
  names=['slides.html','slides.pdf','slide-1.png','narration.wav','narration.txt','subtitles.srt','subtitles.vtt','timing.json','concat.txt','clip-1.mp4','visuals.mp4','demo.mp4','ffprobe.json','benchmark.json','validation.json','check-1.png']
  for name in names:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    base=pathlib.Path(d);project=base/'project';project.mkdir();sentinel=base/'sentinel';sentinel.write_bytes(b'unchanged')
    with patch.object(render,'ROOT',project):
     out=render.prepare_output('owned');marker=(out/render.MARKER).read_bytes();(out/name).symlink_to(sentinel)
     with self.assertRaises(ValueError):render.prepare_output('owned',True)
     self.assertEqual((out/render.MARKER).read_bytes(),marker)
    self.assertEqual(sentinel.read_bytes(),b'unchanged')
 def test_dangling_nested_and_hardlink_outputs_rejected(self):
  for kind in ['dangling','nested','hardlink']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    base=pathlib.Path(d);project=base/'project';project.mkdir()
    with patch.object(render,'ROOT',project):
     out=render.prepare_output('owned')
     if kind=='dangling':(out/'demo.mp4').symlink_to(base/'missing')
     elif kind=='nested':
      (out/'nested').mkdir();(out/'nested'/'escape').symlink_to(base/'missing')
     else:
      sentinel=base/'sentinel';sentinel.write_bytes(b'keep');(out/'demo.mp4').hardlink_to(sentinel)
     with self.assertRaises(ValueError):render.prepare_output('owned',True)
 def test_atomic_writer_rejects_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);sentinel=root/'sentinel';sentinel.write_text('keep');link=root/'report';link.symlink_to(sentinel)
   with self.assertRaises(ValueError):write_text(link,'bad')
   self.assertEqual(sentinel.read_text(),'keep')

class LiveMediaRegressions(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  # Synthetic, model-free fixture: a four-second color video and sine-wave WAV.
  # No historical demonstration files are required or bundled.
  cls.fixture_tmp=tempfile.TemporaryDirectory();cls.fixture=pathlib.Path(cls.fixture_tmp.name)
  cls.addClassCleanup(cls.fixture_tmp.cleanup)
  subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4','-c:a','pcm_s16le',str(cls.fixture/'narration.wav')],check=True)
  subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=navy:s=1280x720:r=30:d=4','-i',str(cls.fixture/'narration.wav'),'-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-t','4',str(cls.fixture/'demo.mp4')],check=True)
  scenes=[dict(slide=i+1,start=i,end=i+1,frames=30) for i in range(4)]
  cues=[dict(slide=i+1,start=i+.18,end=i+.8,text=f'Synthetic cue {i+1}') for i in range(4)]
  (cls.fixture/'timing.json').write_text(json.dumps(dict(fps=30,scenes=scenes,cues=cues)))
  srt='';vtt='WEBVTT\n\n'
  for i in range(4):
   text=f'Synthetic cue {i+1}'
   srt+=f'{i+1}\n00:00:0{i},180 --> 00:00:0{i},800\n{text}\n\n'
   vtt+=f'00:00:0{i}.180 --> 00:00:0{i}.800\n{text}\n\n'
  (cls.fixture/'subtitles.srt').write_text(srt);(cls.fixture/'subtitles.vtt').write_text(vtt)
  (cls.fixture/'ffprobe.json').write_bytes(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(cls.fixture/'demo.mp4')]))
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)/'media';self.root.mkdir()
  for name in ['demo.mp4','narration.wav','timing.json','subtitles.srt','subtitles.vtt','ffprobe.json']:
   shutil.copyfile(self.fixture/name,self.root/name)
 def tearDown(self):self.tmp.cleanup()
 def remux(self,arguments):
  target=self.root/'changed.mp4';subprocess.run(['ffmpeg','-y','-v','error',*arguments,str(target)],check=True);target.replace(self.root/'demo.mp4')
 def test_fresh_probe_ignores_invalid_cache(self):
  (self.root/'ffprobe.json').write_text('this is not JSON')
  result=validate.validate_directory(self.root)
  self.assertEqual(result['checks'],'PASS');self.assertEqual(result['media_sha256'],hashlib.sha256((self.root/'demo.mp4').read_bytes()).hexdigest())
 def test_missing_audio_fails_despite_original_cache_and_source_wav(self):
  self.remux(['-i',str(self.root/'demo.mp4'),'-map','0:v','-c','copy'])
  with self.assertRaisesRegex(ValueError,'one video and one audio'):validate.validate_directory(self.root)
 def test_silent_mux_fails_despite_valid_source_wav(self):
  self.remux(['-i',str(self.root/'demo.mp4'),'-f','lavfi','-i','anullsrc=r=48000:cl=mono','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-t','4'])
  with self.assertRaisesRegex(ValueError,'silent'):validate.validate_directory(self.root)
 def test_cue_outside_live_media_fails(self):
  path=self.root/'timing.json';t=json.loads(path.read_text());t['cues'][-1]['end']=100;path.write_text(json.dumps(t))
  with self.assertRaisesRegex(ValueError,'Cue overlaps or exceeds'):validate.validate_directory(self.root)
 def test_subtitle_desync_fails(self):
  path=self.root/'subtitles.srt';text=path.read_text();path.write_text(text.replace('00:00:00,180','00:00:00,000',1))
  with self.assertRaisesRegex(ValueError,'Subtitle sidecar'):validate.validate_directory(self.root)
 def test_validator_input_and_output_links_preserve_sentinel(self):
  for name in ['demo.mp4','timing.json','narration.wav','validation.json','verified-ffprobe.json','check-1.png']:
   with self.subTest(name=name):
    target=self.root/name;backup=target.read_bytes() if target.exists() else None
    if target.exists():target.unlink()
    sentinel=pathlib.Path(self.tmp.name)/'sentinel';sentinel.write_bytes(b'preserve');target.symlink_to(sentinel)
    with self.assertRaises(ValueError):validate.validate_directory(self.root)
    self.assertEqual(sentinel.read_bytes(),b'preserve');target.unlink()
    if backup is not None:target.write_bytes(backup)

if __name__=='__main__':unittest.main(verbosity=2)
