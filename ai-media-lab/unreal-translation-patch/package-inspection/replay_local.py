"""Replay inspections against already acquired legal local PAKs, enforcing hashes."""
import argparse
import hashlib
import json
from pathlib import Path
from pak_index import inspect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    expected=json.loads(Path(__file__).with_name('expected-paks.json').read_text())
    baseline_records=json.loads((Path(__file__).with_name('expected-inspections.json')).read_text())
    baselines={r['file']:{k:v for k,v in r.items() if k!='sha256'} for r in baseline_records}
    reports=[]
    for record in expected:
        path=args.directory/record['file']
        if path.stat().st_size != record['file_bytes']:
            raise ValueError(f'File size mismatch: {path.name}')
        digest=hashlib.sha256()
        with path.open('rb') as file:
            for block in iter(lambda:file.read(1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=record['sha256']:
            raise ValueError(f'Pinned SHA-256 mismatch: {path.name}')
        report=inspect(path)
        for key in ('pak_version','encrypted_index','status'):
            if report[key] != record[key]:
                raise ValueError(f'Inspection mismatch: {path.name}: {key}')
        if report != baselines.get(path.name):
            raise ValueError(f'Full metadata replay mismatch: {path.name}')
        reports.append(report)
    print(json.dumps({'verified_paks':len(reports),'payloads_extracted':0,'text_extraction_validated':False,'reports':reports},indent=2))


if __name__=='__main__':main()
