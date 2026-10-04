"""Aggregate explicitly annotated sampled comments, never infer population opinion.
Likes must be observed nonnegative integer counts. Missing/invalid counts remain
unknown; like-share percentages require complete coverage of included comments.
Deduplication keeps the first occurrence, including its original like observation.
"""
import argparse,collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from comment_likes import row_likes

def aggregate(rows,min_sample=20):
    if min_sample<1:raise ValueError('min_sample must be positive')
    seen=set();unique=[]
    for row in rows:
        key=str(row['id'])
        if key in seen:continue
        seen.add(key);unique.append(row)
    included=[r for r in unique if r.get('primary_stance')]
    counts=collections.Counter(r['primary_stance'] for r in included)
    likes=collections.Counter();coverage=collections.Counter();per_stance={}
    for row in included:
        value=row_likes(row);label=row['primary_stance'];coverage[value['status']]+=1
        per_stance.setdefault(label,collections.Counter())[value['status']]+=1
        if value['status']=='observed':likes[label]+=value['value']
    n=len(included);observed=coverage['observed'];total_observed_likes=sum(likes.values())
    complete=bool(n) and observed==n
    coverage_status='no_eligible_comments' if not n else ('complete' if complete else ('none_observed' if not observed else 'incomplete'))
    if n<min_sample:like_share_status='suppressed_insufficient_sample'
    elif not complete:like_share_status='suppressed_incomplete_likes_coverage'
    elif not total_observed_likes:like_share_status='suppressed_zero_observed_likes'
    else:like_share_status='display_sample_only'
    stances=[]
    for label,count in counts.most_common():
        cov=per_stance[label];known=cov['observed'];stance_complete=known==count
        stances.append({'label':label,'count':count,'comment_share_pct':round(100*count/n,2) if n>=min_sample else None,
            'likes_received':likes[label] if stance_complete else None,
            'observed_likes_received':likes[label] if known else None,
            'likes_observed_comments':known,'likes_unknown_comments':cov['unknown'],'likes_invalid_comments':cov['invalid'],
            'likes_coverage_pct':round(100*known/count,2),
            'share_of_sample_likes_pct':round(100*likes[label]/total_observed_likes,2) if like_share_status=='display_sample_only' else None})
    return {'schema_version':'2.0','minimum_sample_for_display':min_sample,
        'percentage_status':'display_sample_only' if n>=min_sample else 'suppressed_insufficient_sample',
        'like_share_status':like_share_status,
        'likes_coverage':{'scope':'Included deduplicated comments only','status':coverage_status,'eligible_comments':n,'observed_comments':observed,'unknown_comments':coverage['unknown'],'invalid_comments':coverage['invalid'],'observed_comment_pct':round(100*observed/n,2) if n else None,'observed_likes_total':total_observed_likes if observed else None,'complete_sample_likes_total':total_observed_likes if complete else None},
        'scope':'Observed sampled comments only; not all viewers, users, or public opinion.',
        'received_rows':len(rows),'deduplicated_comments':len(unique),'deduplication':'first_occurrence_wins',
        'included_comments':n,'excluded_comments':len(unique)-n,
        'exclusion_reasons':dict(collections.Counter(r.get('exclusion_reason','unspecified') for r in unique if not r.get('primary_stance'))),
        'sampling_groups':dict(collections.Counter(r.get('sampling_group','unknown') for r in unique)),
        'stances':stances,
        'caveats':['One primary stance per included comment; explicitly annotated before aggregation.',
            'Missing, null, blank and invalid like counts are not observed zeros.',
            'Like-share percentages require complete valid like coverage across included comments; otherwise suppressed.',
            'Observed like subtotals with incomplete coverage are partial, not complete sample totals.',
            'Likes measure engagement with sampled comments, not unique people or agreement.',
            'Hot comments, replies and latest comments have different selection biases.',
            'No population confidence interval is claimed for a convenience sample.']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('output');parser.add_argument('--min-sample',type=int,default=20);args=parser.parse_args()
    if args.min_sample<1:parser.error('--min-sample must be positive')
    rows=json.loads(Path(args.input).read_text(encoding='utf-8'))
    Path(args.output).write_text(json.dumps(aggregate(rows,args.min_sample),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
