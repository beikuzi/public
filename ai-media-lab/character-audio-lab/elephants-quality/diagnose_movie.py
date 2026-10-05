import sys,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent; B=P.parent/'boundary-audit';sys.path.insert(0,str(B));sys.path.insert(0,str(B/'deps'))
import numpy as np, soundfile as sf, torch, whisper
from audit import infer,require_vendor_hash,require_local_runtime,VAD_SHA256
from silero_vad import load_silero_vad
r=json.loads((P/'movie-separation/segments_report.json').read_text()); torch.set_num_threads(2);require_vendor_hash(B/'deps/silero_vad/data/silero_vad.jit',VAD_SHA256);require_vendor_hash(B/'models/tiny.en.pt',whisper._MODELS['tiny.en'].split('/')[-2]);vad=load_silero_vad(onnx=False);asr=whisper.load_model(str(B/'models/tiny.en.pt'),device='cpu'); require_local_runtime()
o={'complete':False,'human_listening':False,'reference_sdr_status':'Not computed: raw-to-film edit/phase/gain consistency not validated.','segments':[]}
if (P/'movie-diagnostics.json').exists():
 o=json.loads((P/'movie-diagnostics.json').read_text());o['complete']=False
completed={s['id'] for s in o['segments']}
for s in r['segments']:
 if s['segment_id'] in completed:continue
 a={'id':s['segment_id'],'movie_start_sample':s['output_source_start_sample'],'signals':{}}
 for name,key in [('movie','input_path'),('neural_vocals','output_path')]:
  x,sr=sf.read(s[key],dtype='float32',always_2d=True)
  if sr!=48000: raise ValueError('rate')
  z=infer(x.mean(1),s['output_source_start_sample'],vad,asr,'');z.pop('caption_wer');z['frames']=len(x);z['seconds']=len(x)/sr;z['channels']=x.shape[1];z['full_scale_samples']=int((abs(x)>=1).sum());a['signals'][name]=z
 o['segments'].append(a);(P/'movie-diagnostics.json').write_text(json.dumps(o,indent=2));print(a['id'],[(k,v['asr_text'])for k,v in a['signals'].items()],flush=True)
o['complete']=True;(P/'movie-diagnostics.json').write_text(json.dumps(o,indent=2))
