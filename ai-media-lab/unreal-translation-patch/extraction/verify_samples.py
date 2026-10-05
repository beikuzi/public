"""Compare downloaded compiled resources against independent author source files."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import zlib
from locres import read

ROOT = Path(__file__).resolve().parent


def archive_entries(node, parent=''):
    namespace = '.'.join(x for x in (parent, node.get('Namespace', '')) if x)
    for entry in node.get('Children', []):
        yield namespace, entry['Key'], zlib.crc32(entry['Source']['Text'].encode('utf-32-le')), entry['Translation']['Text']
    for child in node.get('Subnamespaces', []):
        yield from archive_entries(child, namespace)


def validate_pins(root=ROOT):
    samples = json.loads((root/'samples.json').read_text())
    for sample in samples:
        for relative in sample['files']:
            path = root/'fixtures'/sample['name']/relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != sample['sha256'][relative]:
                raise ValueError(f'Pinned fixture SHA-256 mismatch: {sample["name"]}/{relative}')
    return samples


def verify():
    validate_pins()
    results = []
    output = ROOT/'results'
    output.mkdir(exist_ok=True)
    for name in ('video-example', 'easy-localization'):
        base = ROOT/'fixtures'/name
        provenance = json.loads((base/'provenance.json').read_text())
        file_hashes = {f: hashlib.sha256((base/f).read_bytes()).hexdigest() for f in provenance['files']}
        for path in sorted(base.rglob('*.locres')):
            data = read(path)
            language = path.parent.name
            if name == 'video-example':
                reference = list(archive_entries(json.loads(path.with_suffix('.archive').read_text(encoding='utf-16'))))
            else:
                with (base/'Content/Localization/TestLocA.csv').open(encoding='utf-8', newline='') as file:
                    reference = [(r['Namespace'], r['Key'], zlib.crc32(r['Key'].encode('utf-32-le')), r['lang-'+language]) for r in csv.DictReader(file)]
            actual = [(r['namespace'], r['key'], r['source_hash'], r['text']) for r in data['entries']]
            if Counter(actual) != Counter(reference):
                raise AssertionError(f'{path}: exact identity/hash/text/multiplicity mismatch')
            (output/f'{name}-{language}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            with (output/f'{name}-{language}.csv').open('w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=list(data['entries'][0]))
                writer.writeheader(); writer.writerows(data['entries'])
            results.append({'sample': name, 'engine': '5.3' if name == 'video-example' else '4.27', 'language': language, 'locres_version': data['version'], 'entries': len(actual), 'exact_match': True, 'sha256': data['sha256'], 'reference': str(path.with_suffix('.archive').relative_to(base)) if name == 'video-example' else 'Content/Localization/TestLocA.csv'})
        provenance['sha256'] = file_hashes
        (base/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    report = {'scope': 'Real author-published loose compiled localization resources; not packaged-container or runtime validation.', 'total_resources': len(results), 'total_entries': sum(r['entries'] for r in results), 'resources': results, 'not_validated': ['PAK/IoStore unpacking', 'encrypted resources', 'runtime hooks or visible text', 'raw uasset StringTable parsing', 'whole-game text coverage', 'real-world locres versions 0/1/2']}
    (output/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    verify()
