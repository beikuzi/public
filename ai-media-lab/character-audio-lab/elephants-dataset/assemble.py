#!/usr/bin/env python3
"""Multi-source, authored-character dataset assembly. No identity, isolation or purity certification."""
import argparse,array,hashlib,json,math,os,subprocess,sys,tempfile
from pathlib import Path
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from dataset import safe_path,sha256,wav_info,union_seconds,batches,RATE,CHANNELS

def require(ok,reason):
    if not ok: raise ValueError(reason)

def decode_region(path,a,b):
    result=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map','0:a:0','-af',f'atrim=start_sample={a}:end_sample={b},asetpts=PTS-STARTPTS','-ac','2','-ar',str(RATE),'-f','f32le','-'])
    x=array.array('f');x.frombytes(result)
    if sys.byteorder!='little':x.byteswap()
    require(len(x)==(b-a)*2,'Decoded region frame count differs from requested source mapping')
    require(all(math.isfinite(v) for v in x),'Nonfinite source audio')
    return x

def source_audio_info(path):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))
    streams=[s for s in data['streams'] if s.get('codec_type')=='audio'];require(bool(streams),'No source audio')
    s=streams[0];rate=int(s['sample_rate'])
    if 'duration_ts' in s:frames=round(int(s['duration_ts'])*Fraction(s['time_base'])*rate)
    else:frames=round(float(s['duration'])*rate)
    return {'sample_rate':rate,'channels':int(s['channels']),'frames':frames,'duration_seconds':frames/rate,'codec':s['codec_name']}

def validate_ref(ref,sources):
    source=sources[ref['source_id']];a=ref['start_frame'];b=ref['end_frame']
    require(type(a) is int and type(b) is int and 0<=a<b<=source['audio']['frames'],'Invalid source frame interval')
    require(b-a<=10*RATE,'Utterance exceeds10s; natural-pause reannotation required')
    return source,a,b

