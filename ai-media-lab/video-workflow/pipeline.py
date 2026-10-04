#!/usr/bin/env python3
"""Video evidence extraction. ASR remains an unverified hypothesis."""
import argparse,datetime,hashlib,importlib.metadata,json,os,pathlib,platform,re,resource,subprocess,time,unicodedata
from quality_gates import assess
VERSION='2.0.0'

def norm(s):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC',s) if c.isalnum())

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def command(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(f'Command failed ({p.returncode}): {args[0]}\n{p.stderr[-4000:]}')
    return p

def sha256(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def reserve_output(path):
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError(f'Output must be a new or empty directory: {path}. Existing evidence was not changed.')
    path.mkdir(parents=True,exist_ok=True)

def extract_frames(video,out,kind,selection,stream_start):
    start=time.perf_counter()
    p=command(['ffmpeg','-nostdin','-y','-copyts','-i',str(video),'-map','0:v:0','-an','-vf',f'select={selection},showinfo,scale=480:-1','-fps_mode','vfr',str(out/'frames'/f'{kind}_%03d.jpg')])
    (out/f'{kind}_ffmpeg.log').write_text(p.stderr)
    matches=re.findall(r'\bn:\s*\d+\s+pts:\s*(-?\d+)\s+pts_time:([\d.eE+-]+)',p.stderr)
    timebase=re.search(r'config in time_base: (\d+)/(\d+)',p.stderr)
    if not timebase:raise RuntimeError('Missing source frame timebase')
    numerator,denominator=map(int,timebase.groups())
    pts=[int(ticks)*numerator/denominator for ticks,_ in matches]
    images=sorted((out/'frames').glob(f'{kind}_*.jpg'))
    if len(pts)!=len(images):raise RuntimeError(f'{kind} timestamp/image mismatch: {len(pts)} vs {len(images)}')
    rows=[{'path':str(path.relative_to(out)),'kind':kind,'source_pts':int(matches[i][0]),'source_time_base':f'{numerator}/{denominator}','source_pts_seconds':timestamp,'video_relative_seconds':timestamp-stream_start,'timestamp_basis':'Decoded source frame PTS from FFmpeg showinfo with -copyts'} for i,(path,timestamp) in enumerate(zip(images,pts))]
    return rows,time.perf_counter()-start

def contact_sheet(out,rows):
    from PIL import Image,ImageDraw
    tiles=[]
    for row in rows:
        with Image.open(out/row['path']) as src:im=src.convert('RGB')
        tile=Image.new('RGB',(480,im.height+28),'white');tile.paste(im,(0,28))
        ImageDraw.Draw(tile).text((8,8),f"t={row['video_relative_seconds']:.3f}s | PTS={row['source_pts_seconds']:.3f}s",fill='black');tiles.append(tile)
    if not tiles:raise RuntimeError('Video produced no decodable frames')
    h=max(im.height for im in tiles);sheet=Image.new('RGB',(960,h*((len(tiles)+1)//2)),'#dddddd')
    for i,im in enumerate(tiles):sheet.paste(im,((i%2)*480,(i//2)*h))
    sheet.save(out/'contact_sheet.jpg')

def parse_args():
    p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('--output',default='outputs/run');p.add_argument('--models',nargs='+',default=['tiny','base']);p.add_argument('--language',default='zh');p.add_argument('--reference');p.add_argument('--threads',type=int,default=4);p.add_argument('--repeats',type=int,default=2);p.add_argument('--frames-only',action='store_true');p.add_argument('--beam',type=int,default=5);p.add_argument('--offline',action='store_true');p.add_argument('--interval',type=float,default=10);p.add_argument('--scene-threshold',type=float,default=.25)
    a=p.parse_args()
    if a.interval<=0 or a.threads<1 or a.repeats<1 or a.beam<1 or not 0<=a.scene_threshold<=1:p.error('Positive interval/threads/repeats/beam and scene threshold0–1 required')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name in ['.','..'] for name in a.models):p.error('Model names must be simple identifiers')
    return a

def main():
    a=parse_args();video=pathlib.Path(a.video).resolve();out=pathlib.Path(a.output)
    if not video.is_file():raise ValueError(f'Input is not a readable file: {video}')
    reserve_output(out)
    versions={}
    for package in ['faster-whisper','ctranslate2','av','numpy','Pillow','jiwer']:
        try:versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:versions[package]=None
    manifest={'pipeline_version':VERSION,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':{'filename':video.name,'bytes':video.stat().st_size,'sha256':sha256(video)},'options':vars(a),'versions':versions,'python':platform.python_version(),'platform':platform.platform(),'cpu_count':os.cpu_count(),'status':'running','timing_note':'v2 extraction differs from original benchmark; prior measurements were not overwritten'}
    if a.reference:manifest['reference_sha256']=sha256(pathlib.Path(a.reference))
    save(out/'run_manifest.json',manifest)
    try:
        manifest['ffmpeg_version']=command(['ffmpeg','-version']).stdout.splitlines()[0]
        info=json.loads(command(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(video)]).stdout);save(out/'probe.json',info)
        videos=[s for s in info['streams'] if s['codec_type']=='video'];audio=[s for s in info['streams'] if s['codec_type']=='audio']
        if not videos:raise ValueError('No video track')
        duration=float(info['format'].get('duration',videos[0].get('duration',0)));stream_start=float(videos[0].get('start_time',0));wav=out/'audio.wav'
        audio_seconds=0
        if audio:
            t=time.perf_counter();command(['ffmpeg','-nostdin','-y','-i',str(video),'-map','0:a:0','-vn','-ac','1','-ar','16000',str(wav)]);audio_seconds=time.perf_counter()-t
        (out/'frames').mkdir()
        uniform,uniform_seconds=extract_frames(video,out,'uniform',f'eq(n\\,0)+gte(t-prev_selected_t\\,{a.interval})',stream_start)
        scene,scene_seconds=extract_frames(video,out,'scene',f'eq(n\\,0)+gt(scene\\,{a.scene_threshold})',stream_start)
        save(out/'frame_index.json',uniform+scene);contact_sheet(out,uniform)
        result={'pipeline_version':VERSION,'duration_seconds':duration,'audio_track_present':bool(audio),'asr_status':'skipped_frames_only' if a.frames_only else ('pending' if audio else 'unavailable_no_audio_track'),'audio_extraction_seconds':audio_seconds,'uniform_frame_seconds':uniform_seconds,'scene_frame_seconds':scene_seconds,'uniform_count':len(uniform),'scene_count':len(scene),'runs':[]}
        if not audio:result['asr_status']='unavailable_no_audio_track'
        save(out/'extraction_results.json',result);save(out/'results.json',result)
        if not a.frames_only and audio:run_asr(a,out,wav,duration,result)
        manifest['status']='completed';manifest['asr_status']=result['asr_status'];save(out/'run_manifest.json',manifest)
        print(json.dumps({'output':str(out),'status':'completed','asr_status':result['asr_status'],'uniform_count':len(uniform),'scene_count':len(scene)}))
    except Exception as error:
        manifest['status']='failed';manifest['error']=str(error);save(out/'run_manifest.json',manifest);raise

def run_asr(a,out,wav,duration,result):
    import faster_whisper,jiwer,wave,numpy as np
    with wave.open(str(wav),'rb') as wf:waveform=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768
    if not len(waveform) or not np.any(waveform):
        result['asr_status']='unavailable_empty_or_digital_silence';save(out/'results.json',result);return
    ref=pathlib.Path(a.reference).read_text() if a.reference else None
    for name in a.models:
        modeldir=pathlib.Path('models')/name;t=time.perf_counter()
        if not a.offline:
            from faster_whisper.utils import download_model
            download_model(name,output_dir=str(modeldir))
        elif not (modeldir/'model.bin').exists():raise FileNotFoundError(f'Offline model missing: {modeldir}')
        download_seconds=0 if a.offline else time.perf_counter()-t
        t=time.perf_counter();model=faster_whisper.WhisperModel(str(modeldir),device='cpu',compute_type='int8',cpu_threads=a.threads);load_seconds=time.perf_counter()-t
        size=sum(f.stat().st_size for f in modeldir.rglob('*') if f.is_file())
        for rep in range(a.repeats):
            t=time.perf_counter();segments,meta=model.transcribe(waveform,language=a.language,beam_size=a.beam,temperature=0,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
            segs=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in (s.words or [])]} for s in segments];elapsed=time.perf_counter()-t;text=''.join(s['text'] for s in segs)
            row={'beam_size':a.beam,'model':name,'repeat':rep,'first_inference_after_load':rep==0,'model_download_seconds':download_seconds if rep==0 else 0,'model_load_seconds':load_seconds if rep==0 else 0,'model_bytes':size,'inference_seconds':elapsed,'real_time_factor':elapsed/duration if duration else None,'transcript':text,'cer':jiwer.cer(norm(ref),norm(text)) if ref else None,'max_rss_kib_process_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'timestamps_in_bounds':all(0<=s['start']<=s['end']<=duration+.5 for s in segs),'segments':segs,'quality_gate':assess(text,segs)}
            result['runs'].append(row);save(out/f'{name}_{rep}.json',row);save(out/'results.json',result)
            print(json.dumps({k:v for k,v in row.items() if k not in ['segments','transcript']},ensure_ascii=False),flush=True)
        del model
    result['asr_status']='completed_unverified_hypotheses';save(out/'results.json',result)

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,FileNotFoundError) as error:raise SystemExit(str(error))
