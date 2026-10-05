#!/usr/bin/env python3
"""Auditable annotation-driven character audio preparation (stdlib + FFmpeg)."""
import argparse, array, hashlib, json, math, os, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

VERSION = '0.2.0'
RATE = 48000
CHANNELS = 2

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()

def safe_path(path, root=None):
    p = Path(path).absolute()
    if '..' in p.parts: raise ValueError('Parent traversal is forbidden')
    for parent in [p, *p.parents]:
        if parent.is_symlink(): raise ValueError(f'Symlink forbidden: {parent}')
    if root is not None and not p.is_relative_to(Path(root).absolute()):
        raise ValueError('Path outside allowed root')
    return p

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))

def union_seconds(intervals):
    merged=[]
    for a,b in sorted(intervals):
        if merged and a <= merged[-1][1]: merged[-1][1]=max(merged[-1][1],b)
        else: merged.append([a,b])
    return sum(b-a for a,b in merged)

def finite(value):
    result=float(value)
    if not math.isfinite(result): raise ValueError('Nonfinite annotation number')
    return result

def prepare_segments(data, duration, threshold=.9, allow_unverified_overlap=False):
    target=data['target_speaker']; accepted=[]; excluded=[]; ids=set()
    rows=data['segments']
    for i,row in enumerate(rows):
        s=dict(row); s['id']=str(s.get('id', f'seg_{i:04d}'))
        if s['id'] in ids: raise ValueError('Duplicate annotation id')
        ids.add(s['id'])
        a,b=finite(s['start']),finite(s['end'])
        if a<0 or b<=a or b>duration+1/RATE: raise ValueError(f'Invalid interval {s["id"]}: {a}, {b}; duration={duration}')
        s['start_sample']=round(a*RATE); s['end_sample']=min(round(b*RATE),round(duration*RATE))
        s['start']=s['start_sample']/RATE; s['end']=s['end_sample']/RATE
        reasons=[]
        confidence=finite(s.get('confidence',0))
        if not 0<=confidence<=1: raise ValueError('Confidence outside [0,1]')
        if s.get('speaker')!=target: reasons.append('other_speaker')
        if confidence<threshold: reasons.append('low_confidence')
        if s.get('overlap') is True: reasons.append('annotated_overlap')
        elif s.get('overlap') is not False and not allow_unverified_overlap: reasons.append('unverified_overlap')
        if s.get('quality') not in ('clean','noisy'): reasons.append('unknown_quality')
        if not s.get('quality_evidence'): reasons.append('missing_quality_evidence')
        if s['end_sample']-s['start_sample']>10*RATE: reasons.append('long_utterance_needs_natural_pause_annotation')
        if reasons: s['exclusion_reasons']=reasons; excluded.append(s)
        else: accepted.append(s)
    # Any intersection with another annotated speaker is quarantined, regardless of confidence.
    kept=[]
    for s in accepted:
        others=[r for r in rows if r.get('speaker')!=target and finite(r['start'])<s['end'] and finite(r['end'])>s['start']]
        same=[r for r in accepted if r['id']!=s['id'] and r['start']<s['end'] and r['end']>s['start']]
        if others or same:
            s['exclusion_reasons']=['cross_speaker_overlap' if others else 'duplicate_or_overlapping_target_annotation']; excluded.append(s)
        else: kept.append(s)
    return sorted(kept,key=lambda x:x['start']), excluded

def batches(segments, gap_samples):
    current=[]; size=0
    for s in segments:
        n=s['end_sample']-s['start_sample']; add=n+(gap_samples if current else 0)
        if current and size+add>10*RATE: yield current; current=[]; size=0; add=n
        current.append(s); size+=add
    if current: yield current

def write_wav(path, samples, rate=RATE):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(CHANNELS); w.setsampwidth(2); w.setframerate(rate)
        if sys.byteorder!='little': samples=array.array('h',samples); samples.byteswap()
        w.writeframes(samples.tobytes())

