#!/usr/bin/env python3
"""Conservative phrase-matched proposals; no speaker/overlap verification."""
import json
from pathlib import Path
from audit import norms,wer,SR
ROOT=Path(__file__).resolve().parent

def phrase_match(caption,signal):
 words=[w for seg in signal.get('asr_segments',[]) for w in seg.get('words',[])]
 target=norms(caption);best=None
 for a in range(len(words)):
  for b in range(a+1,min(len(words),a+len(target)+3)+1):
   text=' '.join(w['word'] for w in words[a:b]);score=wer(caption,text)
   rank=(score,abs(len(norms(text))-len(target)),b-a)
   if best is None or rank<best[0]:best=(rank,{'text':text.strip(),'wer':score,'start':words[a]['start'],'end':words[b-1]['end']})
 return best[1] if best else {'text':'','wer':1,'start':0,'end':0}
def summarize(report):
 rows=[]
 for s in report['segments']:
  eligible=[];matches={}
  for name,v in s['signals'].items():
   m=phrase_match(s['caption'],v);matches[name]=m
   lo=s['context_start_sample']+round(m['start']*SR);hi=s['context_start_sample']+round(m['end']*SR)
   regs=[r for r in v['speech_regions'] if r['start_sample'] < hi and r['end_sample'] > lo]
   seconds=sum(r['end_sample']-r['start_sample'] for r in regs)/SR
   if m['wer']<=.25 and seconds>=.2 and not v['flags'] and len(norms(s['caption']))>=3:
    eligible.append((name,v,regs,m))
  longest=max((sum(r['end_sample']-r['start_sample'] for r in z[2]) for z in eligible),default=0)
  eligible.sort(key=lambda z: (sum(r['end_sample']-r['start_sample'] for r in z[2]) < .7*longest, {'center':0,'stereo':1,'neural_vocals':2}[z[0]]))
  row={'id':s['id'],'target':s['target'],'speaker_label':s['speaker_label'],'speaker_identity_verified':False,'overlap':None,'human_auditory_review':False,'original_caption_start_sample':s['caption_start_sample'],'original_caption_end_sample':s['caption_end_sample'],'proposal_status':'quarantine_ambiguous','proposed_regions':[],'independent_phrase_matches':matches,'reasons':[]}
  if eligible:
   name,v,regs,m=eligible[0]
   row.update(proposal_status='machine_supported_candidate',boundary_signal=name,proposed_regions=regs,supporting_signals=[n for n,*_ in eligible],proposed_speech_seconds=sum(r['end_sample']-r['start_sample'] for r in regs)/SR,proposed_start_sample=min(r['start_sample'] for r in regs),proposed_end_sample=max(r['end_sample'] for r in regs))
   row['reasons']=['At least three caption words and independently decoded matching phrase WER <=0.25 with VAD support. Full contextual VAD regions intersecting the matched ASR phrase are retained; no fixed offset assumed.','Not auditory verified; VAD does not establish character identity or absence of overlap.']
  else:
   if len(norms(s['caption']))<3:row['reasons'].append('Short utterance or proper name: recognition is useful evidence but insufficient for automatic admission.')
   if not any(v['caption_overlap_speech_seconds']>=.2 for v in s['signals'].values()):row['reasons'].append('No substantial VAD overlap inside caption; see context detections before discarding.')
   row['reasons'].append('Insufficient ASR/VAD support for automatic boundary repair; preserve evidence in quarantine.')
  rows.append(row)
 # Any proposed inter-caption collision is a blocker, never silently resolved.
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   if a.get('proposed_start_sample',10**20)<b.get('proposed_end_sample',-1) and b.get('proposed_start_sample',10**20)<a.get('proposed_end_sample',-1):
    for x in (a,b):x['proposal_status']='quarantine_proposed_boundary_collision';x['reasons'].append('Proposed contextual boundary overlaps another caption proposal.')
 return {'schema_version':2,'complete':report['complete'],'sample_rate':SR,'timebase':'decoded_audio_samples','source_sha256':report.get('source_sha256'),'overlap_resolved':False,'speaker_identity_verified':False,'proposals':rows}
if __name__=='__main__':
 r=summarize(json.loads((ROOT/'audit.json').read_text()));(ROOT/'boundary-proposals.json').write_text(json.dumps(r,indent=2))
 for s in r['proposals']:print(s['id'],s['proposal_status'],s.get('boundary_signal'),s.get('proposed_speech_seconds'),s['proposed_regions'])
