"""Numerical review-candidate gates. No perceptual or speaker-purity guarantee."""
import math

def clipped_union(regions,start,end):
    if not math.isfinite(start) or not math.isfinite(end) or end<=start:raise ValueError('Invalid crop')
    intervals=sorted((max(start,r['start_seconds']),min(end,r['end_seconds'])) for r in regions if min(end,r['end_seconds'])>max(start,r['start_seconds']))
    result=[]
    for a,b in intervals:
        if result and a<=result[-1]['end_seconds']:result[-1]['end_seconds']=max(b,result[-1]['end_seconds'])
        else:result.append({'start_seconds':a,'end_seconds':b})
    return result

def screen(duration,vad_seconds,full_scale_count,word_count,asr_supported,file_nonvad_dbfs,alternate=False):
    if not all(math.isfinite(z) for z in [duration,vad_seconds]) or duration<=0 or not 0<=vad_seconds<=duration+1e-8:raise ValueError('Invalid duration')
    checks={'duration_5_to_10_seconds':5<=duration<=10,'no_full_scale_samples':full_scale_count==0,'sufficient_vad':vad_seconds/duration>=.65,'asr_support':word_count>=6 and asr_supported,'low_file_nonvad_energy':file_nonvad_dbfs is not None and math.isfinite(file_nonvad_dbfs) and file_nonvad_dbfs<=-50,'not_known_alternate':not alternate}
    return {'gates':checks,'machine_screen_pass':all(checks.values()),'failed_gates':[k for k,v in checks.items() if not v]}

if __name__=='__main__':
    import json
    from pathlib import Path
    import numpy as np,soundfile as sf
    p=Path(__file__).resolve().parent; r=json.loads((p/'measurements.json').read_text());lookup={x['file']:x for x in r['files']};rows=[]
    for name,a,b in [('1_PROOG.WAV',0,8.075),('2_PROOG.WAV',12.4,19.0),('7_PROOG.WAV',5.2,12.1),('3_2_PROOG.WAV',12.05,18.90)]:
        f=lookup[name];x,sr=sf.read(p.parent/'second-source-research/soundbytes'/name,dtype='float32');first=round(a*sr);last=round(b*sr);crop=x[first:last];regions=clipped_union(f['speech_regions'],a,b);v=sum(q['end_seconds']-q['start_seconds'] for q in regions)
        segs=[s for s in f['asr_segments'] if s['end']>a and s['start']<b];words=[w for s in segs for w in s['words'] if a<=(w['start']+w['end'])/2<b];n=int((abs(crop)>=32767/32768).sum());supported=bool(segs) and all(s['avg_logprob']>=-1 and s['compression_ratio']<=2.4 and s['no_speech_prob']<=.6 for s in segs)
        rows.append({'file':name,'start_seconds':a,'end_seconds':b,'start_sample':first,'end_sample':last,'sample_rate':sr,'frames':last-first,'duration_seconds':(last-first)/sr,'full_scale_sample_count':n,'peak_abs':float(abs(crop).max()),'vad_speech_seconds':v,'vad_fraction':v/(b-a),'speech_regions':regions,'file_nonvad_rms_dbfs':f['nonvad_region_rms_dbfs'],'asr_word_count':len(words),'asr_supported':supported,**screen(b-a,v,n,len(words),supported,f['nonvad_region_rms_dbfs']),'clean_verified':False,'music_absence':'unknown','other_speaker_overlap':'unknown','quality_label':'production_source_machine_screen_candidate','caveat':'No listening. Non-VAD file RMS is a screening proxy, not background measurement. ASR words are timestamp estimates; same dialogue in film is validated separately. Known role-overlap matches excluded by builder, but overlap absence is unverified.'})
    (p/'selected-crop-qc.json').write_text(json.dumps({'complete':True,'crops':rows},indent=2))
    for z in rows:print(z['file'],z['machine_screen_pass'],z['failed_gates'],z['vad_speech_seconds'],z['vad_fraction'],z['full_scale_sample_count'],z['asr_word_count'])
