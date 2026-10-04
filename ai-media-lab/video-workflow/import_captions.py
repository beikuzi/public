"""Preserve supplied captions and structured cues; never mistake captions for validated ASR."""
import argparse,json,pathlib,re,time,hashlib

def parse_srt(text):
 def sec(t):
  h,m,s=t.replace(',', '.').split(':');return int(h)*3600+int(m)*60+float(s)
 cues=[]
 for block in re.split(r'\n\s*\n',text.strip()):
  lines=block.strip().splitlines(); ti=next((i for i,l in enumerate(lines) if '-->' in l),None)
  if ti is None: continue
  start,end=lines[ti].split('-->');cues.append({'start':sec(start.strip()),'end':sec(end.strip().split()[0]),'text':'\n'.join(lines[ti+1:])})
 return cues
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('srt');p.add_argument('output');p.add_argument('--source-url',default='user supplied');a=p.parse_args();t=time.perf_counter();raw=pathlib.Path(a.srt).read_bytes();cues=parse_srt(raw.decode('utf-8-sig'));elapsed=time.perf_counter()-t
 out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'source':a.source_url,'source_sha256':hashlib.sha256(raw).hexdigest(),'parse_seconds':elapsed,'independently_verified':False,'cues':cues},ensure_ascii=False,indent=2));print(f'{len(cues)} cues parsed in {elapsed:.6f}s')
