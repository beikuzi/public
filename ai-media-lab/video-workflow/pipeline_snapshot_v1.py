#!/usr/bin/env python3
"""Local video evidence pipeline. ASR outputs are hypotheses, not visual analysis."""
import argparse,json,pathlib,subprocess,time,unicodedata,os,platform,resource
from quality_gates import assess

def run(args):
    subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def norm(s):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC',s) if c.isalnum())
def main():
    p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('--output',default='outputs');p.add_argument('--models',nargs='+',default=['tiny','base']);p.add_argument('--language',default='zh');p.add_argument('--reference');p.add_argument('--threads',type=int,default=4);p.add_argument('--repeats',type=int,default=2);p.add_argument('--frames-only',action='store_true');p.add_argument('--beam',type=int,default=5);p.add_argument('--offline',action='store_true');a=p.parse_args()
    out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    video=str(pathlib.Path(a.video).resolve()); start=time.perf_counter()
    info=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',video]));(out/'probe.json').write_text(json.dumps(info,indent=2))
    duration=float(info['format']['duration']);wav=out/'audio.wav'
    run(['ffmpeg','-y','-i',video,'-vn','-ac','1','-ar','16000',str(wav)])
    extraction_seconds=time.perf_counter()-start
    frames=out/'frames';frames.mkdir(exist_ok=True)
    t=time.perf_counter();run(['ffmpeg','-y','-i',video,'-vf',"fps=1/10,scale=480:-1",str(frames/'uniform_%03d.jpg')]); uniform_seconds=time.perf_counter()-t
    t=time.perf_counter();run(['ffmpeg','-y','-i',video,'-vf',"select=eq(n\\,0)+gt(scene\\,0.25),scale=480:-1",'-fps_mode','vfr',str(frames/'scene_%03d.jpg')]);scene_seconds=time.perf_counter()-t
    from PIL import Image,ImageDraw
    imgs=sorted(frames.glob('uniform_*.jpg'));thumbs=[]
    for i,path in enumerate(imgs):
        im=Image.open(path).convert('RGB'); tile=Image.new('RGB',(480,im.height+28),'white');tile.paste(im,(0,28));ImageDraw.Draw(tile).text((8,8),f'Uniform sample {i+1} (~{i*10+5}s)',fill='black');thumbs.append(tile)
    if thumbs:
        w=960;h=max(x.height for x in thumbs);sheet=Image.new('RGB',(w,h*((len(thumbs)+1)//2)), '#dddddd')
        for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*480,(i//2)*h))
        sheet.save(out/'contact_sheet.jpg')
    (out/'frame_index.json').write_text(json.dumps([{'path':str(path),'approximate_video_seconds':i*10+5,'timestamp_basis':'FFmpeg fps=1/10 nearest frame; not verified exact PTS'} for i,path in enumerate(imgs)],indent=2))
    if a.frames_only:
        (out/"extraction_results.json").write_text(json.dumps({"duration_seconds":duration,"audio_extraction_seconds":extraction_seconds,"uniform_frame_seconds":uniform_seconds,"scene_frame_seconds":scene_seconds,"uniform_count":len(imgs),"scene_count":len(list(frames.glob("scene*")))},indent=2));return
    import faster_whisper,jiwer
    import wave,numpy as np
    with wave.open(str(wav),'rb') as wf: waveform=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768
    ref=pathlib.Path(a.reference).read_text() if a.reference else None
    results={'duration_seconds':duration,'machine':{'python':platform.python_version(),'platform':platform.platform(),'cpu_count':os.cpu_count(),'threads':a.threads},'audio_extraction_seconds':extraction_seconds,'uniform_frame_seconds':uniform_seconds,'scene_frame_seconds':scene_seconds,'uniform_count':len(imgs),'scene_count':len(list(frames.glob('scene*'))),'runs':[]}
    for name in a.models:
        modeldir=pathlib.Path('models')/name
        t=time.perf_counter()
        from faster_whisper.utils import download_model
        if not a.offline: download_model(name,output_dir=str(modeldir))
        elif not (modeldir/'model.bin').exists(): raise FileNotFoundError(f'Offline model missing: {modeldir}')
        download_seconds=time.perf_counter()-t
        t=time.perf_counter(); model=faster_whisper.WhisperModel(str(modeldir),device='cpu',compute_type='int8',cpu_threads=a.threads);load_seconds=time.perf_counter()-t
        size=sum(f.stat().st_size for f in modeldir.rglob('*') if f.is_file())
        for rep in range(a.repeats):
            t=time.perf_counter();segments,meta=model.transcribe(waveform,language=a.language,beam_size=a.beam,temperature=0,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
            segs=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in (s.words or [])]} for s in segments];elapsed=time.perf_counter()-t
            text=''.join(s['text'] for s in segs); row={'beam_size':a.beam,'model':name,'repeat':rep,'first_inference_after_load':rep==0,'model_download_seconds':download_seconds if rep==0 else 0,'model_load_seconds':load_seconds if rep==0 else 0,'model_bytes':size,'inference_seconds':elapsed,'real_time_factor':elapsed/duration,'transcript':text,'cer':jiwer.cer(norm(ref),norm(text)) if ref else None,'max_rss_kib_process_cumulative':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'timestamps_in_bounds':all(0<=s['start']<=s['end']<=duration+.5 for s in segs),'segments':segs}
            row['quality_gate']=assess(text,segs)
            results['runs'].append(row);(out/f'{name}_{rep}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2));(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in row.items() if k not in ['segments','transcript']},ensure_ascii=False),flush=True)
        del model
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
