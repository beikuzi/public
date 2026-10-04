#!/usr/bin/env python3
"""Conservative anonymous public Bilibili acquisition. No login, cookies, spoofing, or bypass.
Run only in an environment where ordinary access is permitted. Stops on first access gate.
Stdlib only. Media is deliberately not auto-downloaded after access failure.
"""
import argparse, datetime, hashlib, json, pathlib, time, urllib.parse, urllib.request, urllib.error

class AccessBlocked(Exception): pass

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bvid'); p.add_argument('--out', default='evidence'); p.add_argument('--pages',type=int,default=3)
    args=p.parse_args()
    if not args.bvid.startswith('BV') or not args.bvid.isalnum(): p.error('Expected a BV identifier')
    if not 1 <= args.pages <= 5: p.error('pages must be 1..5')
    out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=True)
    audit=[]; comments={}; raw=[]
    def get(url):
        row={'url':url,'capture_utc':utc(),'authentication':'none'}; audit.append(row)
        try:
            with urllib.request.urlopen(url,timeout=30) as response:
                body=response.read(); row.update(http_status=response.status,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        except urllib.error.HTTPError as e:
            row.update(http_status=e.code,error=str(e)); raise AccessBlocked(f'HTTP {e.code} at {url}; no retry or alternate route')
        except Exception as e:
            row.update(error=f'{type(e).__name__}: {e}'); raise AccessBlocked(row['error'])
        text=body.decode('utf-8',errors='replace')
        # No retry when a public endpoint returns an application-level denial.
        if url.startswith('https://api.bilibili.com/'):
            obj=json.loads(text); row['api_code']=obj.get('code')
            if obj.get('code') != 0: raise AccessBlocked(f'API code {obj.get("code")}: {obj.get("message")}')
            return obj['data'],row
        return text,row
    status='incomplete'; blocker=None
    try:
        page=f'https://www.bilibili.com/video/{args.bvid}/'
        html,_=get(page)
        # Presence of a normal optional login button is not itself a gate.
        if '访问权限不足' in html or '访问被拒绝' in html: raise AccessBlocked('Page access gate')
        data,_=get('https://api.bilibili.com/x/web-interface/view?'+urllib.parse.urlencode({'bvid':args.bvid}))
        meta={k:data.get(k) for k in ['bvid','aid','cid','title','duration','pubdate','desc','pages','stat']}
        meta.update(url=page,uploader=data.get('owner',{}).get('name'),capture_utc=utc())
        save(out/'video_metadata.json',meta)
        # Sample first N pages of each public sort, maximum 200 requested root records.
        # Keep only comment text and evidence IDs, never author profile/name/ID.
        for sort,label in [(2,'hot'),(0,'latest')]:
            for pn in range(1,args.pages+1):
                time.sleep(2)
                endpoint='https://api.bilibili.com/x/v2/reply?'+urllib.parse.urlencode({'type':1,'oid':data['aid'],'sort':sort,'pn':pn,'ps':20,'nohot':1})
                response,a=get(endpoint)
                roots=response.get('replies') or []
                def ingest(r,kind,parent=None):
                    rid=str(r.get('rpid_str') or r.get('rpid'))
                    item={'comment_id':rid,'root_id':str(r.get('root') or rid),'parent_id':parent,'kind':kind,'text':r.get('content',{}).get('message',''),'likes':r.get('like'),'created_unix':r.get('ctime'),'observations':[{'sort':label,'page':pn,'capture_utc':a['capture_utc'],'source_url':endpoint}]}
                    if rid in comments: comments[rid]['observations']+=item['observations']
                    else: comments[rid]=item
                    for child in r.get('replies') or []: ingest(child,'reply_preview',rid)
                for r in roots: ingest(r,'root')
                raw.append({'sort':label,'page':pn,'capture_utc':a['capture_utc'],'page_info':response.get('page'),'root_count':len(roots)})
                if not roots: break
        status='comments_acquired_media_not_downloaded'
    except AccessBlocked as e:
        status='blocked'; blocker=str(e)
    finally:
        with (out/'comments.jsonl').open('w',encoding='utf-8') as f:
            for r in comments.values(): f.write(json.dumps(r,ensure_ascii=False)+'\n')
        save(out/'sampling.json',{'requested_pages_per_sort':args.pages,'requested_page_size':20,'sorts':{'hot':2,'latest':0},'dedup_key':'comment_id','count_unique':len(comments),'pages':raw,'limitations':['Convenience sample, not representative.','Nested replies limited to API previews.','Sort behavior is platform-controlled and may change.','Text retained locally; do not publish full corpus.']})
        save(out/'provenance.json',{'bvid':args.bvid,'status':status,'blocker':blocker,'audit':audit})
    print(json.dumps({'status':status,'comments':len(comments),'blocker':blocker},ensure_ascii=False))
    return 2 if status=='blocked' else 0
if __name__=='__main__': raise SystemExit(main())
