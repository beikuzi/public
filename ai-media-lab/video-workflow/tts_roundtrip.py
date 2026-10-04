"""Offline ASR round-trip diagnostic of authored synthetic speech; not listening quality."""
import argparse,pathlib,json,datetime,time,platform,importlib.metadata
from types import SimpleNamespace
from pipeline import run_asr,command,reserve_output,sha256,save,norm,VERSION
p=argparse.ArgumentParser();p.add_argument('audio');p.add_argument('script');p.add_argument('--output',default='outputs/tts_roundtrip');a=p.parse_args();out=pathlib.Path(a.output);reserve_output(out);source=pathlib.Path(a.audio);script=pathlib.Path(a.script)
probe=json.loads(command(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(source)]).stdout);duration=float(probe['format']['duration']);save(out/'probe.json',probe)
manifest={'kind':'synthetic Mandarin TTS to ASR roundtrip, not human naturalness/listening or general speech accuracy','audio_filename':source.name,'source_sha256':sha256(source),'reference_filename':script.name,'reference_sha256':sha256(script),'pipeline_version':VERSION,'python':platform.python_version(),'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_hint_passed_to_model':False,'normalization':'NFKC; lowercase; keep only Unicode isalnum; no Traditional/Simplified conversion or forced matching'};manifest['versions']={x:importlib.metadata.version(x) for x in ['faster-whisper','ctranslate2','numpy','jiwer']};manifest['asr_options']={'model':'tiny','compute_type':'int8','threads':4,'beam_size':5,'word_timestamps':True,'vad':False,'offline':True,'script_hint':False};save(out/'run_manifest.json',manifest)
(out/'reference.txt').write_text(script.read_text());(out/'normalized_reference.txt').write_text(norm(script.read_text()))
t=time.perf_counter();wav=out/'audio_16k.wav';command(['ffmpeg','-nostdin','-y','-i',str(source),'-ac','1','-ar','16000',str(wav)]);elapsed=time.perf_counter()-t
result={'duration_seconds':duration,'resample_seconds':elapsed,'runs':[],'asr_status':'pending','diagnostic_domain':'synthetic_eSpeak_Mandarin'}
settings=SimpleNamespace(models=['tiny'],offline=True,threads=4,language='zh',reference=str(script),repeats=2,beam=5)
run_asr(settings,out,wav,duration,result)
