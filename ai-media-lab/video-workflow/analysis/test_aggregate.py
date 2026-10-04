import unittest
from aggregate_stances import aggregate
class Test(unittest.TestCase):
    def test_dedup_and_denominator(self):
        rows=[{'id':'a','primary_stance':'support','likes':10},{'id':'a','primary_stance':'support'}, {'id':'b','primary_stance':'oppose','likes':2},{'id':'c','primary_stance':None,'exclusion_reason':'spam'}]
        out=aggregate(rows,min_sample=1)
        self.assertEqual(out['deduplicated_comments'],3)
        self.assertEqual(out['included_comments'],2)
        self.assertEqual(out['stances'][0]['comment_share_pct'],50)
        self.assertEqual(out['stances'][0]['share_of_sample_likes_pct'],83.33)
    def test_small_sample_suppressed(self):
        out=aggregate([{'id':'x','primary_stance':'support'}]);self.assertEqual(out['percentage_status'],'suppressed_insufficient_sample');self.assertIsNone(out['stances'][0]['comment_share_pct'])
    def test_empty(self): self.assertEqual(aggregate([])['stances'],[])
if __name__=='__main__': unittest.main()
