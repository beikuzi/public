"""Evaluate only independently timestamped ASR words overlapping caption; never prompt ASR."""
import json
from pathlib import Path
from audit import wer, SR
p = Path(__file__).resolve().parent / 'audit.json'
r = json.loads(p.read_text())
if not r['complete']:
    raise ValueError("Audit validation failed: r['complete']")
for s in r['segments']:
    for v in s['signals'].values():
        v['context_caption_wer'] = v['caption_wer']
        v['caption_asr_text'] = ' '.join((w['word'].strip() for seg in v['asr_segments'] for w in seg.get('words', []) if s['caption_start_sample'] <= s['context_start_sample'] + (w['start'] + w['end']) / 2 * SR < s['caption_end_sample']))
        v['caption_wer'] = wer(s['caption'], v['caption_asr_text'])
p.write_text(json.dumps(r, indent=2))
