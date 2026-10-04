#!/usr/bin/env python3
"""Offline authored HTML → PDF → PNG → H264/AAC. No browser, API or model download."""
import argparse, ctypes, hashlib, html, importlib.util, json, math, os, pathlib, re, subprocess, time, wave
from safe_io import checked_path, guard_directory, safe_target, write_text
ROOT=pathlib.Path(__file__).resolve().parent

SOURCE_VERSION='1.4.0'
MARKER='.html-video-output.json'

def plain_text(value, name, maximum, multiline=False):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f'{name}: nonempty plain text required')
    if any(ord(c)<32 and not(multiline and c=='\n') for c in value):
        raise ValueError(f'{name}: control characters are forbidden')
    if '<' in value or '>' in value or re.search(r'(?i)(?:https?|file|data|javascript|ftp):',value):
        raise ValueError(f'{name}: markup, URLs and asset references are forbidden')
    if len(value)>maximum: raise ValueError(f'{name}: maximum {maximum} characters')
    return value

def validate_project(project):
    if not isinstance(project,dict) or set(project)!={'title','slides'}:
        raise ValueError('Project must contain only title and slides')
    plain_text(project['title'],'project title',40)
    slides=project['slides']
    if not isinstance(slides,list) or len(slides)!=4:
        raise ValueError('This fixed-layout template requires exactly four slides')
    keys={'label','title','accent','keyword','note','cards','lines'}
    for i,slide in enumerate(slides):
        if not isinstance(slide,dict) or set(slide)!=keys:
            raise ValueError(f'Slide {i+1}: unexpected or missing schema fields')
        plain_text(slide['label'],'label',24)
        title=plain_text(slide['title'],'slide title',17,True).split('\n')
        if len(title)>2 or any(not line.strip() or len(line)>8 for line in title):
            raise ValueError('Slide title allows at most two nonempty lines of eight characters')
        if not isinstance(slide['accent'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',slide['accent']):
            raise ValueError('Accent must be a six-digit hex color')
        plain_text(slide['keyword'],'keyword',2)
        plain_text(slide['note'],'note',24)
        if not isinstance(slide['cards'],list) or len(slide['cards'])!=3:
            raise ValueError('Exactly three cards are required per slide')
        for card in slide['cards']:
            if not isinstance(card,list) or len(card)!=2: raise ValueError('Card must be [heading, text]')
            plain_text(card[0],'card heading',8);plain_text(card[1],'card text',20)
        if not isinstance(slide['lines'],list) or not 1<=len(slide['lines'])<=4:
            raise ValueError('Each slide requires one to four narration sentences')
        for line in slide['lines']:plain_text(line,'narration/subtitle',30)
    return project

def prepare_output(name, overwrite=False):
    # Restrict paths to owned local directories, avoiding FFmpeg-filter path escaping.
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*',name):
        raise ValueError('Output must be a relative simple directory path, e.g. output/run-1')
    out=ROOT/name
    for part in [out,*out.parents]:
        if part==ROOT:break
        if part.is_symlink():raise ValueError('Symlink output paths are forbidden')
    out=out.resolve()
    if ROOT not in out.parents or (out.exists() and not out.is_dir()):
        raise ValueError('Output must be a directory inside this project')
    if out.exists():guard_directory(out)
    marker=out/MARKER
    checked_path(marker,allow_missing=True)
    if out.exists() and any(out.iterdir()):
        if not overwrite:raise ValueError('Output is nonempty; use a new directory or explicit --overwrite')
        if not marker.is_file() or json.loads(marker.read_text()).get('owner')!='html-video-workflow':
            raise ValueError('Refusing to overwrite an unrecognized directory')
    out.mkdir(parents=True,exist_ok=True)
    write_text(marker,json.dumps({'owner':'html-video-workflow','source_version':SOURCE_VERSION}))
    return out

def run(*args):
    for arg in args:
        if isinstance(arg,pathlib.Path):
            checked_path(arg,allow_missing=True)
            guard_directory(arg.parent)
    subprocess.run(list(map(str,args)),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def robot(accent, word):
    return f'''<svg width="320" height="280" viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 44 L80 20 M255 36 L298 14 M12 140 L48 130 M266 151 L312 170" stroke="{accent}" stroke-width="5"/>
    <ellipse cx="171" cy="246" rx="99" ry="17" fill="#080b14"/>
    <path d="M90 195 L58 217 L37 193 M245 195 L267 160 L291 178" fill="none" stroke="#f5f3ed" stroke-width="17" stroke-linejoin="round"/>
    <path d="M116 212 L111 246 M209 212 L222 246" stroke="#f5f3ed" stroke-width="18"/>
    <rect x="88" y="143" width="150" height="82" rx="23" fill="{accent}" stroke="#090c17" stroke-width="6"/>
    <rect x="70" y="35" width="192" height="137" rx="30" fill="#f5f3ed" stroke="#090c17" stroke-width="6"/>
    <path d="M230 35 L262 67 L230 67 Z" fill="{accent}"/>
    <rect x="96" y="75" width="133" height="59" rx="20" fill="#141b2d"/>
    <path d="M123 100 L130 108 L141 93 M182 96 L200 96" fill="none" stroke="{accent}" stroke-width="7" stroke-linecap="round"/>
    <path d="M153 119 Q165 129 177 117" fill="none" stroke="#f5f3ed" stroke-width="3"/>
    <text x="162" y="198" text-anchor="middle" font-family="Noto Sans CJK SC" font-size="25" font-weight="700" fill="#141b2d">{html.escape(word)}</text>
    </svg>'''

def make_html(project, voice_footer="合成旁白 · eSpeak-NG 中文机械音"):
    validate_project(project)
    css='''@page {size:1280px 720px;margin:0} *{box-sizing:border-box}body{margin:0;font-family:"Noto Sans CJK SC",sans-serif;color:#f4f3ec;background:#101728}section{width:1280px;height:720px;position:relative;overflow:hidden;break-after:page;background:#101728;padding:40px 58px}section:last-child{break-after:auto}.top{font-size:17px;letter-spacing:2px;color:#a9b4c5}.brand{float:right;font-size:14px;letter-spacing:1px}.rule{height:2px;background:#364051;margin-top:17px}.left{position:absolute;left:58px;top:113px;width:600px}.label{font-size:16px;font-weight:700;letter-spacing:3px}h1{font-size:64px;line-height:1.22;margin:17px 0 24px;letter-spacing:-2px}.note{font-size:21px;color:#c4cede;margin-top:13px}.robot{position:absolute;left:88px;top:366px;transform:rotate(-5deg) scale(.85);transform-origin:top left}.cards{position:absolute;left:660px;right:58px;top:124px}.card{border:2px solid #364051;border-radius:16px;padding:18px 23px;margin-bottom:17px;background:#172137;height:128px}.cardhead{font-size:16px;letter-spacing:3px;font-weight:bold}.cardtext{font-size:25px;line-height:1.45;margin-top:9px}.footer{position:absolute;left:58px;right:58px;bottom:99px;font-size:14px;color:#91a0b7}.counter{float:right}.subzone{position:absolute;left:0;right:0;bottom:0;height:88px;background:#080d17}.dots{position:absolute;left:440px;top:425px;font-size:29px;line-height:1.6;color:#4b5972}'''
    out=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+html.escape(project['title'])+'</title><style>'+css+'</style><body>']
    for i,s in enumerate(project['slides']):
        a=s['accent']; title=html.escape(s['title']).replace('\n','<br>')
        cards=''.join(f'<div class="card"><div class="cardhead" style="color:{a}">{html.escape(k)}</div><div class="cardtext">{html.escape(v)}</div></div>' for k,v in s['cards'])
        out.append(f'<section><div class="top">TEXT → VIDEO LAB<span class="brand">原创分镜 / 本地合成演示</span></div><div class="rule"></div><div class="left"><div class="label" style="color:{a}">{html.escape(s["label"])}</div><h1>{title}</h1><div class="note">{html.escape(s["note"])}</div></div><div class="robot">{robot(a,s["keyword"])}</div><div class="dots">· · ·<br>· · ·<br>· · ·</div><div class="cards">{cards}</div><div class="footer">{html.escape(voice_footer)}<span class="counter">{i+1:02d} / 04</span></div><div class="subzone"></div></section>')
    return ''.join(out)+'</body></html>'

class Voice:
    def __init__(self,rate):
        root=pathlib.Path(importlib.util.find_spec('piper').origin).parent
        self.lib=ctypes.CDLL(str(root/'espeakbridge.so'))
        self.lib.espeak_Initialize.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
        self.sr=self.lib.espeak_Initialize(2,0,str(root).encode(),0)
        if self.sr<=0: raise RuntimeError('eSpeak initialization failed')
        self.lib.espeak_SetVoiceByName.argtypes=[ctypes.c_char_p]
        if self.lib.espeak_SetVoiceByName(b'cmn')!=0: raise RuntimeError('Mandarin cmn voice unavailable')
        self.lib.espeak_SetParameter(1,rate,0)
        self.lib.espeak_SetParameter(2,65,0)
        self.frames=[]
        CB=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.POINTER(ctypes.c_short),ctypes.c_int,ctypes.c_void_p)
        @CB
        def cb(data,n,events):
            if data and n:self.frames.append(ctypes.string_at(data,n*2))
            return 0
        self.cb=cb;self.lib.espeak_SetSynthCallback(cb)
        self.lib.espeak_Synth.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p]
    def say(self,text):
        self.frames=[];data=text.encode('utf-8')
        result=self.lib.espeak_Synth(data,len(data)+1,0,1,0,1,None,None)
        if result: raise RuntimeError(f'eSpeak synth error {result}')
        self.lib.espeak_Synchronize();return b''.join(self.frames)

