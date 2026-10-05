import tempfile, unittest
from pathlib import Path
from process_segments import validate_segments, prepare_output_directory
class SegmentSafetyTests(unittest.TestCase):
 def make(self, identifier='clip_01', start=1., end=2.):
  return {'segments':[{'id':identifier,'start':start,'end':end,'target':True,'quality':'noisy'}]}
 def test_quarantine_never_selected(self):
  a=self.make();a['segments'][0]['review_quarantine']=True
  with self.assertRaises(ValueError):validate_segments(a,10,1,True)
 def test_unknown_explicit_opt_in(self):
  a=self.make();a['segments'][0]['quality']='unknown'
  with self.assertRaises(ValueError):validate_segments(a,10,1)
  self.assertEqual(len(validate_segments(a,10,1,True)),1)
  self.assertEqual(a['segments'][0]['quality'],'unknown')
 def test_valid(self):self.assertEqual(len(validate_segments(self.make(),10,1)),1)
 def test_reject_path_ids(self):
  for bad in ['../escape','/tmp/escape','a/b','a\\b','.','..','a.wav','', 'x'*129]:
   with self.subTest(bad=bad),self.assertRaises(ValueError):validate_segments(self.make(bad),10,1)
 def test_reject_duplicate(self):
  a=self.make();a['segments']*=2
  with self.assertRaises(ValueError):validate_segments(a,10,1)
 def test_reject_bad_times(self):
  for start,end in [(-1,2),(3,2),(0,11),(float('nan'),2),(1,float('inf')),(True,2)]:
   with self.subTest(start=start,end=end),self.assertRaises(ValueError):validate_segments(self.make(start=start,end=end),10,1)
 def test_reject_bad_context(self):
  for c in [-1,31,float('nan'),float('inf')]:
   with self.subTest(c=c),self.assertRaises(ValueError):validate_segments(self.make(),10,c)
 def test_nonempty_output_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'existing').write_text('keep')
   with self.assertRaises(ValueError):prepare_output_directory(p)
   self.assertEqual((p/'existing').read_text(),'keep')
 def test_empty_output_allowed(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(prepare_output_directory(d),Path(d).resolve())
 def test_symlink_output_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'real').mkdir();(p/'link').symlink_to(p/'real',target_is_directory=True)
   with self.assertRaises(ValueError):prepare_output_directory(p/'link')
if __name__=='__main__':unittest.main()
