"""Independent Vosk route, same 16k PCM audio, no network access at inference."""
import argparse,pathlib,json,time,wave,resource,importlib.metadata
from vosk import Model,KaldiRecognizer,SetLogLevel
from jiwer import cer
from pipeline import norm
p=argparse.ArgumentParser();p.add_argument('--model',default='models/vosk-model-small-cn-0.22');p.add_argument('--output',default='outputs/vosk');a=p.parse_args();out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True);SetLogLevel(-1)
t=time.perf_counter();model=Model(a.model);load=time.perf_counter()-t
sources=[('subway_eval','outputs/subway_eval/audio.wav','references/subway_10.954_28.894.txt'),('subway_full','outputs/subway_full_tiny_beam5/audio.wav',None),('ma_jian','outputs/ma_jian_tiny/audio.wav',None)]
results=[]
for name,wav,reference in sources:
 for rep in range(2):
  t=time.perf_counter();rec=KaldiRecognizer(model,16000);rec.SetWords(True);parts=[]
  with wave.open(wav,'rb') as w:
   assert w.getframerate()==16000 and w.getnchannels()==1 and w.getsampwidth()==2
   duration=w.getnframes()/w.getframerate()
   while True:
    data=w.readframes(4000)
    if not data:break
    if rec.AcceptWaveform(data):parts.append(json.loads(rec.Result()))
   parts.append(json.loads(rec.FinalResult()))
  elapsed=time.perf_counter()-t;text=''.join(x.get('text','').replace(' ','') for x in parts)
  row={'model':'vosk-model-small-cn-0.22','vosk_version':importlib.metadata.version('vosk'),'sample':name,'repeat':rep,'duration_seconds':duration,'inference_seconds':elapsed,'real_time_factor':elapsed/duration,'model_load_seconds':load,'transcript':text,'cer':cer(norm(pathlib.Path(reference).read_text()),norm(text)) if reference else None,'reference_label':'Published-caption reference, not independent listening' if reference else None,'segments':parts,'max_rss_kib_process_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
  results.append(row);(out/f'{name}_{rep}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in row.items() if k!='segments'},ensure_ascii=False),flush=True)
modelbytes=sum(p.stat().st_size for p in pathlib.Path(a.model).rglob('*') if p.is_file());(out/'results.json').write_text(json.dumps({'model_load_seconds':load,'model_uncompressed_bytes':modelbytes,'runs':results},ensure_ascii=False,indent=2))
