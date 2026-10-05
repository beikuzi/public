import os,sys,json,hashlib,re,subprocess,time
from pathlib import Path
from validation import validate_runtime_inputs, validate_boundary_inputs, validate_context
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'deps'))
import numpy as np
import torch
from speechbrain.lobes.models.ECAPA_TDNN import ECAPA_TDNN
from speechbrain.lobes.features import Fbank
from speechbrain.processing.features import InputNormalization
torch.set_num_threads(2)
ann=json.load(open(ROOT.parent/'source/target-annotations.json'))
validate_runtime_inputs(ROOT, ann)
protocol=json.load(open(ROOT/'protocol.json'))
feat=Fbank(n_mels=80).eval()
norm=InputNormalization(norm_type='sentence',std_norm=False).eval()
model=ECAPA_TDNN(input_size=80,channels=[1024,1024,1024,1024,3072],kernel_sizes=[5,3,3,3,1],dilations=[1,2,3,4,1],attention_channels=128,lin_neurons=192).eval()
state=torch.load(ROOT/'embedding_model.ckpt',map_location='cpu',weights_only=True)
model.load_state_dict(state,strict=True)
emb={}; measures={}; crops=ROOT/'crops';crops.mkdir(exist_ok=True)
for s in ann['segments']:
 for mode,file,filter_ in [('center','sintel-master-51.flac','pan=mono|c0=c2'),('stereo','sintel-master-st.flac','pan=mono|c0=0.5*c0+0.5*c1')]:
  cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(s['start']),'-i',str(ROOT.parent/'source'/file),'-t',str(s['end']-s['start']),'-af',filter_,'-ar','16000','-f','f32le','pipe:1']
  x=np.frombuffer(subprocess.check_output(cmd),np.float32).copy()
  wav=torch.from_numpy(x)[None,:]
  with torch.inference_mode():
   z=model(norm(feat(wav),torch.ones(1))).flatten().numpy();z=z/np.linalg.norm(z)
  emb[(s['id'],mode)]=z
  frames=x[:len(x)//320*320].reshape(-1,320)
  rms=np.sqrt(np.mean(frames**2,axis=1));db=20*np.log10(np.maximum(rms,1e-10))
  measures[(s['id'],mode)]={'rms_dbfs':float(20*np.log10(max(np.sqrt(np.mean(x*x)),1e-10))), 'energy_above_minus40dbfs_seconds':round(float(np.sum(db>-40)*.02),3),'peak_dbfs':float(20*np.log10(max(np.max(np.abs(x)),1e-10)))}
 print('embedded',s['id'],flush=True)
res=[]
for s in ann['segments']:
 item={k:s[k] for k in ['id','start','end','speaker','target','transcript']}; modes={}
 for mode in ['center','stereo']:
  scores={}
  for speaker,ids in protocol['anchor_candidates'].items():
   valid=[i for i in ids if i!=s['id']]
   center=np.mean([emb[(i,mode)] for i in valid],axis=0);center/=np.linalg.norm(center)
   scores[speaker]=float(emb[(s['id'],mode)]@center)
  winner=max(scores,key=scores.get); ordered=sorted(scores.values(),reverse=True)
  modes[mode]={'cosine':scores,'winner':winner,'margin':ordered[0]-ordered[1],**measures[(s['id'],mode)]}
 words=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",s['transcript']);reasons=[]
 if s['end']-s['start']<2:reasons.append('caption_duration_below_2_seconds')
 if len(words)<3:reasons.append('fewer_than_3_lexical_words')
 for mode,q in modes.items():
  if max(q['cosine'].values())<.35:reasons.append(mode+'_cosine_below_exploratory_gate')
  if q['margin']<.10:reasons.append(mode+'_margin_below_exploratory_gate')
  if q['winner']!=s['speaker']:reasons.append(mode+'_disagrees_with_scene_label')
 if modes['center']['winner']!=modes['stereo']['winner']:reasons.append('channel_winners_disagree')
 item.update({'duration_seconds':round(s['end']-s['start'],3),'lexical_word_count':len(words),'anchor':any(s['id'] in v for v in protocol['anchor_candidates'].values()),'acoustic_results':modes,'triage':'quarantine' if reasons else 'acoustically_consistent_provisional','reasons':reasons,'speaker_overlap':None,'training_ready':False,'human_auditory_review':False})
 res.append(item)
result={'method':'SpeechBrain ECAPA-TDNN, frozen public pretrained embeddings, 16kHz center and mono-downmixed stereo, cosine to scene anchors; enrollment samples leave-one-out','protocol':protocol,'source_annotation_sha256':hashlib.sha256((ROOT.parent/'source/target-annotations.json').read_bytes()).hexdigest(),'model_url':'https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb','model_sha256':hashlib.sha256((ROOT/'embedding_model.ckpt').read_bytes()).hexdigest(),'software':{'speechbrain':'1.1.1','torch':torch.__version__},'coverage':{'annotated_intervals':len(res),'full_film_diarization':False},'limitations':['Not human auditory verification.','Scores are similarities, not calibrated probabilities.','No overlap detector, ASR, or forced alignment was run.','Model domain differs from movie dialogue and effects.','Anchor labels rely on scene evidence and may be wrong.','Long subtitle intervals may contain very brief speech.','All outputs remain training_ready=false.'],'segments':res}
json.dump(result,open(ROOT/'verification.json','w'),indent=2)
np.savez(ROOT/'embeddings-local-only.npz',**{f'{k[0]}_{k[1]}':v for k,v in emb.items()})
print(json.dumps([{k:x[k] for k in ['id','speaker','triage','reasons']} for x in res],indent=2))