def wav_info(path):
    try:
        with wave.open(str(path),'rb') as w:
            return {'frames':w.getnframes(),'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width':w.getsampwidth(),'duration_seconds':w.getnframes()/w.getframerate()}
    except wave.Error:
        streams=probe(path)['streams']; audio=[s for s in streams if s.get('codec_type')=='audio']
        if len(audio)!=1: raise ValueError('Expected exactly one WAV audio stream')
        s=audio[0]
        if s.get('codec_name') not in ('pcm_f32le','pcm_f64le','pcm_s24le','pcm_s32le','pcm_s16le'): raise ValueError('Expected uncompressed WAV')
        rate=int(s['sample_rate']); duration=float(s['duration']); frames=round(duration*rate)
        return {'frames':frames,'sample_rate':rate,'channels':int(s['channels']),'sample_width':int(s.get('bits_per_sample',0))//8,'codec_name':s['codec_name'],'duration_seconds':frames/rate}

def build(annotation_path, source, output, gap=.12, fade=.005, threshold=.9, allow_unverified_overlap=False):
    source=safe_path(source); annotation_path=safe_path(annotation_path); output=safe_path(output)
    if not source.is_file(): raise ValueError('Source is missing')
    if output.exists() and any(output.iterdir()): raise ValueError('Output must not already contain files')
    if not 0<=gap<=1 or not 0<=fade<=.05: raise ValueError('Invalid gap/fade')
    data=json.loads(annotation_path.read_text())
    source_hash=sha256(source)
    if not data.get('source_sha256') or data['source_sha256']!=source_hash: raise ValueError('Annotation source_sha256 does not match media')
    if data.get('timebase')!='decoded_audio_seconds': raise ValueError('Explicit decoded_audio_seconds timebase required')
    metadata=probe(source)
    if not any(s.get('codec_type')=='audio' for s in metadata['streams']): raise ValueError('No audio stream')
    with tempfile.TemporaryDirectory(prefix='character_audio_') as temp:
        pcm=Path(temp)/'decoded.wav'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(source),'-map','0:a:0','-vn','-ac',str(CHANNELS),'-ar',str(RATE),'-c:a','pcm_s16le',str(pcm)],check=True)
        with wave.open(str(pcm),'rb') as w: audio=array.array('h',w.readframes(w.getnframes()))
        if sys.byteorder!='little': audio.byteswap()
        duration=len(audio)/(RATE*CHANNELS)
        accepted,excluded=prepare_segments(data,duration,threshold,allow_unverified_overlap)
        output.mkdir(parents=True,exist_ok=True)
        for group in ('clean','noisy'):
            (output/group/'raw').mkdir(parents=True,exist_ok=True)
        (output/'noisy'/'voice_only').mkdir(exist_ok=True)
        manifest={'schema_version':1,'pipeline_version':VERSION,'provisional_unverified_overlap_allowed':allow_unverified_overlap,'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],'source':{'filename':source.name,'sha256':source_hash,'decoded_duration_seconds':duration,'timebase':'decoded_audio_seconds','input_probe':metadata},'annotation_sha256':sha256(annotation_path),'target_speaker':data['target_speaker'],'speaker_label_method':data.get('speaker_label_method','explicit annotations; not automatic speaker identification'),'quality_criteria':data.get('quality_criteria','clean requires affirmative listening/measurement evidence; unknown is excluded'),'rendering':{'sample_rate':RATE,'channels':CHANNELS,'pcm_bits':16,'downmix':'ffmpeg stereo rendering of first audio stream; preserves stereo when present','gap_seconds':gap,'edge_fade_seconds':fade,'time_stretch':False,'normalization':False},'clips':[],'excluded':excluded,'separation':{'status':'not_run','reason':'No separator output imported; raw is not voice_only'},'limitations':['Annotation-derived intervals are not measured pure speech; they may include breath or silence.','Concatenated utterances do not form a continuous original sentence.','Padding and inter-utterance gaps are not usable voice.','This pipeline does not automatically identify characters or certify training fitness.']}
        gap_n=round(gap*RATE); fade_n=round(fade*RATE)
        for group in ('clean','noisy'):
            for idx,items in enumerate(batches([s for s in accepted if s['quality']==group],gap_n)):
                clip_id=f'{group}_{idx:04d}'; samples=array.array('h'); mappings=[]; gap_total=0
                for s in items:
                    if samples: samples.extend([0]*(gap_n*CHANNELS)); gap_total+=gap_n
                    piece=audio[s['start_sample']*CHANNELS:s['end_sample']*CHANNELS]; nfade=min(fade_n,len(piece)//(2*CHANNELS))
                    for j in range(nfade):
                        weight=j/max(1,nfade)
                        for ch in range(CHANNELS):
                            piece[j*CHANNELS+ch]=round(piece[j*CHANNELS+ch]*weight); piece[-(j+1)*CHANNELS+ch]=round(piece[-(j+1)*CHANNELS+ch]*weight)
                    begin=len(samples)//CHANNELS; samples.extend(piece)
                    mappings.append({**s,'clip_start_sample':begin,'clip_end_sample':len(samples)//CHANNELS,'fade_samples_per_edge':nfade})
                padding=max(0,5*RATE-len(samples)//CHANNELS); samples.extend([0]*(padding*CHANNELS))
                relative=f'{group}/raw/{clip_id}.wav'; path=output/relative; write_wav(path,samples)
                info=wav_info(path)
                if not 5<=info['duration_seconds']<=10: raise AssertionError('Clip duration violation')
                manifest['clips'].append({'clip_id':clip_id,'quality':group,'raw_path':relative,'raw_sha256':sha256(path),'raw_audio':info,'source_mappings':mappings,'source_interval_seconds':sum(s['end']-s['start'] for s in items),'inserted_gap_seconds':gap_total/RATE,'trailing_padding_seconds':padding/RATE,'voice_only':None})
        manifest['statistics']=statistics(manifest)
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        (output/'statistics.json').write_text(json.dumps(manifest['statistics'],indent=2)+'\n')
    return manifest

def statistics(m):
    result={}
    for group in ('clean','noisy'):
        clips=[c for c in m['clips'] if c['quality']==group]
        intervals=[(s['start'],s['end']) for c in clips for s in c['source_mappings']]
        processed=[c['voice_only'] for c in clips if c.get('voice_only')]
        result[group]={'raw_clip_count':len(clips),'raw_file_duration_seconds':sum(c['raw_audio']['duration_seconds'] for c in clips),'unique_source_interval_seconds':union_seconds(intervals),'summed_source_interval_seconds':sum(b-a for a,b in intervals),'inserted_gap_seconds':sum(c['inserted_gap_seconds'] for c in clips),'trailing_padding_seconds':sum(c['trailing_padding_seconds'] for c in clips),'processed_clip_count':len(processed),'processed_file_duration_seconds':sum(v['audio']['duration_seconds'] for v in processed),'usable_voice_seconds':None,'usable_voice_seconds_note':'Not estimated: requires validated speech activity and separation quality review.'}
    all_intervals=[(s['start'],s['end']) for c in m['clips'] for s in c['source_mappings']]
    exclusions=[(s['start'],s['end']) for s in m['excluded']]
    target_exclusions=[(s['start'],s['end']) for s in m['excluded'] if s.get('speaker')==m['target_speaker']]
    result['coverage']={'source_duration_seconds':m['source']['decoded_duration_seconds'],'accepted_unique_seconds':union_seconds(all_intervals),'excluded_annotation_count':len(exclusions),'excluded_unique_seconds':union_seconds(exclusions),'excluded_target_unique_seconds':union_seconds(target_exclusions),'annotated_unique_seconds':union_seconds(all_intervals+exclusions),'unannotated_source_seconds':m['source']['decoded_duration_seconds']-union_seconds(all_intervals+exclusions),'exclusion_reason_counts':{reason:sum(reason in s['exclusion_reasons'] for s in m['excluded']) for reason in sorted({r for s in m['excluded'] for r in s['exclusion_reasons']})}}
    return result

def import_separation(dataset, report, allowed_root):
    dataset=safe_path(dataset); report=safe_path(report); root=safe_path(allowed_root)
    m=json.loads((dataset/'manifest.json').read_text()); entries=json.loads(report.read_text())['outputs']; by_id={c['clip_id']:c for c in m['clips']}
    if len({e['clip_id'] for e in entries})!=len(entries): raise ValueError('Duplicate separated clip IDs')
    staged=[]
    for entry in entries:
        clip=by_id[entry['clip_id']]
        if clip['quality']!='noisy': raise ValueError('Only noisy clips accept separation')
        raw=safe_path(dataset/clip['raw_path'],dataset)
        if sha256(raw)!=clip['raw_sha256'] or entry['input_sha256']!=clip['raw_sha256']: raise ValueError('Separator input hash mismatch')
        src=safe_path(entry['output_path'],root)
        for key in ('model','model_version','method','limitations'):
            if key not in entry: raise ValueError(f'Missing separator provenance: {key}')
        info=wav_info(src)
        if abs(info['duration_seconds']-clip['raw_audio']['duration_seconds'])>max(1/info['sample_rate'],.01): raise ValueError('Separator duration drift > 10ms')
        if not 5<=info['duration_seconds']<=10: raise ValueError('Separated duration outside 5–10s')
        dst=safe_path(dataset/'noisy'/'voice_only'/f'{clip["clip_id"]}.wav',dataset)
        if dst.exists(): raise ValueError('Refusing to overwrite separated audio')
        staged.append((entry,clip,src,dst,info))
    for entry,clip,src,dst,info in staged:
        shutil.copyfile(src,dst)
        clip['voice_only']={'path':str(dst.relative_to(dataset)),'sha256':sha256(dst),'audio':info,'provenance':entry,'quality_status':'requires_listening_review; voice_only is a processing label, not a purity guarantee'}
    m['separation']={'status':'complete' if all(c.get('voice_only') for c in m['clips'] if c['quality']=='noisy') else 'partial','report_sha256':sha256(report)}
    m['statistics']=statistics(m)
    (dataset/'manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n'); (dataset/'statistics.json').write_text(json.dumps(m['statistics'],indent=2)+'\n')
    return m

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build'); b.add_argument('--annotations',required=True); b.add_argument('--source',required=True); b.add_argument('--output',required=True); b.add_argument('--gap',type=float,default=.12); b.add_argument('--fade',type=float,default=.005); b.add_argument('--confidence',type=float,default=.9); b.add_argument('--allow-unverified-overlap',action='store_true',help='Explicit experimental mode: retain unknown overlap labels; not training-ready')
    s=sub.add_parser('import-separation'); s.add_argument('--dataset',required=True); s.add_argument('--report',required=True); s.add_argument('--allowed-root',required=True)
    a=p.parse_args()
    if a.command=='build': result=build(a.annotations,a.source,a.output,a.gap,a.fade,a.confidence,a.allow_unverified_overlap)
    else: result=import_separation(a.dataset,a.report,a.allowed_root)
    print(json.dumps(result['statistics'],indent=2))
if __name__=='__main__': main()
