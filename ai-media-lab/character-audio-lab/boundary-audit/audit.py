"""Independent local speech activity and ASR; captions are evaluation text only."""
import sys, json, time, hashlib, re, difflib, importlib.metadata
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'deps'))
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import torch
from silero_vad import load_silero_vad, get_speech_timestamps
import whisper
SR = 48000
VAD_SHA256 = 'e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require_sample_rate(rate):
    if rate != SR:
        raise ValueError(f'Expected {SR} Hz, got {rate}')

def require_vendor_hash(path, expected):
    if sha(path) != expected:
        raise ValueError('Unexpected Silero vendor model checksum')

def require_local_runtime():
    if 'onnxruntime' in sys.modules:
        raise ValueError('ONNX runtime must not be imported')

def norms(s):
    return re.findall('[a-z]+', s.lower().replace('’', "'"))

def wer(a, b):
    a, b = (norms(a), norms(b))
    d = list(range(len(b) + 1))
    for i, x in enumerate(a):
        z = [i + 1]
        for j, y in enumerate(b):
            z.append(min(z[-1] + 1, d[j + 1] + 1, d[j] + (x != y)))
        d = z
    return d[-1] / max(1, len(a))

def crop(path, start, end, channel=None):
    with sf.SoundFile(path) as f:
        require_sample_rate(f.samplerate)
        f.seek(start)
        x = f.read(end - start, dtype='float32', always_2d=True)
    return x[:, channel] if channel is not None else x.mean(axis=1)

def intersect(regions, a, b):
    return [{'start_sample': max(a, r['start_sample']), 'end_sample': min(b, r['end_sample'])} for r in regions if min(b, r['end_sample']) > max(a, r['start_sample'])]

def infer(x, origin, vad, asr, caption):
    y = resample_poly(x, 1, 3).astype('float32')
    t = time.perf_counter()
    regs = get_speech_timestamps(torch.from_numpy(y), vad, sampling_rate=16000, threshold=0.5, min_speech_duration_ms=100, min_silence_duration_ms=100, speech_pad_ms=60)
    regions = [{'start_sample': origin + r['start'] * 3, 'end_sample': min(origin + len(x), origin + r['end'] * 3)} for r in regs]
    out = asr.transcribe(y, language='en', fp16=False, temperature=0, condition_on_previous_text=False, initial_prompt=None, word_timestamps=True, verbose=None)
    segs = []
    for s in out['segments']:
        segs.append({k: s[k] for k in ('start', 'end', 'text', 'avg_logprob', 'no_speech_prob', 'compression_ratio', 'words')})
    flags = []
    if not regs:
        flags.append('no_vad_speech')
    if any((s['compression_ratio'] > 2.4 or s['avg_logprob'] < -1 for s in segs)):
        flags.append('asr_low_quality')
    if any((s['no_speech_prob'] > 0.6 for s in segs)):
        flags.append('asr_high_no_speech_probability')
    if len(norms(out['text'])) > 3 and len(set(norms(out['text']))) / len(norms(out['text'])) < 0.35:
        flags.append('asr_repetition')
    return {'rms': float(np.sqrt(np.mean(x * x))), 'peak': float(abs(x).max()), 'speech_regions': regions, 'vad_speech_seconds': sum((r['end'] - r['start'] for r in regs)) / 16000, 'asr_text': out['text'], 'caption_wer': wer(caption, out['text']), 'asr_segments': segs, 'flags': flags, 'wall_seconds': time.perf_counter() - t}

def main():
    t = time.perf_counter()
    torch.set_num_threads(2)
    require_vendor_hash(ROOT / 'deps/silero_vad/data/silero_vad.jit', VAD_SHA256)
    vad = load_silero_vad(onnx=False)
    require_local_runtime()
    asr = whisper.load_model('tiny.en', device='cpu', download_root=str(ROOT / 'models'))
    ann = json.loads((ROOT.parent / 'source/target-annotations.json').read_text())
    context = json.loads((ROOT.parent / 'separation/contextual/segments_report.json').read_text())
    ctx = {s['segment_id']: s for s in context['segments']}
    report = {'schema_version': 1, 'complete': False, 'sample_rate': SR, 'timebase': 'decoded_audio_samples', 'caption_correction_already_applied_seconds': -0.044, 'caption_text_supplied_to_asr': False, 'human_auditory_review': False, 'overlap_resolved': False, 'models': {'vad': 'silero-vad 6.2.3 official bundled TorchScript', 'asr': 'OpenAI Whisper tiny.en 20250625', 'vad_sha256': sha(ROOT / 'deps/silero_vad/data/silero_vad.jit'), 'asr_sha256': sha(ROOT / 'models/tiny.en.pt'), 'license': 'Both MIT', 'asr_official_url': whisper._MODELS['tiny.en'], 'vad_source': 'https://github.com/snakers4/silero-vad'}, 'source_sha256': ann['source_sha256'], 'segments': []}
    for s in ann['segments']:
        a, b = (round(s['start'] * SR), round(s['end'] * SR))
        origin = max(0, a - SR)
        end = b + SR
        row = {'id': s['id'], 'target': s['target'], 'speaker_label': s['speaker'], 'caption': s['transcript'], 'caption_start_sample': a, 'caption_end_sample': b, 'context_start_sample': origin, 'context_end_sample': end, 'signals': {}}
        for name, path, ch in [('stereo', ROOT.parent / 'source/sintel-master-st.flac', None), ('center', ROOT.parent / 'source/sintel-master-51.flac', 2)]:
            x = crop(path, origin, end, ch)
            row['signals'][name] = infer(x, origin, vad, asr, s['transcript'])
        if s['id'] in ctx:
            c = ctx[s['id']]
            x, fs = sf.read(c['output_path'], dtype='float32', always_2d=True)
            require_sample_rate(fs)
            row['signals']['neural_vocals'] = infer(x.mean(axis=1), c['output_source_start_sample'], vad, asr, s['transcript'])
        for v in row['signals'].values():
            v['caption_asr_text'] = ' '.join((w['word'].strip() for seg in v['asr_segments'] for w in seg.get('words', []) if a <= origin + (w['start'] + w['end']) / 2 * SR < b))
            v['caption_wer'] = wer(s['transcript'], v['caption_asr_text'])
            v['caption_overlap_regions'] = intersect(v['speech_regions'], a, b)
            v['caption_overlap_speech_seconds'] = sum((r['end_sample'] - r['start_sample'] for r in v['caption_overlap_regions'])) / SR
        report['segments'].append(row)
        (ROOT / 'audit.json').write_text(json.dumps(report, indent=2))
        print(s['id'], [(k, v['asr_text'], round(v['caption_overlap_speech_seconds'], 3)) for k, v in row['signals'].items()], flush=True)
    report['complete'] = True
    report['wall_seconds'] = time.perf_counter() - t
    (ROOT / 'audit.json').write_text(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
