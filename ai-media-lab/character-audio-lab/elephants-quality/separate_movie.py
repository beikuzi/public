import sys,json,hashlib,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent; L=P.parent;sys.path.insert(0,str(L/'separation'))
from separate import separate,MODEL_SHA256
import soundfile as sf
source=L/'second-source-research/ED-CM-St-16bit.flac'; out=P/'movie-separation'; out.mkdir(exist_ok=True)
sha=hashlib.sha256(source.read_bytes()).hexdigest(); info=sf.info(source); sr=info.samplerate
report={'schema_version':1,'complete':False,'source_sha256':sha,'method':'Actual movie stereo HybridDemucs vocals, broad contexts retained until matching and boundary refinement. Not speaker isolation.','segments':[]}
if (out/'segments_report.json').exists():
 report=json.loads((out/'segments_report.json').read_text())
 if report['source_sha256']!=sha:raise ValueError('Source changed')
 report['complete']=False
contexts=[('ed_proog_01',13,27),('ed_proog_02',55,65),('ed_proog_03',433,442),('ed_proog_04',181,191)]
completed={s['segment_id'] for s in report['segments']}
for name,start,end in contexts:
 if name in completed:continue
 a=round(start*sr);b=round(end*sr); raw=out/(name+'_context.wav'); dest=out/(name+'_context_vocals.wav')
 if raw.exists() or dest.exists(): raise FileExistsError(name)
 with sf.SoundFile(source) as f: f.seek(a); x=f.read(b-a,dtype='float32',always_2d=True)
 if len(x)!=b-a:raise ValueError('length')
 sf.write(raw,x,sr,subtype='FLOAT'); metrics=separate(raw,dest)
 report['segments'].append({'segment_id':name,'output_path':str(dest.resolve()),'input_path':str(raw.resolve()),'output_source_start_sample':a,'output_source_start':a/sr,'output_source_end_sample':b,'sample_rate':sr,'samples':b-a,'source_sha256':sha,'model':'HDEMUCS_HIGH_MUSDB_PLUS','model_sha256':MODEL_SHA256,'model_version':'torchaudio2.8.0+cpu','metrics':metrics,'limitations':['All vocals retained, not target-speaker isolation','No human auditory review','Exact source-reference alignment pending; no SI-SDR asserted']})
 (out/'segments_report.json').write_text(json.dumps(report,indent=2));print(name,metrics,flush=True)
report['complete']=True;(out/'segments_report.json').write_text(json.dumps(report,indent=2))
