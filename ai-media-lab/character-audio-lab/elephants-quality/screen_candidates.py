"""Declared conservative machine screening; never establishes clean purity."""
from pathlib import Path
import json, numpy as np, soundfile as sf
P=Path(__file__).resolve().parent; S=P.parent/'second-source-research/soundbytes'
r=json.loads((P/'measurements.json').read_text()); rows=[]
# Thresholds declared before selecting individual windows.
gates={'crop_length_seconds':[5,10],'full_scale_samples':0,'minimum_vad_fraction':.65,'minimum_asr_words':6,'minimum_asr_mean_logprob':-1,'maximum_asr_compression_ratio':2.4,'maximum_asr_no_speech_probability':.6,'file_nonvad_rms_max_dbfs':-50,'known_alternative_exclusions':['7_10_EMO.WAV','7_10_PROOG.WAV','8_PROOG_WHOAS.WAV'],'unknowns':['Music absence not established','Other-speaker overlap not verified','No listening performed','ASR words are estimates']}
for f in r['files']:
 x,sr=sf.read(S/f['file'],dtype='float32');
 for w in f['candidate_windows']:
  a,b=w['start_seconds'],w['end_seconds']; crop=x[round(a*sr):round(b*sr)]
  segs=[s for s in f['asr_segments'] if s['end']>a and s['start']<b]
  words=[q['word'].strip() for s in segs for q in s['words'] if a<=(q['start']+q['end'])/2<b]
  checks={'no_full_scale_samples':bool(np.all(abs(crop)<32767/32768)),'sufficient_vad':w['vad_fraction']>=.65,'asr_support':len(words)>=6 and bool(segs) and all(s['avg_logprob']>=-1 and s['compression_ratio']<=2.4 and s['no_speech_prob']<=.6 for s in segs),'low_file_nonvad_energy':f['nonvad_region_rms_dbfs'] is not None and f['nonvad_region_rms_dbfs']<=-50,'not_known_alternate':f['file'] not in gates['known_alternative_exclusions']}
  rows.append({'file':f['file'],**w,'asr_words':' '.join(words),'gates':checks,'machine_screen_pass':all(checks.values()),'quality_class':'clean_candidate_machine_screen' if all(checks.values()) else 'review_candidate','clean_verified':False,'overlap':'unknown','music_absence':'unknown','caveat':'Low non-VAD energy is only a file-level screen, not an actual background/noise estimate. Windows overlap and cannot be summed.'})
(P/'candidate-screen.json').write_text(json.dumps({'criteria':gates,'candidates':rows},indent=2))
for a in rows:
 if a['machine_screen_pass']:print(a['file'],a['start_seconds'],a['end_seconds'],a['asr_words'])
