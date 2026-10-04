"""Synthetic importer-to-aggregator regressions; no collected comments or network."""
import importlib.util,json,pathlib,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from comment_likes import parse_likes
spec=importlib.util.spec_from_file_location('comment_importer',ROOT/'bilibili/import_comments.py');importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
spec=importlib.util.spec_from_file_location('comment_aggregator',ROOT/'analysis/aggregate_stances.py');aggregator=importlib.util.module_from_spec(spec);spec.loader.exec_module(aggregator)
def row(i,**kwargs):return {'id':f'SYNTHETIC-{i}','text':'SYNTHETIC TEST ONLY','primary_stance':'support',**kwargs}
class LikeParsingTests(unittest.TestCase):
 def test_observed_nonnegative_integer(self):
  for source,expected in [(0,0),(7,7),('0',0),(' 12 ',12),('001',1)]:
   with self.subTest(source=source):self.assertEqual(parse_likes(source),{'value':expected,'status':'observed','reason':None})
 def test_unknown_remains_unknown(self):
  for value in [None,'',' \t\n']:
   with self.subTest(value=value):self.assertEqual(parse_likes(value)['status'],'unknown');self.assertIsNone(parse_likes(value)['value'])
 def test_malformed_never_becomes_zero(self):
  for value in [True,False,-1,1.0,1.5,float('nan'),float('inf'),'1.0','1.5','-1','1e3','NaN','1,000','many','+2','１２',[],{},'9'*5000]:
   with self.subTest(type=type(value).__name__):self.assertEqual(parse_likes(value)['status'],'invalid');self.assertIsNone(parse_likes(value)['value'])
class PipelineTests(unittest.TestCase):
 def test_audit_missing_likes_repro(self):
  normalized=importer.normalize([row(1)]);self.assertIsNone(normalized[0]['likes']);self.assertEqual(normalized[0]['likes_status'],'unknown')
  out=aggregator.aggregate(normalized,min_sample=1);self.assertEqual(out['likes_coverage']['unknown_comments'],1);self.assertIsNone(out['stances'][0]['likes_received']);self.assertIsNone(out['stances'][0]['share_of_sample_likes_pct'])
 def test_null_and_zero_are_distinct(self):
  out=aggregator.aggregate(importer.normalize([row(1,likes=None),row(2,likes=0)]),1);cov=out['likes_coverage'];self.assertEqual(cov['observed_comments'],1);self.assertEqual(cov['unknown_comments'],1);self.assertEqual(cov['observed_likes_total'],0);self.assertIsNone(cov['complete_sample_likes_total']);self.assertEqual(out['like_share_status'],'suppressed_incomplete_likes_coverage')
 def test_all_observed_zero_has_undefined_share(self):
  out=aggregator.aggregate(importer.normalize([row(1,likes=0),row(2,likes='0')]),1);self.assertEqual(out['likes_coverage']['status'],'complete');self.assertEqual(out['likes_coverage']['complete_sample_likes_total'],0);self.assertEqual(out['like_share_status'],'suppressed_zero_observed_likes');self.assertEqual(out['stances'][0]['likes_received'],0)
 def test_valid_complete_likes_share(self):
  out=aggregator.aggregate(importer.normalize([row(1,likes='8'),row(2,likes=2,primary_stance='oppose')]),1);self.assertEqual(out['like_share_status'],'display_sample_only');self.assertEqual(out['stances'][0]['share_of_sample_likes_pct'],80)
 def test_incomplete_likes_does_not_suppress_comment_shares(self):
  out=aggregator.aggregate(importer.normalize([row(1,likes=10),row(2,likes=None,primary_stance='oppose')]),1);self.assertEqual(out['percentage_status'],'display_sample_only');self.assertEqual([s['comment_share_pct'] for s in out['stances']],[50,50]);self.assertTrue(all(s['share_of_sample_likes_pct'] is None for s in out['stances']));self.assertEqual(out['likes_coverage']['observed_comment_pct'],50)
 def test_invalid_metadata_survives_import(self):
  normalized=importer.normalize([row(1,likes='many'),row(2,likes=True)]);out=aggregator.aggregate(normalized,1);self.assertEqual(out['likes_coverage']['invalid_comments'],2);self.assertEqual(out['likes_coverage']['unknown_comments'],0);self.assertIsNone(out['likes_coverage']['observed_likes_total'])
 def test_direct_malformed_aggregator(self):
  out=aggregator.aggregate([row(1,likes=2.5),row(2,likes=-8)],1);self.assertEqual(out['likes_coverage']['invalid_comments'],2)
 def test_exclusion_reason_survives_import(self):
  out=aggregator.aggregate(importer.normalize([row(1,likes=1),row(2,primary_stance=None,exclusion_reason='synthetic_spam')]),1);self.assertEqual(out['exclusion_reasons'],{'synthetic_spam':1});self.assertEqual(out['likes_coverage']['eligible_comments'],1);self.assertEqual(out['likes_coverage']['status'],'complete')
 def test_dedup_does_not_impute_later_likes(self):
  out=aggregator.aggregate(importer.normalize([row(1),row(1,likes=9)]),1);self.assertEqual(out['included_comments'],1);self.assertEqual(out['likes_coverage']['unknown_comments'],1)
 def test_direct_cli_json_and_jsonl(self):
  for extension in ['json','jsonl']:
   with self.subTest(extension=extension),tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp);source=root/f'synthetic.{extension}';rows=[row(1),row(2,likes=0),row(3,likes='bad'),row(4,primary_stance=None,exclusion_reason='synthetic_spam')]
    source.write_text(json.dumps(rows) if extension=='json' else '\n'.join(json.dumps(r) for r in rows));normalized=root/'normalized.json';output=root/'summary.json'
    first=subprocess.run([sys.executable,str(ROOT/'bilibili/import_comments.py'),str(source),'--out',str(normalized)],capture_output=True,text=True);self.assertEqual(first.returncode,0,first.stderr)
    second=subprocess.run([sys.executable,str(ROOT/'analysis/aggregate_stances.py'),str(normalized),str(output),'--min-sample','1'],capture_output=True,text=True);self.assertEqual(second.returncode,0,second.stderr)
    out=json.loads(output.read_text());self.assertEqual(out['likes_coverage']['observed_comments'],1);self.assertEqual(out['likes_coverage']['unknown_comments'],1);self.assertEqual(out['likes_coverage']['invalid_comments'],1);self.assertEqual(out['like_share_status'],'suppressed_incomplete_likes_coverage');self.assertEqual(out['exclusion_reasons'],{'synthetic_spam':1})
if __name__=='__main__':unittest.main()
