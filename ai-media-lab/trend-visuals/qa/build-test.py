"""Fail-closed tests run on disposable copies, never changing real evidence."""
from pathlib import Path
import tempfile,shutil,subprocess,hashlib,json
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='trend-build-test-') as folder:
    dst=Path(folder);shutil.copy(ROOT/'build_data.py',dst/'build_data.py');shutil.copytree(ROOT/'inputs',dst/'inputs');(dst/'dist').mkdir();output=dst/'dist/data.json';output.write_text('sentinel')
    def run(): return subprocess.run(['python',str(dst/'build_data.py')],capture_output=True,text=True)
    baseline=dst/'inputs/v5-compiled-snapshot.json';saved=baseline.read_bytes();baseline.unlink();assert run().returncode!=0;assert output.read_text()=='sentinel'
    baseline.write_bytes(saved+b' ');assert run().returncode!=0;assert output.read_text()=='sentinel'
    baseline.write_bytes(saved);result=run();assert result.returncode==0,result.stderr;first=output.read_bytes();assert run().returncode==0;assert first==output.read_bytes()
    manifest=json.loads((dst/'inputs/manifest.json').read_text());entry=manifest['temporal_batches'][0]['comparison'];comparison=dst/entry['path'];data=json.loads(comparison.read_text());data['comparisons'][0]['changes'][0]['rankDelta']=999;comparison.write_text(json.dumps(data));entry['sha256']=hashlib.sha256(comparison.read_bytes()).hexdigest();(dst/'inputs/manifest.json').write_text(json.dumps(manifest));assert run().returncode!=0;assert output.read_bytes()==first
report={'passed':True,'checks':['missing required input blocks write','hash mismatch blocks write','deterministic same-input compilation','semantic rank mismatch blocks write','prior output remains intact on failure'],'test_target':'disposable local copies only'}
(Path(__file__).resolve().parent/'build-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
