import unittest
from crop_qc import clipped_union,screen

class CropQCTest(unittest.TestCase):
    def test_union_clips_and_avoids_double_counting(self):
        r=clipped_union([{'start_seconds':0,'end_seconds':3},{'start_seconds':2,'end_seconds':7}],1,6)
        self.assertEqual(r,[{'start_seconds':1,'end_seconds':6}])
    def test_disjoint(self):
        r=clipped_union([{'start_seconds':0,'end_seconds':1},{'start_seconds':3,'end_seconds':4}],0,5)
        self.assertEqual(sum(x['end_seconds']-x['start_seconds'] for x in r),2)
    def test_valid_pass(self):
        self.assertTrue(screen(8,7,0,12,True,-55)['machine_screen_pass'])
    def test_noisy_or_unknown_proxy_fails(self):
        for value in [None,float('nan'),float('inf'),-49]:
            self.assertFalse(screen(8,7,0,12,True,value)['machine_screen_pass'])
    def test_gates_fail_independently(self):
        for args in [(4,3,0,12,True,-55),(8,3,0,12,True,-55),(8,7,1,12,True,-55),(8,7,0,5,True,-55),(8,7,0,12,False,-55)]:
            self.assertFalse(screen(*args)['machine_screen_pass'])
    def test_known_alternate_fails(self):
        self.assertFalse(screen(8,7,0,12,True,-55,True)['machine_screen_pass'])
    def test_invalid_duration_rejected(self):
        for duration,vad in [(0,0),(float('nan'),0),(5,6),(5,-1)]:
            with self.assertRaises(ValueError):screen(duration,vad,0,6,True,-55)
    def test_bad_crop_rejected(self):
        for a,b in [(1,0),(1,1),(0,float('inf'))]:
            with self.assertRaises(ValueError):clipped_union([],a,b)
if __name__=='__main__':unittest.main()