def render(path,clip_items,variant,sources,gap_frames=5760,fade_frames=240):
    samples=array.array('f');mapping=[]
    for item in clip_items:
        ref=item[variant];source,a,b=validate_ref(ref,sources)
        if samples:samples.extend([0.]*(gap_frames*2))
        start=len(samples)//2;piece=decode_region(source['path'],a,b);fade=min(fade_frames,(b-a)//2)
        for j in range(fade):
            for ch in (0,1):
                w=j/max(1,fade);piece[j*2+ch]*=w;piece[-(j+1)*2+ch]*=w
        samples.extend(piece)
        mapping.append({'voice_unit_id':item['id'],'speaker':item['speaker'],'source_id':ref['source_id'],'source_sha256':source['sha256'],'source_start_frame':a,'source_end_frame':b,'clip_start_frame':start,'clip_end_frame':len(samples)//2,'fade_frames':fade,'source_ref':ref,'speech_regions':item.get('speech_regions',[]),'speech_regions_timebase':'author source frames, not this variant','quality':item.get('quality',{}),'alignment':item.get('alignment'),'overlap_status':item.get('overlap_status','unknown')})
    before_padding=len(samples)//2;padding=max(0,5*RATE-before_padding);samples.extend([0.]*(padding*2))
    frames=len(samples)//2;require(5*RATE<=frames<=10*RATE,'Output duration outside5–10s')
    peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/max(1,len(samples)))
    if sys.byteorder!='little':samples.byteswap()
    codec='pcm_f32le' if variant=='separated' else 'pcm_s16le'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','f32le','-ar',str(RATE),'-ac','2','-i','pipe:0','-c:a',codec,str(path)],input=samples.tobytes(),check=True)
    info=wav_info(path);require(info['frames']==frames,'Output frame drift')
    return {'audio':info,'sha256':sha256(path),'mappings':mapping,'source_interval_seconds':sum((m['source_end_frame']-m['source_start_frame'])/RATE for m in mapping),'gap_seconds':max(0,len(mapping)-1)*gap_frames/RATE,'padding_seconds':padding/RATE,'preencoding_peak':peak,'preencoding_rms_dbfs':20*math.log10(max(rms,1e-12)),'samples_at_or_above_full_scale':sum(abs(v)>=1 for v in samples)}

def source_union(items,variant):
    groups={}
    for s in items:
        if variant in s:
            r=s[variant];groups.setdefault(r.get('source_sha256',r['source_id']),[]).append((r['start_frame']/RATE,r['end_frame']/RATE))
    return {'seconds':sum(union_seconds(v) for v in groups.values()),'per_source_seconds':{k:union_seconds(v) for k,v in groups.items()}}

def activity_union(items):
    groups={}
    for s in items:
        sid=s['author'].get('source_sha256',s['author']['source_id']);groups.setdefault(sid,[]).extend((r['start_frame']/RATE,r['end_frame']/RATE) for r in s.get('speech_regions',[]))
    return sum(union_seconds(v) for v in groups.values())

def build(config_path,output):
    config_path=safe_path(config_path);output=safe_path(output);config=json.loads(config_path.read_text())
    require(not output.exists(),'Output must not exist (no overwrite)')
    require(config.get('sample_rate')==RATE,'Only explicit48k frame timebase supported')
    sources={}
    for sid,source in config['sources'].items():
        row=dict(source);path=safe_path(row['path']);require(sha256(path)==row['sha256'],'Source hash mismatch: '+sid);row['path']=str(path);row['audio']=source_audio_info(path)
        require(row['audio']['sample_rate']==RATE,'Source needs explicit pre-resampling provenance before assembly')
        sources[sid]=row
    selected=[];excluded=[];ids=set()
    for item in config['segments']:
        s=dict(item);require(s['id'] not in ids,'Duplicate voice unit ID');ids.add(s['id'])
        source,a,b=validate_ref(s['author'],sources);reasons=[]
        for variant in ('author','movie','separated'):
            if variant in s:s[variant]['source_sha256']=sources[s[variant]['source_id']]['sha256']
        if s.get('speaker')!=config['target_speaker']:reasons.append('other_role')
        if source.get('role')!=s.get('speaker'):reasons.append('source_role_label_mismatch')
        if s.get('machine_qc_pass') is not True:reasons.append('machine_qc_not_passed')
        if source.get('kind')!='authored_role_labelled_production_wav':reasons.append('author_source_provenance_not_confirmed')
        if s.get('overlap_status')=='known_cross_role_overlap':reasons.append('known_cross_role_overlap')
        if s.get('quarantine_reason'):reasons.append(s['quarantine_reason'])
        for region in s.get('speech_regions',[]):
            require(type(region['start_frame']) is int and type(region['end_frame']) is int and a<=region['start_frame']<region['end_frame']<=b,'VAD frame region outside author selection')
        if 'movie' in s:
            movie_source,ma,mb=validate_ref(s['movie'],sources)
            require(movie_source.get('kind')=='movie_mix','Movie reference must use movie_mix source kind')
            require(mb-ma==b-a,'Aligned movie and author intervals must preserve exact length')
            if s.get('alignment',{}).get('accepted') is not True:reasons.append('movie_alignment_not_accepted')
        if 'separated' in s:
            require('movie' in s,'Separated result requires matched movie reference')
            separated_source,sa,sb=validate_ref(s['separated'],sources);require(sb-sa==b-a,'Separated source region duration differs')
            require(separated_source.get('kind')=='contextual_separated_vocals','Separated reference must use contextual_separated_vocals source kind')
            require(sources[s['separated']['source_id']].get('model_provenance'),'Missing separator provenance')
        if reasons:s['exclusion_reasons']=reasons;excluded.append(s)
        else:selected.append(s)
    require(selected,'No admitted segments')
    # Never duplicate the same source interval as if it were new voice content.
    for variant in ('author','movie'):
        refs=[(s,s[variant]) for s in selected if variant in s]
        for i,(s,r) in enumerate(refs):
            for other,t in refs[i+1:]:
                require(r['source_sha256']!=t['source_sha256'] or r['end_frame']<=t['start_frame'] or t['end_frame']<=r['start_frame'],'Overlapping selected source intervals require review')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dataset-staging-',dir=output.parent) as temp:
        stage=Path(temp)/'ready';stage.mkdir()
        for folder in ('clean/raw','noisy/raw','noisy/voice_only'):(stage/folder).mkdir(parents=True)
        manifest={'schema_version':1,'pipeline':'multi-source authored role assembly v1','config_sha256':sha256(config_path),'target_speaker':config['target_speaker'],'sample_rate':RATE,'sources':sources,'training_ready':False,'human_auditory_review':False,'clean_folder_meaning':'Authored role-labelled production-source candidate with machine QC; isolation and clean purity are unverified.','noisy_folder_meaning':'Verified matched film mix and contextual neural vocal separation; not guaranteed target-only.','rendering':{'rate':RATE,'channels':2,'mono_to_stereo':'FFmpeg default equal-power conversion','gap_frames':5760,'edge_fade_frames':240,'no_time_stretch':True},'selected_voice_units':selected,'excluded':excluded,'clips':[],'license':config.get('license',{}),'limitations':config.get('limitations',[])}
        variant_folders={'author':'clean/raw','movie':'noisy/raw','separated':'noisy/voice_only'}
        for variant,folder in variant_folders.items():
            available=[s for s in selected if variant in s]
            # Matched variants use identical item ordering and grouping when coverage is identical.
            packed=[{**s,'start_sample':0,'end_sample':s[variant]['end_frame']-s[variant]['start_frame']} for s in available]
            for i,group in enumerate(batches(packed,5760)):
                rel=f'{folder}/{variant}_{i:04d}.wav';result=render(stage/rel,group,variant,sources)
                manifest['clips'].append({'variant':variant,'path':rel,**result})
        stats={}
        for variant,folder in variant_folders.items():
            clips=[c for c in manifest['clips'] if c['variant']==variant];items=[s for s in selected if variant in s]
            stats[folder]={'clip_count':len(clips),'file_seconds':sum(c['audio']['duration_seconds'] for c in clips),'source_unique_seconds':source_union(items,variant)['seconds'],'source_summed_seconds':sum(c['source_interval_seconds'] for c in clips),'gap_seconds':sum(c['gap_seconds'] for c in clips),'padding_seconds':sum(c['padding_seconds'] for c in clips),'machine_estimated_voice_seconds':activity_union(items),'machine_estimate_basis':'Author-source VAD projected by mapping; not a separate activity/purity measurement on movie or separated outputs','human_verified_usable_voice_seconds':None}
        stats['deduplicated_voice_units']={'count':len(selected),'author_unique_source_seconds':source_union(selected,'author')['seconds'],'machine_estimated_voice_seconds':activity_union(selected),'note':'Paired author, movie and separated versions are alternate copies, never summed as new voice.'}
        stats['coverage']={'available_author_files':sum(s.get('kind')=='authored_role_labelled_production_wav' for s in sources.values()),'selected_voice_units':len(selected),'excluded_voice_units':len(excluded),'full_movie_exhaustive':False}
        manifest['statistics']=stats
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');(stage/'statistics.json').write_text(json.dumps(stats,indent=2)+'\n')
        os.rename(stage,output)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(build(a.config,a.output)['statistics'],indent=2))
