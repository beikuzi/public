#!/usr/bin/env python3
import array,json,pathlib,subprocess,sys,wave
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'final')
t=json.loads((root/'timing.json').read_text());p=json.loads((root/'ffprobe.json').read_text());v=next(x for x in p['streams'] if x['codec_type']=='video');a=next(x for x in p['streams'] if x['codec_type']=='audio')
assert v['codec_name']=='h264' and a['codec_name']=='aac'
assert (v['width'],v['height'])==(1280,720) and v['pix_fmt']=='yuv420p'
assert abs(float(v['duration'])-float(a['duration']))<=1/30
assert int(v['nb_frames'])==sum(s['frames'] for s in t['scenes'])
prev=0
for c in t['cues']:
 assert prev<=c['start']<c['end']<=float(v['duration']);prev=c['end']
 s=t['scenes'][c['slide']-1];assert s['start']<=c['start']<c['end']<=s['end']
with wave.open(str(root/'narration.wav')) as w:
 data=array.array('h',w.readframes(w.getnframes()));sr=w.getframerate()
peak=max(map(abs,data));assert 500<peak<32767
for i,s in enumerate(t['scenes'],1):
 ts=(s['start']+s['end'])/2
 subprocess.run(['ffmpeg','-y','-v','error','-ss',str(ts),'-i',str(root/'demo.mp4'),'-frames:v','1',str(root/f'check-{i}.png')],check=True)
result={'checks':'PASS','sentence_cues':len(t['cues']),'frames':int(v['nb_frames']),'audio_peak_pcm16':peak,'audio_peak_dbfs':round(20*__import__('math').log10(peak/32768),2),'av_duration_difference_seconds':abs(float(v['duration'])-float(a['duration'])),'subtitle_policy':'Sentence-level, exact generated waveform duration; not forced-aligned word timing. Includes TTS leading/trailing silence.'}
(root/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
