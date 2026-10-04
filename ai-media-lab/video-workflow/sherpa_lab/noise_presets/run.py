import pathlib,json,subprocess,time,hashlib,wave,sys,argparse
parser=argparse.ArgumentParser();parser.add_argument('--python',default=sys.executable,help='Interpreter with sherpa-onnx installed');parser.add_argument('--model',required=True,help='Local reviewed SenseVoice directory');args=parser.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[2];spec=json.loads((ROOT/'sherpa_lab/noise_presets/presets.json').read_text());source=ROOT/spec['source'];assert hashlib.sha256(source.read_bytes()).hexdigest()==spec['source_sha256'];metrics=[]
for preset in spec['variants']:
 target=ROOT/'sherpa_lab/noise_presets'/f"{preset['name']}.wav"
 if target.exists():raise RuntimeError('Refuse overwrite waveform')
 t=time.perf_counter();subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(source),'-af',preset['ffmpeg_filter'],'-ar','16000','-ac','1',str(target)],check=True);seconds=time.perf_counter()-t
 with wave.open(str(target)) as w:
  frames=w.readframes(w.getnframes());duration=w.getnframes()/w.getframerate();assert w.getframerate()==16000 and w.getnchannels()==1 and w.getsampwidth()==2
 row={**preset,'preprocessing_seconds':seconds,'wav_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'pcm_sha256':hashlib.sha256(frames).hexdigest(),'duration_seconds':duration};metrics.append(row);(ROOT/'sherpa_lab/noise_presets/preprocessing.json').write_text(json.dumps(metrics,indent=2))
 output=ROOT/'outputs'/f"sensevoice_noise_{preset['name']}"
 with (ROOT/'sherpa_lab/noise_presets'/f"{preset['name']}.log").open('w') as log:
  subprocess.run([args.python,str(ROOT/'sherpa_lab/recognize_audio.py'),str(target),str(ROOT/spec['reference']),'--output',str(output),'--model',args.model],stdout=log,stderr=subprocess.STDOUT,check=True)