def timestamp(t,sep=','):
    n=round(t*1000);h,n=divmod(n,3600000);m,n=divmod(n,60000);s,ms=divmod(n,1000)
    return f'{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='output');p.add_argument('--backend',choices=['espeak','aishell3','melo'],default='espeak');p.add_argument('--model-dir');p.add_argument('--speaker',type=int);p.add_argument('--speed',type=float,default=1.0);p.add_argument('--overwrite',action='store_true');p.add_argument('--rate',type=int,default=225);p.add_argument('--preset',default='veryfast');p.add_argument('--threads',type=int,default=4);args=p.parse_args()
    if not 80<=args.rate<=350:p.error('--rate must be between 80 and 350')
    if not 1<=args.threads<=32:p.error('--threads must be between 1 and 32')
    if args.preset not in {'ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'}:p.error('Invalid x264 preset')
    if not .5<=args.speed<=2:p.error('--speed must be between 0.5 and 2')
    if args.backend!='espeak' and not args.model_dir:p.error('--model-dir is required for neural backends')
    if args.backend=='espeak' and args.model_dir:p.error('--model-dir only applies to neural backends')
    if args.speaker is None:args.speaker=0 if args.backend=='melo' else 10
    start=time.perf_counter();metrics={};project=validate_project(json.loads((ROOT/'project.json').read_text()))
    out=prepare_output(args.out,args.overwrite)
    voice_name='eSpeak-NG cmn (synthetic)' if args.backend=='espeak' else f'{args.backend} VITS neural preset {args.speaker} (unreviewed preview)'
    voice_footer='合成旁白 · eSpeak-NG 中文机械音' if args.backend=='espeak' else f'{args.backend} 神经配音试听版 · 未经过人工可懂度/自然度验收'
    source=make_html(project,voice_footer);write_text(out/'slides.html',source)
    checked_path(ROOT/'.cache',allow_missing=True)
    (ROOT/'.cache').mkdir(exist_ok=True)
    guard_directory(ROOT/'.cache')
    os.environ['XDG_CACHE_HOME']=str(ROOT/'.cache')
    from weasyprint import HTML
    def deny_network(url):
        raise ValueError('External resources are disabled; use inline authored assets')
    t=time.perf_counter();HTML(string=source,url_fetcher=deny_network).write_pdf(safe_target(out/'slides.pdf'));run('pdftoppm','-png','-r','96',out/'slides.pdf',out/'slide');metrics['html_pdf_png_seconds']=time.perf_counter()-t
    assert len(list(out.glob('slide-*.png')))==len(project['slides'])
    t=time.perf_counter();load_start=time.perf_counter()
    if args.backend=='espeak':voice=Voice(args.rate)
    else:
        from neural_voice import NeuralVoice
        voice=NeuralVoice(args.model_dir,args.speaker,args.speed,args.backend)
    metrics['voice_load_seconds']=time.perf_counter()-load_start
    synthesis_start=time.perf_counter();pcm=bytearray();cues=[];scenes=[];fps=30
    for i,slide in enumerate(project['slides']):
        scene_start=len(pcm)/(2*voice.sr)
        pcm.extend(bytes(round(.18*voice.sr)*2))
        for line in slide['lines']:
            audio=voice.say(line);begin=len(pcm)/(2*voice.sr);pcm.extend(audio);end=len(pcm)/(2*voice.sr)
            cues.append(dict(text=line,start=begin,end=end,slide=i+1));pcm.extend(bytes(round(.10*voice.sr)*2))
        duration=len(pcm)/(2*voice.sr)-scene_start+.20;nframes=math.ceil(duration*fps)
        target=round((scene_start+nframes/fps)*voice.sr)*2
        pcm.extend(bytes(max(0,target-len(pcm))));scenes.append(dict(slide=i+1,start=scene_start,end=len(pcm)/(2*voice.sr),frames=nframes))
    metrics['sentence_synthesis_and_timing_seconds']=time.perf_counter()-synthesis_start
    metrics['audio_gain']=1.0
    if args.backend!='espeak':
        import numpy as np
        samples=np.frombuffer(pcm,dtype='<i2').astype(np.float64)
        peak=float(np.abs(samples).max())
        gain=(32767*10**(-3/20))/peak if peak else 1.0
        pcm=bytearray(np.round(samples*gain).astype('<i2').tobytes());metrics['audio_gain']=gain
    with wave.open(str(safe_target(out/'narration.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(voice.sr);w.writeframes(pcm)
    write_text(out/'narration.txt','\n'.join(c['text'] for c in cues))
    for ext,sep in [('srt',','),('vtt','.')]:
        text=('WEBVTT\n\n' if ext=='vtt' else '')+'\n\n'.join(f'{i+1}\n{timestamp(c["start"],sep)} --> {timestamp(c["end"],sep)}\n{c["text"]}' for i,c in enumerate(cues))+'\n'
        write_text(out/f'subtitles.{ext}',text)
    write_text(out/'timing.json',json.dumps(dict(fps=fps,voice=voice_name,backend=args.backend,sample_rate=voice.sr,cues=cues,scenes=scenes),ensure_ascii=False,indent=2));metrics['tts_timing_seconds']=time.perf_counter()-t
    t=time.perf_counter()
    for scene in scenes:
        i=scene['slide'];dur=scene['frames']/fps
        filt=f'fade=t=in:st=0:d=0.18,fade=t=out:st={dur-.18}:d=0.18,format=yuv420p'
        run('ffmpeg','-y','-v','error','-loop','1','-framerate',fps,'-i',out/f'slide-{i}.png','-vf',filt,'-frames:v',scene['frames'],'-c:v','libx264','-preset',args.preset,'-crf','20','-threads',args.threads,out/f'clip-{i}.mp4')
    write_text(out/'concat.txt',''.join(f"file 'clip-{s['slide']}.mp4'\n" for s in scenes))
    run('ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',out/'concat.txt','-c','copy',out/'visuals.mp4')
    style='FontName=Noto Sans CJK SC,FontSize=20,PrimaryColour=&H00F3F3F4,OutlineColour=&H00170D08,Outline=1,Alignment=2,MarginV=18'
    run('ffmpeg','-y','-v','error','-i',out/'visuals.mp4','-i',out/'narration.wav','-vf',f"subtitles='{out/'subtitles.srt'}':force_style='{style}'",'-c:v','libx264','-preset',args.preset,'-crf','20','-threads',args.threads,'-c:a','aac','-ar','48000','-b:a','128k','-movflags','+faststart','-shortest',out/'demo.mp4')
    metrics['ffmpeg_encode_seconds']=time.perf_counter()-t
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(out/'demo.mp4')]))
    write_text(out/'ffprobe.json',json.dumps(probe,indent=2));metrics.update(training_data_provenance='undisclosed in reviewed upstream sources' if args.backend=='melo' else 'see provenance documentation',backend=args.backend,voice=voice_name,source_sample_rate=voice.sr,model_sha256=getattr(voice,'model_sha256',None),neural_voice_py_sha256=hashlib.sha256((ROOT/'neural_voice.py').read_bytes()).hexdigest() if args.backend!='espeak' else None,source_version=SOURCE_VERSION,render_py_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),project_sha256=hashlib.sha256((ROOT/'project.json').read_bytes()).hexdigest(),total_seconds=time.perf_counter()-start,video_seconds=float(probe['format']['duration']),bytes=(out/'demo.mp4').stat().st_size,fps=fps,width=1280,height=720,threads=args.threads,paid_api_cost_usd=0,render_strategy='4 offline HTML static rasterizations; FFmpeg fades; audio-derived sentence subtitles')
    write_text(out/'benchmark.json',json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
