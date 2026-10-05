import unittest
from audit import wer,intersect
from summarize import summarize
class AuditTests(unittest.TestCase):
 def test_text(self):self.assertEqual(wer('Thank you.', 'thank you'),0);self.assertEqual(wer('Scales','scars'),1)
 def test_clipping(self):
  r=intersect([{'start_sample':0,'end_sample':200},{'start_sample':300,'end_sample':400}],100,350)
  self.assertEqual(r,[{'start_sample':100,'end_sample':200},{'start_sample':300,'end_sample':350}])
 def test_short_caption_quarantine(self):
  r=summarize({'complete':True,'segments':[{'id':'a','target':True,'speaker_label':'Sintel','caption':'Scales','context_start_sample':0,'caption_start_sample':0,'caption_end_sample':48000,'signals':{'center':{'caption_wer':0,'caption_overlap_speech_seconds':1,'flags':[],'speech_regions':[]}}}]})
  self.assertEqual(r['proposals'][0]['proposal_status'],'quarantine_ambiguous');self.assertIsNone(r['proposals'][0]['overlap'])
class HardeningTests(unittest.TestCase):
 def test_production_checks_are_not_asserts(self):
  import ast
  from pathlib import Path
  for name in ('audit.py','reconcile_words.py','validate_results.py'):
   tree=ast.parse((Path(__file__).parent/name).read_text())
   self.assertFalse(any(isinstance(n,ast.Assert) for n in ast.walk(tree)),name)
 def test_guards_survive_optimized_python(self):
  import subprocess,sys,os
  from pathlib import Path
  code="""
import audit,sys,tempfile
from pathlib import Path
checks=0
try: audit.require_sample_rate(16000)
except ValueError: checks+=1
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'fake.jit';p.write_bytes(b'not vendor weights')
 try: audit.require_vendor_hash(p,audit.VAD_SHA256)
 except ValueError: checks+=1
sys.modules['onnxruntime']=object()
try: audit.require_local_runtime()
except ValueError: checks+=1
if checks!=3: raise RuntimeError('Optimized Python bypassed a safety guard')
print('All 3 guards reject invalid inputs under -O')
"""
  env=dict(os.environ);env['PYTHONPATH']=str(Path(__file__).resolve().parent)+os.pathsep+env.get('PYTHONPATH','')
  result=subprocess.run([sys.executable,'-O','-c',code],env=env,text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn('All 3 guards',result.stdout)
if __name__=='__main__':unittest.main()

