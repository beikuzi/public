"""Aggregate explicitly annotated sampled comments, never infer population opinion.
Input JSON list: id, text, primary_stance, optional author_hash, likes, sampling_group.
Excluded rows use primary_stance=null and exclusion_reason. Unknown/ambiguous is a
valid explicit label, not automatically dropped. Keep raw data private by default.
"""
import argparse, collections, json
from pathlib import Path

def aggregate(rows, min_sample=20):
    seen=set(); unique=[]
    for row in rows:
        key=str(row['id'])
        if key in seen: continue
        seen.add(key); unique.append(row)
    included=[r for r in unique if r.get('primary_stance')]
    counts=collections.Counter(r['primary_stance'] for r in included)
    likes=collections.Counter()
    for r in included: likes[r['primary_stance']]+=max(0,int(r.get('likes',0)))
    total_likes=sum(likes.values())
    return {
        'minimum_sample_for_display':min_sample,
        'percentage_status':'display_sample_only' if len(included)>=min_sample else 'suppressed_insufficient_sample',
        'scope':'Observed sampled comments only; not all viewers, users, or public opinion.',
        'received_rows':len(rows),'deduplicated_comments':len(unique),
        'included_comments':len(included),'excluded_comments':len(unique)-len(included),
        'exclusion_reasons':dict(collections.Counter(r.get('exclusion_reason','unspecified') for r in unique if not r.get('primary_stance'))),
        'sampling_groups':dict(collections.Counter(r.get('sampling_group','unknown') for r in unique)),
        'stances':[{'label':k,'count':v,'comment_share_pct':round(100*v/len(included),2) if len(included)>=min_sample else None,
          'likes_received':likes[k], 'share_of_sample_likes_pct':round(100*likes[k]/total_likes,2) if total_likes and len(included)>=min_sample else None}
          for k,v in counts.most_common()],
        'caveats':['One primary stance per included comment; explicitly annotated before aggregation.',
          'Likes measure engagement with sampled comments, not unique people or agreement.',
          'Hot comments, replies and latest comments have different selection biases.',
          'No population confidence interval is claimed for a convenience sample.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--min-sample',type=int,default=20);args=ap.parse_args()
    if args.min_sample<1: ap.error('--min-sample must be positive')
    rows=json.loads(Path(args.input).read_text(encoding='utf-8'))
    Path(args.output).write_text(json.dumps(aggregate(rows,args.min_sample),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
