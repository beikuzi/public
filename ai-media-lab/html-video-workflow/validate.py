#!/usr/bin/env python3
"""Verify live media, never trust cached ffprobe.json. Single-writer local workflow."""
import array,hashlib,json,math,pathlib,re,subprocess,sys,wave
from fractions import Fraction
from safe_io import checked_path,guard_directory,safe_target,write_text
VALIDATOR_VERSION='1.4.0'

def require(condition,message):
    if not condition:raise ValueError(message)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def sidecar_cues(path):
    text=path.read_text(encoding='utf-8').replace('\r','').strip()
    if text.startswith('WEBVTT'):text=text[len('WEBVTT'):].strip()
    cues=[]
    def seconds(value):
        h,m,s=map(float,value.replace(',','.').split(':'));return h*3600+m*60+s
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines()
        if lines and lines[0].isdigit():lines=lines[1:]
        require(len(lines)==2,'Malformed or multiline subtitle sidecar')
        match=re.fullmatch(r'(\d{2}:\d{2}:\d{2}[,.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,.]\d{3})',lines[0])
        require(match is not None,'Malformed subtitle time')
        cues.append((seconds(match[1]),seconds(match[2]),lines[1]))
    return cues

def validate_directory(directory):
    root=guard_directory(directory)
    names=['demo.mp4','timing.json','narration.wav','subtitles.srt','subtitles.vtt']
    for name in names:require(checked_path(root/name).is_file(),f'Missing regular input {name}')
    for name in ['validation.json','verified-ffprobe.json']+[f'check-{i}.png' for i in range(1,5)]:safe_target(root/name)
    # Count actual decoded frames; cached ffprobe.json is intentionally neither read nor trusted.
    raw=subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_format','-show_streams','-of','json',str(root/'demo.mp4')])
    p=json.loads(raw);videos=[s for s in p['streams'] if s['codec_type']=='video'];audios=[s for s in p['streams'] if s['codec_type']=='audio']
    require(len(videos)==1 and len(audios)==1,'Current MP4 must have exactly one video and one audio stream')
    v,a=videos[0],audios[0]
    require(v['codec_name']=='h264' and a['codec_name']=='aac','Expected H.264/AAC in current MP4')
    require((v['width'],v['height'],v['pix_fmt'])==(1280,720,'yuv420p'),'Unexpected live video dimensions/format')
    fps=float(Fraction(v['avg_frame_rate']));require(fps==30,'Expected actual 30fps video')
    vd,ad=float(v['duration']),float(a['duration']);require(0<vd<=600 and 0<ad<=600,'Invalid/oversized media duration')
    require(abs(vd-ad)<=1/fps,'Actual A/V durations differ by more than one frame')
    t=json.loads((root/'timing.json').read_text());require(t['fps']==fps,'Timeline FPS differs from live video')
    scenes=t['scenes'];cues=t['cues'];require(len(scenes)==4 and len(cues)>0,'Expected four scenes and nonempty cues')
    require(int(v['nb_read_frames'])==sum(s['frames'] for s in scenes),'Actual decoded frame count differs from timeline')
    with wave.open(str(root/'narration.wav')) as w:
        require(w.getnchannels()==1 and w.getsampwidth()==2,'Expected mono PCM16 source narration')
        sr=w.getframerate();source=array.array('h',w.readframes(w.getnframes()));wd=len(source)/sr
    require(abs(wd-vd)<=1/fps,'Source WAV and current video duration mismatch')
    last=0
    for i,s in enumerate(scenes,1):
        require(s['slide']==i and type(s['frames']) is int and s['frames']>0,'Invalid scene/frame numbering')
        require(math.isfinite(s['start']) and math.isfinite(s['end']),'Nonfinite scene time')
        require(abs(s['start']-last)<=1/sr and s['end']>s['start'],'Scenes must be contiguous and positive')
        require(abs(s['end']-s['start']-s['frames']/fps)<=2/sr,'Scene duration does not match its frames')
        last=s['end']
    require(abs(last-vd)<=1/fps,'Timeline endpoint differs from current video')
    prev=0
    for c in cues:
        require(isinstance(c['text'],str) and bool(c['text'].strip()),'Empty subtitle text')
        require(type(c['slide']) is int and 1<=c['slide']<=4,'Invalid cue scene index')
        require(math.isfinite(c['start']) and math.isfinite(c['end']),'Nonfinite cue time')
        require(prev<=c['start']<c['end']<=min(vd,ad,wd),'Cue overlaps or exceeds current media bounds');prev=c['end']
        s=scenes[c['slide']-1];require(s['start']<=c['start']<c['end']<=s['end'],'Cue exceeds its scene')
    for ext in ['srt','vtt']:
        sidecar=sidecar_cues(root/f'subtitles.{ext}');require(len(sidecar)==len(cues),'Subtitle count differs from timing')
        for actual,expected in zip(sidecar,cues):
            require(abs(actual[0]-expected['start'])<=.001 and abs(actual[1]-expected['end'])<=.001 and actual[2]==expected['text'],'Subtitle sidecar differs from timing')
    # Decode the audio actually muxed in MP4; checking narration.wav alone misses silent/replaced mux audio.
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'demo.mp4'),'-map','0:a:0','-ac','1','-ar',str(sr),'-f','s16le','pipe:1'])
    decoded=array.array('h',pcm);require(len(decoded)>0,'Current MP4 decoded audio is empty')
    peak=max(map(abs,decoded));require(500<peak<32767,'Current MP4 audio is silent or clipped')
    source_peak=max(map(abs,source));require(500<source_peak<32767,'Source narration is silent or clipped')
    require(abs(len(decoded)/sr-vd)<=max(1/fps,2048/int(a['sample_rate'])),'Decoded mux audio duration mismatch')
    rms=[]
    for c in cues:
        chunk=decoded[round(c['start']*sr):min(round(c['end']*sr),len(decoded))]
        value=math.sqrt(sum(x*x for x in chunk)/len(chunk)) if chunk else 0
        require(value>10,'A cue has no audible energy in the current mux audio');rms.append(value)
    n=min(len(source),len(decoded));dot=sum(source[i]*decoded[i] for i in range(n));den=math.sqrt(sum(x*x for x in source[:n])*sum(x*x for x in decoded[:n]))
    similarity=dot/den if den else 0
    require(similarity>.25,'Current mux audio does not correlate with the declared narration WAV')
    for i,s in enumerate(scenes,1):
        ts=(s['start']+s['end'])/2;target=safe_target(root/f'check-{i}.png')
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(ts),'-i',str(root/'demo.mp4'),'-frames:v','1',str(target)],check=True)
    result={'checks':'PASS','validator_version':VALIDATOR_VERSION,'probe_source':'fresh ffprobe of current demo.mp4, with actual decoded frame count','media_sha256':sha(root/'demo.mp4'),'narration_sha256':sha(root/'narration.wav'),'timing_sha256':sha(root/'timing.json'),'sentence_cues':len(cues),'frames':int(v['nb_read_frames']),'audio_peak_pcm16':source_peak,'mux_audio_peak_pcm16':peak,'mux_to_source_cosine_similarity':similarity,'minimum_cue_mux_rms_pcm16':min(rms),'audio_peak_dbfs':round(20*math.log10(source_peak/32768),2),'av_duration_difference_seconds':abs(vd-ad),'subtitle_policy':'Sidecars checked against sample-derived sentence timeline and live media bounds; cue audio energy checked in actual decoded mux. Not word alignment, OCR of burned-in captions, or human intelligibility validation.'}
    write_text(root/'verified-ffprobe.json',json.dumps(p,indent=2));write_text(root/'validation.json',json.dumps(result,indent=2));return result

def main():
    root=guard_directory(sys.argv[1] if len(sys.argv)>1 else 'neural-melo-preview')
    try:result=validate_directory(root)
    except Exception as e:
        write_text(root/'validation.json',json.dumps({'checks':'FAIL','validator_version':VALIDATOR_VERSION,'error':str(e)},indent=2));raise
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
