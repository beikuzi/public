import tempfile,unittest
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from separate import separate,read_audio
class SeparationTests(unittest.TestCase):
 def test_center_exact(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'in.wav';b=Path(d)/'out.wav';x=np.zeros((4801,6),np.float32);x[:,2]=np.linspace(-.5,.5,len(x));wavfile.write(a,48000,x)
   r=separate(a,b,'center');sr,y=wavfile.read(b)
   self.assertEqual(sr,48000);self.assertEqual(len(y),4801);np.testing.assert_array_equal(y,x[:,2]);self.assertFalse(r['target_character_isolated'])
 def test_reject_stereo_as_real_center(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'in.wav';wavfile.write(a,44100,np.zeros((4410,2),np.float32))
   with self.assertRaises(ValueError):separate(a,Path(d)/'out.wav','center')
 def test_pcm16_to_float(self):
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'in.wav';wavfile.write(a,16000,np.array([-32768,0,32767],np.int16));sr,x=read_audio(a)
   self.assertEqual(sr,16000);self.assertEqual(x.shape,(3,1));self.assertEqual(x[0,0],-1.)
if __name__=='__main__':unittest.main()
