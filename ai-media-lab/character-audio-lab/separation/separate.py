#!/usr/bin/env python3
"""Local, aligned Hybrid Demucs or center-channel baseline. No speaker isolation."""
import argparse, hashlib, json, math, resource, subprocess, time
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
ROOT=Path(__file__).resolve().parent
MODEL=ROOT/'models/hdemucs_high_trained.pt'
MODEL_SHA256='a004b2790d73ffeaa535db458a1a79b539dfdbafbccc31f275d07e632ebd7816'
_MODEL_CACHE=None
def read_audio(path):
    sr,x=wavfile.read(path)
    if np.issubdtype(x.dtype,np.integer): x=x.astype(np.float32)/max(abs(np.iinfo(x.dtype).min),np.iinfo(x.dtype).max)
    else: x=x.astype(np.float32)
    if x.ndim==1:x=x[:,None]
    return sr,x

def separate(input_path, output_path, method='hdemucs',threads=4):
    start=time.perf_counter(); sr,x=read_audio(input_path); n=len(x)
    if method=='center':
        if x.shape[1]!=6:raise ValueError('Center baseline requires verified WAV 5.1 order FL FR FC LFE BL BR; no stereo center is assumed')
        y=x[:,2:3]; model_seconds=0; name='5.1 center channel extraction; not neural'
    else:
        import torch,torchaudio
        torch.set_num_threads(threads)
        # Checkpoint comes only from the official PyTorch model CDN. Never unsafe pickle.
        global _MODEL_CACHE
        if _MODEL_CACHE is None:
            if hashlib.sha256(MODEL.read_bytes()).hexdigest()!=MODEL_SHA256:raise ValueError('Official model checksum mismatch')
            _MODEL_CACHE=torchaudio.models.hdemucs_high(sources=['drums','bass','other','vocals'])
            _MODEL_CACHE.load_state_dict(torch.load(MODEL,map_location='cpu',weights_only=True));_MODEL_CACHE.eval()
        model=_MODEL_CACHE
        if x.shape[1]==1: stereo=np.repeat(x,2,axis=1)
        elif x.shape[1]==2:stereo=x
        else:raise ValueError('Neural input must be mono or stereo; explicitly downmix multichannel upstream')
        divisor=math.gcd(sr,44100); a=resample_poly(stereo,44100//divisor,sr//divisor,axis=0)
        audio=torch.from_numpy(a.T.copy()); ref=audio.mean(0); mean=ref.mean(); std=ref.std().clamp_min(1e-8); audio=(audio-mean)/std
        total=audio.shape[-1]; seg=5*44100; overlap=44100//2; step=seg-overlap
        out=torch.zeros((2,total)); weights=torch.zeros(total); inf=time.perf_counter()
        with torch.inference_mode():
            for offset in range(0,total,step):
                end=min(offset+seg,total); piece=audio[:,offset:end]
                pred=model(piece[None])[0,3]
                window=torch.ones(end-offset)
                k=min(overlap,len(window))
                if offset:window[:k]=torch.linspace(0,1,k)
                if end<total:window[-k:]=torch.linspace(1,0,k)
                out[:,offset:end]+=pred*window;weights[offset:end]+=window
                if end==total:break
        out=out/weights.clamp_min(1e-8)*std+mean
        model_seconds=time.perf_counter()-inf
        y=resample_poly(out.numpy().T,sr//divisor,44100//divisor,axis=0)
        if len(y)<n:y=np.pad(y,((0,n-len(y)),(0,0)))
        y=y[:n];name='Torchaudio 2.8.0 Hybrid Demucs HDEMUCS_HIGH_MUSDB_PLUS'
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    # Float WAV preserves amplitudes without hidden peak normalization or PCM clipping.
    wavfile.write(output_path,sr,y.astype(np.float32))
    result={'input':str(input_path),'output':str(output_path),'method':name,'sample_rate':sr,'input_samples':n,'output_samples':len(y),'duration_seconds':n/sr,'input_channels':x.shape[1],'output_channels':y.shape[1], 'wall_seconds':time.perf_counter()-start,'inference_seconds':model_seconds,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'threads':threads,'api_cost_usd':0,'infrastructure_cost':'not priced','target_character_isolated':False,'requires_listening_review':True,'output_peak_abs':float(abs(y).max()),'input_rms':float(np.sqrt(np.mean(x*x))),'output_rms':float(np.sqrt(np.mean(y*y)))}
    result['real_time_factor']=result['wall_seconds']/result['duration_seconds']
    Path(str(output_path)+'.json').write_text(json.dumps(result,indent=2))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--method',choices=['hdemucs','center'],default='hdemucs');p.add_argument('--threads',type=int,default=4);args=p.parse_args()
    print(json.dumps(separate(args.input,args.output,args.method,args.threads),indent=2))
