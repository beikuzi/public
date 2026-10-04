#!/usr/bin/env python3
"""Offline SenseVoice for local audio/video. Reference text is optional and never a model hint."""
import argparse,datetime,hashlib,json,pathlib,shutil,subprocess,sys,tempfile,time,unicodedata,wave
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from quality_gates import assess
VERSION='2.0.0'

def sha(path):
    with pathlib.Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def norm(text):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC',text) if c.isalnum())

def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(previous[j]+1,row[-1]+1,previous[j-1]+(x!=y)))
        previous=row
    return previous[-1]

def reference_score(reference,hypothesis):
    if reference is None:return {'reference_characters':None,'edit_distance':None,'cer':None,'accuracy_status':'unverified_no_reference'}
    normalized=norm(reference)
    if not normalized:raise ValueError('Reference must contain at least one alphanumeric character after normalization')
    edits=distance(normalized,norm(hypothesis))
    return {'reference_characters':len(normalized),'edit_distance':edits,'cer':edits/len(normalized),'accuracy_status':'reference_agreement_only_not_independent_accuracy'}

def command(args):
    p=subprocess.run(args,capture_output=True,text=True)
    if p.returncode:raise ValueError(f'{args[0]} failed: {p.stderr[-2000:]}')
    return p

def local_file(value,label):
    path=pathlib.Path(value).expanduser().resolve()
    if not path.is_file():raise ValueError(f'{label} must be an existing local regular file: {value}')
    return path

def validate_request(audio,reference,output,model):
    source=local_file(audio,'Input')
    out=pathlib.Path(output).expanduser()
    if out.exists() or out.is_symlink():raise ValueError('Output must be a new directory; existing paths are never overwritten')
    refpath=local_file(reference,'Reference') if reference is not None else None
    reftext=refpath.read_text(encoding='utf-8') if refpath else None
    if reftext is not None:reference_score(reftext,'')
    probe=json.loads(command(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(source)]).stdout)
    tracks=[s for s in probe.get('streams',[]) if s.get('codec_type')=='audio']
    if not tracks:raise ValueError('Input has no audio track; no ASR output was created')
    modeldir=pathlib.Path(model).expanduser().resolve()
    for name in ['model.int8.onnx','tokens.txt']:
        path=local_file(modeldir/name,'Model asset')
        if path.stat().st_size==0:raise ValueError(f'Empty model asset: {name}')
    return source,refpath,reftext,out,modeldir,probe,tracks[0]

def parse_args(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio',help='Local audio/video file supported by FFmpeg; URLs and network protocols are not accepted')
    parser.add_argument('reference',nargs='?',help='Optional UTF-8 reference used only after recognition for CER scoring')
    parser.add_argument('--output',required=True,help='A new output directory')
    parser.add_argument('--model',default=str(ROOT/'models/sensevoice-int8'),help='Local reviewed SenseVoice directory containing model.int8.onnx and tokens.txt')
    parser.add_argument('--repeats',type=int,default=2)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args(argv)
    if args.repeats<1 or args.threads<1:parser.error('Repeats and threads must be positive')
    return args

def main(argv=None):
    args=parse_args(argv)
    source,refpath,reference,out,model,probe,track=validate_request(args.audio,args.reference,args.output,args.model)
    # Dependencies and model are loaded only after read-only request validation.
    import numpy as np
    import sherpa_onnx
    with tempfile.TemporaryDirectory(prefix='sensevoice-decode-') as temporary:
        wav=pathlib.Path(temporary)/'audio_16k.wav';start=time.perf_counter()
        command(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-i',str(source),'-map','0:a:0','-vn','-ac','1','-ar','16000',str(wav)])
        resample_seconds=time.perf_counter()-start
        with wave.open(str(wav)) as w:
            if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('Decoded audio is not PCM16mono16000Hz')
            if w.getnframes()==0:raise ValueError('Input decoded to empty audio')
            samples=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
        start=time.perf_counter()
        recognizer=sherpa_onnx.OfflineRecognizer.from_sense_voice(model=str(model/'model.int8.onnx'),tokens=str(model/'tokens.txt'),num_threads=args.threads,language='zh',use_itn=False,provider='cpu')
        model_load_seconds=time.perf_counter()-start
        # No destination is created until input, reference, decoding, and model validation succeed.
        out.mkdir(parents=True,exist_ok=False)
        shutil.copyfile(wav,out/'audio_16k.wav')
    manifest={'cli_version':VERSION,'source':{'filename':source.name,'sha256':sha(source),'sample_rate':track.get('sample_rate'),'channels':track.get('channels'),'codec':track.get('codec_name'),'format_duration_seconds':probe.get('format',{}).get('duration')},'reference_sha256':sha(refpath) if refpath else None,'resampled_sha256':sha(out/'audio_16k.wav'),'resampled_rate':16000,'runtime':sherpa_onnx.__version__,'model':model.name,'model_sha256':sha(model/'model.int8.onnx'),'options':{'threads':args.threads,'repeats':args.repeats,'language':'zh','itn':False,'decoding':'greedy_search','maximum_chunk_seconds':20,'script_hint':False},'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'normalization':'NFKC lowercase alphanumeric only; no Traditional/Simplified conversion','scope':'Audio reference agreement when supplied; no-reference output remains unverified','status':'running'}
    (out/'probe.json').write_text(json.dumps(probe,indent=2))
    if reference is not None:(out/'reference.txt').write_text(reference)
    def save_manifest():(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    save_manifest();runs=[]
    try:
        for repeat in range(args.repeats):
            start=time.perf_counter();segments=[]
            for offset in range(0,len(samples),320000):
                stream=recognizer.create_stream();stream.accept_waveform(16000,samples[offset:offset+320000]);recognizer.decode_stream(stream);r=stream.result
                segments.append({'offset_seconds':offset/16000,'text':r.text,'tokens':list(r.tokens),'timestamps_seconds_global':[offset/16000+x for x in r.timestamps]})
            elapsed=time.perf_counter()-start;text=''.join(s['text'] for s in segments)
            row={'repeat':repeat,'inference_seconds':elapsed,'duration_seconds':len(samples)/16000,**reference_score(reference,text),'transcript':text,'segments':segments,'quality_gate':assess(text)}
            runs.append(row);(out/f'run_{repeat}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2))
            (out/'results.json').write_text(json.dumps({'model_load_seconds':model_load_seconds,'resample_seconds':resample_seconds,'runs':runs},ensure_ascii=False,indent=2))
            print(json.dumps({k:v for k,v in row.items() if k not in ['segments','transcript']},ensure_ascii=False),flush=True)
        manifest['status']='completed';save_manifest()
    except Exception as error:
        manifest['status']='failed';manifest['error']=str(error);save_manifest();raise

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,FileExistsError,UnicodeError) as error:raise SystemExit(str(error))
