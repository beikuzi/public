#!/usr/bin/env python3
"""Import a user-authorized JSON or JSONL comment export; never fetch network data.
Public-safe normalized derivative excludes author identity. Full text stays local.
Input rows: id/comment_id, text, likes(optional), sampling_group(optional).
"""
import argparse, datetime, hashlib, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from comment_likes import row_likes

def normalize(rows):
    out=[]; seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict): raise ValueError(f'Row {i}: expected object')
        text=row.get('text')
        if not isinstance(text,str): raise ValueError(f'Row {i}: text must be a string')
        rid=row.get('id',row.get('comment_id'))
        if rid is None: raise ValueError(f'Row {i}: id/comment_id required for auditable deduplication')
        rid=str(rid)
        if rid in seen: continue
        seen.add(rid)
        groups=sorted({o.get('sort','unknown') for o in row.get('observations',[])})
        sample=row.get('sampling_group') or ('+'.join(groups) if groups else 'user_export_unknown')
        like=row_likes(row)
        item={'id':rid,'text':text,'likes':like['value'],'likes_status':like['status'],'sampling_group':sample}
        if like['reason'] is not None:item['likes_note']=like['reason']
        if row.get('primary_stance') is not None: item['primary_stance']=row['primary_stance']
        if row.get('exclusion_reason') is not None:item['exclusion_reason']=row['exclusion_reason']
        # Deliberately omit usernames, profile URLs, author IDs and inferred traits.
        out.append(item)
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('source');p.add_argument('--out',required=True); args=p.parse_args()
    src=pathlib.Path(args.source); blob=src.read_bytes(); text=blob.decode('utf-8-sig')
    rows=[json.loads(s) for s in text.splitlines() if s.strip()] if src.suffix=='.jsonl' else json.loads(text)
    if not isinstance(rows,list): raise ValueError('Input must be a list of row objects')
    normalized=normalize(rows); dest=pathlib.Path(args.out); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n')
    manifest={'source_basename':src.name,'source_sha256':hashlib.sha256(blob).hexdigest(),'import_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input_count':len(rows),'unique_count':len(normalized),'likes_validation':{status:sum(r['likes_status']==status for r in normalized) for status in ['observed','unknown','invalid']},'collection':'user_supplied_export; not independently fetched','sampling_note':'Use original source metadata for dates, pages and root/reply context; absence remains unknown.'}
    dest.with_suffix('.provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Imported {len(normalized)} unique comments; raw source unchanged. Keep text private.')
if __name__=='__main__': main()
