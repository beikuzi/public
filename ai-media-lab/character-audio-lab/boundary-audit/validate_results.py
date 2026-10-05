import json, sys
from pathlib import Path
from audit import ROOT, SR, torch, np, load_silero_vad, get_speech_timestamps, require_vendor_hash, VAD_SHA256, require_local_runtime
r = json.loads((ROOT / 'audit.json').read_text())
p = json.loads((ROOT / 'boundary-proposals.json').read_text())
if not (r['complete'] and len(r['segments']) == 26):
    raise ValueError("Audit validation failed: r['complete'] and len(r['segments']) == 26")
if not sum((len(x['signals']) for x in r['segments'])) == 66:
    raise ValueError("Audit validation failed: sum((len(x['signals']) for x in r['segments'])) == 66")
for s in r['segments']:
    for v in s['signals'].values():
        for z in v['speech_regions']:
            if not s['context_start_sample'] <= z['start_sample'] < z['end_sample'] <= s['context_end_sample']:
                raise ValueError("Audit validation failed: s['context_start_sample'] <= z['start_sample'] < z['end_sample'] <= s['context_end_sample']")
            if not (isinstance(z['start_sample'], int) and isinstance(z['end_sample'], int)):
                raise ValueError("Audit validation failed: isinstance(z['start_sample'], int) and isinstance(z['end_sample'], int)")
for s in p['proposals']:
    for z in s['proposed_regions']:
        if not s['proposed_start_sample'] <= z['start_sample'] < z['end_sample'] <= s['proposed_end_sample']:
            raise ValueError("Audit validation failed: s['proposed_start_sample'] <= z['start_sample'] < z['end_sample'] <= s['proposed_end_sample']")
require_vendor_hash(ROOT / 'deps/silero_vad/data/silero_vad.jit', VAD_SHA256)
require_local_runtime()
vad = load_silero_vad(onnx=False)
torch.set_num_threads(1)
controls = {}
rng = np.random.default_rng(123)
for name, x in [('silence', np.zeros(48000, dtype='float32')), ('440hz_tone', (0.1 * np.sin(2 * np.pi * 440 * np.arange(48000) / 16000)).astype('float32')), ('white_noise', rng.normal(0, 0.03, 48000).astype('float32'))]:
    controls[name] = get_speech_timestamps(torch.from_numpy(x), vad, sampling_rate=16000, threshold=0.5, min_speech_duration_ms=100, min_silence_duration_ms=100, speech_pad_ms=60)
if not controls['silence'] == []:
    raise ValueError("Audit validation failed: controls['silence'] == []")
if not 'onnxruntime' not in sys.modules:
    raise ValueError("Audit validation failed: 'onnxruntime' not in sys.modules")
out = {'complete': True, 'all26_caption_and66_signal_counts_valid': True, 'all_boundaries_in_context_and_integer48k_samples': True, 'onnxruntime_imported': False, 'vad_synthetic_negative_controls': controls, 'synthetic_controls_are_not_real_music_specificity_validation': True, 'proposals': len(p['proposals']), 'candidate_proposals': sum((x['proposal_status'] == 'machine_supported_candidate' for x in p['proposals']))}
(ROOT / 'validation.json').write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
