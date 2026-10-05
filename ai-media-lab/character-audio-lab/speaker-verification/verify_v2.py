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
protocol=json.load(open(ROOT/'protocol-v2.json'))
feat=Fbank(n_mels=80).eval()
norm=InputNormalization(norm_type='sentence',std_norm=False).eval()
model=ECAPA_TDNN(input_size=80,channels=[1024,1024,1024,1024,3072],kernel_sizes=[5,3,3,3,1],dilations=[1,2,3,4,1],attention_channels=128,lin_neurons=192).eval()
state=torch.load(ROOT/'embedding_model.ckpt',map_location='cpu',weights_only=True)
model.load_state_dict(state,strict=True)
audit=json.load(open(ROOT.parent/'boundary-audit/audit.json'));proposals=json.load(open(ROOT.parent/'boundary-audit/boundary-proposals.json'))
validate_boundary_inputs(audit, proposals)
A={s['id']:s for s in audit['segments']};P={s['id']:s for s in proposals['proposals']}
context=json.load(open(ROOT.parent/'separation/contextual/segments_report.json'))
validate_context(ROOT, context)
C={s['segment_id']:s for s in context['segments']}
emb={}; used={};sr=48000
for s in ann['segments']:
 sid=s['id'];p=P[sid];a=A[sid]
 for mode,file,filter_ in [('center','sintel-master-51.flac','pan=mono|c0=c2'),('stereo','sintel-master-st.flac','pan=mono|c0=0.5*c0+0.5*c1'),('neural_vocals',None,'pan=mono|c0=0.5*c0+0.5*c1')]:
  if mode=='neural_vocals' and sid not in C:continue
  regions=p['proposed_regions'] if p['proposal_status']=='machine_supported_candidate' else [{'start_sample':max(r['start_sample'],a['caption_start_sample']),'end_sample':min(r['end_sample'],a['caption_end_sample'])} for r in a['signals'][mode]['speech_regions'] if min(r['end_sample'],a['caption_end_sample'])>max(r['start_sample'],a['caption_start_sample'])]
  used[(sid,mode)]={'regions':regions,'model_detected_speech_seconds':sum(r['end_sample']-r['start_sample'] for r in regions)/sr,'boundary_supported':p['proposal_status']=='machine_supported_candidate'}
  if not regions:continue
  xs=[]
  for r in regions:
   source=ROOT.parent/'source'/file if file else Path(C[sid]['output_path']);origin=0 if file else C[sid]['output_source_start_sample']
   cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str((r['start_sample']-origin)/sr),'-i',str(source),'-t',str((r['end_sample']-r['start_sample'])/sr),'-af',filter_,'-ar','16000','-f','f32le','pipe:1']
   xs.append(np.frombuffer(subprocess.check_output(cmd),np.float32).copy())
  x=np.concatenate(xs);wav=torch.from_numpy(x)[None,:]
  with torch.inference_mode():
   z=model(norm(feat(wav),torch.ones(1))).flatten().numpy();z=z/np.linalg.norm(z)
  emb[(sid,mode)]=z
 print('embedded',sid,flush=True)
experiments={}
for name,anchors in protocol['anchor_sets'].items():
 rows=[]
 for s in ann['segments']:
  sid=s['id'];p=P[sid];scores={};reason=[]
  for mode in ['center','stereo','neural_vocals']:
   if (sid,mode) not in emb:
    if mode!='neural_vocals':reason.append(mode+'_no_vad_audio')
    continue
   ref_mode='center' if mode=='neural_vocals' else mode
   cos={}
   for role,ids in anchors.items():
    valid=[i for i in ids if i!=sid and (i,ref_mode) in emb]
    if not valid:continue
    centroid=np.mean([emb[(i,ref_mode)] for i in valid],axis=0);centroid/=np.linalg.norm(centroid)
    cos[role]=float(centroid@emb[(sid,mode)])
   if len(cos)!=2:
    if mode!='neural_vocals':reason.append(mode+'_insufficient_anchor_audio')
    continue
   winner=max(cos,key=cos.get);v=sorted(cos.values(),reverse=True);margin=v[0]-v[1]
   scores[mode]={'cosine':cos,'winner':winner,'margin':margin,**used[(sid,mode)]}
   if mode!='neural_vocals':
    if v[0]<.35:reason.append(mode+'_cosine_below_gate')
    if margin<.1:reason.append(mode+'_margin_below_gate')
    if winner!=s['speaker']:reason.append(mode+'_scene_label_disagreement')
  acoustic_consistent=not reason
  if p['proposal_status']!='machine_supported_candidate':reason.append('no_supported_boundary_proposal')
  duration=used.get((sid,'center'),{}).get('model_detected_speech_seconds',0)
  if duration<2:reason.append('model_detected_speech_below_2s')
  enrollment=any(sid in v for v in anchors.values())
  rows.append({'id':sid,'speaker':s['speaker'],'enrollment':enrollment,'evaluation_partition':'enrollment_leave_one_out' if enrollment else 'non_enrolled_candidate','original_caption_seconds':round(s['end']-s['start'],3),'model_detected_speech_seconds':duration,'boundary_status':p['proposal_status'],'proposed_regions':p['proposed_regions'],'acoustic_results':scores,'acoustic_similarity_gates_pass':acoustic_consistent,'triage':'machine_consistent_provisional' if not reason else 'quarantine','reasons':reason,'overlap':None,'human_auditory_review':False,'training_ready':False})
 experiments[name]={'anchors':anchors,'segments':rows,'summary':{}}
 for role in anchors:
  rr=[r for r in rows if r['speaker']==role];passing=[r for r in rr if r['triage']!='quarantine'];held=[r for r in passing if not r['enrollment']]
  experiments[name]['summary'][role]={'passing_ids':[r['id'] for r in passing],'passing_model_speech_seconds':round(sum(r['model_detected_speech_seconds'] for r in passing),3),'non_enrolled_passing_ids':[r['id'] for r in held],'non_enrolled_passing_model_speech_seconds':round(sum(r['model_detected_speech_seconds'] for r in held),3),'quarantined_ids':[r['id'] for r in rr if r['triage']=='quarantine'],'training_ready_seconds':0}
result={'protocol':protocol,'source_sha256':ann['source_sha256'],'boundary_proposals_sha256':hashlib.sha256((ROOT.parent/'boundary-audit/boundary-proposals.json').read_bytes()).hexdigest(),'experiments':experiments,'limitations':['All boundary and speaker evidence is machine-generated, not human listening.','No overlap assessment or calibrated identity/error-rate conclusion.','VAD-positive duration is model-detected speech, not ground-truth voiced duration.','Alternative anchors chosen after initial failed experiment; v2 is exploratory, not a clean independent benchmark.','Neural view scores use center prototypes and are diagnostic only.','Concatenating VAD regions removes pauses and may affect embeddings.','Missing VAD proposals remain quarantined even if scores appear consistent.']}
json.dump(result,open(ROOT/'verification-v2.json','w'),indent=2)
np.savez(ROOT/'embeddings-v2-local-only.npz',**{f'{k[0]}_{k[1]}':v for k,v in emb.items()})
print(json.dumps({k:v['summary'] for k,v in experiments.items()},indent=2))
