"""Fetch only pinned public MIT sample data; verify SHA-256, execute nothing."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent


def main():
    for sample in json.loads((ROOT/'samples.json').read_text()):
        repo = sample['repository'].removeprefix('https://github.com/')
        base = ROOT/'fixtures'/sample['name']
        for relative in sample['files']:
            expected = sample['sha256'][relative]
            output = base/relative
            if output.exists() and hashlib.sha256(output.read_bytes()).hexdigest() == expected:
                continue
            url = f"https://raw.githubusercontent.com/{repo}/{sample['commit']}/{relative}"
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read(1024*1024+1)
            if len(data)>1024*1024 or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'Fixture integrity failure: {relative}')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        (base/'provenance.json').write_text(json.dumps({k:v for k,v in sample.items() if k!='name'}, indent=2)+'\n')
        print(f"Verified sample data: {sample['name']} @ {sample['commit']}")


if __name__ == '__main__': main()
