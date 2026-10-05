#!/usr/bin/env python3
"""Mechanical dataset QA; waveform metrics do not certify speech or identity."""
import argparse, array, json, math, subprocess, sys
from pathlib import Path
from dataset import safe_path, sha256, wav_info

def metrics(path):
    blob=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-f','f32le','-acodec','pcm_f32le','-'])
    x=array.array('f'); x.frombytes(blob)
    if sys.byteorder!='little': x.byteswap()
    if not x: raise ValueError('Empty audio')
    if not all(math.isfinite(v) for v in x): raise ValueError('Nonfinite audio samples')
    rms=math.sqrt(sum(float(v)*v for v in x)/len(x)); peak=max(abs(v) for v in x)
    return {'peak_linear':peak,'rms_dbfs':20*math.log10(max(rms,1e-12)),'samples_at_or_above_full_scale':sum(abs(v)>=1 for v in x),'silent_sample_fraction':sum(abs(v)<1e-7 for v in x)/len(x)}

def verify(root):
    root=safe_path(root); m=json.loads((root/'manifest.json').read_text()); checks=[]
    for c in m['clips']:
        p=safe_path(root/c['raw_path'],root); info=wav_info(p)
        assert sha256(p)==c['raw_sha256'], 'Raw file hash mismatch'
        assert 5<=info['duration_seconds']<=10, 'Raw duration out of range'
        assert info['frames']==c['raw_audio']['frames'], 'Raw frame count changed'
        accounted=c['source_interval_seconds']+c['inserted_gap_seconds']+c['trailing_padding_seconds']
        assert abs(accounted-info['duration_seconds'])<=1/info['sample_rate'], 'Duration accounting mismatch'
        for s in c['source_mappings']:
            assert s['clip_end_sample']-s['clip_start_sample']==s['end_sample']-s['start_sample'], 'Source mapping length mismatch'
        row={'clip_id':c['clip_id'],'raw':{'audio':info,'metrics':metrics(p)},'mechanical_status':'passed'}
        if c['voice_only']:
            v=c['voice_only']; vp=safe_path(root/v['path'],root); vi=wav_info(vp)
            assert sha256(vp)==v['sha256'], 'Processed file hash mismatch'
            assert 5<=vi['duration_seconds']<=10, 'Processed duration out of range'
            assert abs(vi['duration_seconds']-info['duration_seconds'])<=.01, 'Duration drift'
            row['voice_only']={'audio':vi,'metrics':metrics(vp)}
        checks.append(row)
    return {'mechanical_status':'passed','clips_checked':len(checks),'checks':checks,'perceptual_review':'not performed; metrics cannot establish intelligibility, voice identity, natural utterance boundaries, absence of other speakers, or lack of separator artifacts','provisional':m.get('provisional_unverified_overlap_allowed',False)}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('dataset'); parser.add_argument('--output'); a=parser.parse_args()
    result=verify(a.dataset); data=json.dumps(result,indent=2)+'\n'
    if a.output:
        p=safe_path(a.output)
        if p.exists(): raise ValueError('QA output already exists')
        p.write_text(data)
    else: print(data,end='')
