"""Entirely synthetic fixture tests; not real Bilibili comments or opinions."""
import unittest
from import_comments import normalize
class ImportTests(unittest.TestCase):
    def test_dedup_and_strip_identity(self):
        rows=[{'comment_id':'SYNTHETIC-1','text':'SYNTHETIC TEST TEXT','likes':2,'username':'SYNTHETIC-NAME','observations':[{'sort':'hot'}]}, {'id':'SYNTHETIC-1','text':'SYNTHETIC DUPLICATE'}]
        out=normalize(rows)
        self.assertEqual(len(out),1);self.assertEqual(out[0]['sampling_group'],'hot'); self.assertNotIn('username',out[0]);self.assertNotIn('primary_stance',out[0])
    def test_unknown_stays_unknown(self):
        self.assertEqual(normalize([{'id':'SYNTHETIC-2','text':'SYNTHETIC TEST'}])[0]['sampling_group'],'user_export_unknown')
    def test_missing_id_is_error(self):
        with self.assertRaises(ValueError): normalize([{'text':'SYNTHETIC TEST'}])
    def test_nontext_is_error(self):
        with self.assertRaises(ValueError): normalize([{'id':'SYNTHETIC-3','text':3}])
if __name__=='__main__': unittest.main()
