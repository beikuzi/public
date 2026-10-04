import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import render

class PipelineSafetyTests(unittest.TestCase):
 def setUp(self):self.project=json.loads((render.ROOT/'project.json').read_text())
 def test_valid_project(self):render.validate_project(self.project)
 def test_empty_narration(self):
  for value in [[],[''],['   '],['\n']]:
   with self.subTest(value=value):
    p=copy.deepcopy(self.project);p['slides'][0]['lines']=value
    with self.assertRaises(ValueError):render.validate_project(p)
 def test_long_text(self):
  for field,value in [('title','一'*9),('note','一'*25),('keyword','三个字')]:
   p=copy.deepcopy(self.project);p['slides'][0][field]=value
   with self.assertRaises(ValueError):render.validate_project(p)
  p=copy.deepcopy(self.project);p['slides'][0]['cards'][0][1]='一'*21
  with self.assertRaises(ValueError):render.validate_project(p)
  p=copy.deepcopy(self.project);p['slides'][0]['lines']=['一'*31]
  with self.assertRaises(ValueError):render.validate_project(p)
 def test_markup_remote_assets_and_css_injection(self):
  for field,value in [('title','<img src=x>'),('note','https://example.com/a'),('keyword','<x'),('accent','#fff;url(https://x)')]:
   p=copy.deepcopy(self.project);p['slides'][0][field]=value
   with self.assertRaises(ValueError):render.validate_project(p)
  p=copy.deepcopy(self.project);p['slides'][0]['asset']='https://example.com/a'
  with self.assertRaises(ValueError):render.validate_project(p)
 def test_bad_paths(self):
  for name in ['','..','../escape','/tmp/video','output:evil','a/../../b',"a'b",'.venv']:
   with self.subTest(name=name):
    with self.assertRaises(ValueError):render.prepare_output(name)
 def test_nonempty_and_owned_overwrite(self):
  with tempfile.TemporaryDirectory() as d,patch.object(render,'ROOT',pathlib.Path(d)):
   root=pathlib.Path(d);foreign=root/'foreign';foreign.mkdir();(foreign/'important.txt').write_text('keep')
   with self.assertRaises(ValueError):render.prepare_output('foreign')
   with self.assertRaises(ValueError):render.prepare_output('foreign',True)
   self.assertEqual((foreign/'important.txt').read_text(),'keep')
   own=render.prepare_output('owned');(own/'test.txt').write_text('keep')
   with self.assertRaises(ValueError):render.prepare_output('owned')
   self.assertEqual(render.prepare_output('owned',True),own)
   (root/'file').write_text('not a directory')
   with self.assertRaises(ValueError):render.prepare_output('file')
   (root/'link').symlink_to(own,target_is_directory=True)
   with self.assertRaises(ValueError):render.prepare_output('link',True)
 def test_html_is_self_contained(self):
  markup=render.make_html(self.project)
  self.assertNotIn('<script',markup);self.assertNotIn('src=',markup);self.assertNotIn('url(',markup)
  self.assertIn('合成旁白 · eSpeak-NG 中文机械音',markup)

if __name__=='__main__':unittest.main(verbosity=2)
