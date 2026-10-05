#!/usr/bin/env python3
"""Mechanical output QA, independent of model and private source media availability."""
import argparse,array,json,math,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from dataset import safe_path,sha256,wav_info

def require(ok,msg):
    if not ok:raise ValueError(msg)

def verify(folder):
    folder=safe_path(folder);m=json.loads((folder/'manifest.json').read_text());checks=[]
    for clip in m['clips']:
        path=safe_path(folder/clip['path'],folder);require(sha256(path)==clip['sha256'],'Output hash mismatch')
        info=wav_info(path);require(info['frames']==clip['audio']['frames'],'Frame count changed');require(info['sample_rate']==48000 and info['channels']==2,'Output format changed');require(5<=info['duration_seconds']<=10,'Clip length out of range')
        require(abs(info['duration_seconds']-clip['source_interval_seconds']-clip['gap_seconds']-clip['padding_seconds'])<1/48000,'Duration accounting mismatch')
        for s in clip['mappings']:
            require(s['source_end_frame']-s['source_start_frame']==s['clip_end_frame']-s['clip_start_frame'],'Source/output mapping mismatch')
            require(0<=s['clip_start_frame']<s['clip_end_frame']<=info['frames'],'Invalid output mapping bounds')
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-']);samples=array.array('f');samples.frombytes(raw)
        if sys.byteorder!='little':samples.byteswap()
        require(all(math.isfinite(v) for v in samples),'Nonfinite output')
        require(len(samples)==2*info['frames'],'Decoded output length differs')
        checks.append({'path':clip['path'],'frames':info['frames'],'duration_seconds':info['duration_seconds'],'peak':max(abs(v) for v in samples),'full_scale_samples':sum(abs(v)>=1 for v in samples),'hash_verified':True,'mapping_verified':True})
    return {'status':'passed','files_checked':len(checks),'checks':checks,'human_listening':False,'clean_purity_verified':False,'target_only_verified':False,'training_ready':False,'limitation':'Mechanical and numerical quality checks cannot establish intelligibility, purity, natural boundaries, voice identity or lack of overlap.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder');a=p.parse_args();print(json.dumps(verify(a.folder),indent=2))
