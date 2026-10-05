"""Read-only local audit of author-labelled Elephants Dream dialogue WAVs."""
import sys, json, hashlib, time, math
from pathlib import Path
P=Path(__file__).resolve().parent; LAB=P.parent; B=LAB/'boundary-audit'
sys.path.insert(0,str(B/'deps'))
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import torch, whisper
from silero_vad import load_silero_vad, get_speech_timestamps

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def db(x): return 20*math.log10(max(float(np.sqrt(np.mean(np.square(x.astype(float))))),1e-12)) if len(x) else None

def main():
 t=time.time(); torch.set_num_threads(2)
 vp=B/'deps/silero_vad/data/silero_vad.jit'; wp=B/'models/tiny.en.pt'
 if sha(vp)!='e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720': raise ValueError('VAD hash')
 if sha(wp)!=whisper._MODELS['tiny.en'].split('/')[-2]: raise ValueError('Whisper hash')
 vad=load_silero_vad(onnx=False); asr=whisper.load_model(str(wp),device='cpu')
 if 'onnxruntime' in sys.modules: raise ValueError('Forbidden runtime')
 report={'schema_version':1,'complete':False,'human_listening':False,'speaker_overlap_verified':False,'clean_verified':False,'method':'Official production-DVD role-labelled voice candidates; machine measurements do not prove isolation or purity. VAD is activity estimate, not usable duration. Whisper tiny.en unprompted local ASR; no reference text. No uploads.','models':{'vad_sha256':sha(vp),'asr_sha256':sha(wp)},'files':[]}
 priority=['1_PROOG.WAV','2_EMO.WAV','2_PROOG.WAV','3_1_2_PROOG.WAV']
 files=sorted((LAB/'second-source-research/soundbytes').glob('*.WAV'),key=lambda f:(priority.index(f.name) if f.name in priority else 99,f.name))
 for f in files:
  info=sf.info(f); x,sr=sf.read(f,dtype='float32',always_2d=True); mono=x.mean(1); dur=len(x)/sr
  y=resample_poly(mono,16000//math.gcd(sr,16000),sr//math.gcd(sr,16000)).astype('float32')
  regs=get_speech_timestamps(torch.from_numpy(y),vad,sampling_rate=16000,threshold=.5,min_speech_duration_ms=100,min_silence_duration_ms=100,speech_pad_ms=60)
  mask=np.zeros(len(x),bool)
  regions=[]
  for r in regs:
   a=round(r['start']*sr/16000); b=min(len(x),round(r['end']*sr/16000)); mask[a:b]=True; regions.append({'start_seconds':a/sr,'end_seconds':b/sr})
  out=asr.transcribe(y,language='en',fp16=False,temperature=0,condition_on_previous_text=False,initial_prompt=None,word_timestamps=True,verbose=None)
  frame=int(sr*.02); env=np.sqrt(np.mean(mono[:len(mono)//frame*frame].reshape(-1,frame).astype(float)**2,axis=1))
  candidates=[]
  # Fixed 10s candidate crops, stepping by 1s; candidates overlap and may not be summed.
  for length in [5,8,10]:
   if dur<length: continue
   starts=list(np.arange(0,dur-length+1e-6,1.0))+[dur-length]
   best=max(starts,key=lambda a:int(mask[round(a*sr):round((a+length)*sr)].sum()))
   a=round(best*sr); b=round((best+length)*sr)
   candidates.append({'duration_seconds':length,'start_seconds':a/sr,'end_seconds':b/sr,'vad_seconds':float(mask[a:b].sum()/sr),'vad_fraction':float(mask[a:b].mean()),'boundary_policy':'Candidate only; check utterance boundary and movie alignment before export.'})
  nz=np.flatnonzero(mono!=0)
  row={'file':f.name,'sha256':sha(f),'sample_rate':sr,'channels':info.channels,'subtype':info.subtype,'frames':len(x),'duration_seconds':dur,'rms_dbfs':db(mono),'peak_abs':float(abs(x).max()),'full_scale_sample_count':int((abs(x)>=32767/32768).sum()),'zero_fraction':float((x==0).mean()),'leading_digital_zero_seconds':int(nz[0])/sr if len(nz) else dur,'trailing_digital_zero_seconds':(len(x)-1-int(nz[-1]))/sr if len(nz) else dur,'frame_rms_dbfs_percentiles':{str(p):float(20*np.log10(max(float(np.percentile(env,p)),1e-12))) for p in [10,25,50,75,90]},'frames_below_minus60_dbfs_fraction':float((env<.001).mean()),'speech_regions':regions,'vad_speech_seconds':float(mask.sum()/sr),'vad_fraction':float(mask.mean()),'vad_region_rms_dbfs':db(mono[mask]),'nonvad_region_rms_dbfs':db(mono[~mask]),'asr_text':out['text'],'asr_segments':[{k:s[k] for k in ('start','end','text','avg_logprob','no_speech_prob','compression_ratio','words')} for s in out['segments']],'candidate_windows':candidates,'quality_class':'authored role-labelled production WAV; clean purity unverified','nonvad_energy_caution':'Non-VAD samples can contain quiet speech, breath, room noise or effects. Not noise ground truth and no SNR calculated.'}
  report['files'].append(row); (P/'measurements.json').write_text(json.dumps(report,indent=2)); print(f.name,round(dur,3),round(row['vad_speech_seconds'],3),repr(out['text']),flush=True)
 report['complete']=True; report['wall_seconds']=time.time()-t; (P/'measurements.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__': main()
