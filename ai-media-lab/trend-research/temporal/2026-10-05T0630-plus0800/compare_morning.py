"""Compare saved typed public ranking samples; no network or data imputation.

Outputs JSON to stdout. Input captures are preserved. Rounded displayed metrics are
not exact underlying changes; absent rows are absent from the sample only.
"""
import argparse, datetime, json
from pathlib import Path

def number(value):
    if value is None:return None
    s=str(value).replace(' 热度','').strip()
    try:return float(s[:-1])*10000 if s.endswith('万') else float(s)
    except ValueError:return None

def compare(folder, baseline="baseline-records.json"):
    old=json.loads((folder/baseline).read_text())['records']
    result={'schemaVersion':1,'rankDeltaConvention':'current rank minus baseline rank; negative means rise','metricDeltaConvention':'current displayed numeric value minus prior displayed numeric value; rounded display arithmetic only','baselineProvenance':baseline,'comparisons':[]}
    for platform in ('bilibili','douyin','weibo'):
        current=json.loads((folder/f'{platform}-official-snapshot.json').read_text())
        previous=[r for r in old if r['platform']==platform];changes=[]
        for row in previous:
            matched=next((c for c in current['entries'] if c['title']==row['title']),None)
            metrics=row['observed_metrics'];rank=metrics.get('rank',metrics.get('category_rank'))
            now=matched['rank'] if matched else None
            item={'baselineId':row['id'],'title':row['title'],'oldRank':rank,'newRank':now,'rankDelta':now-rank if now is not None and rank is not None else None,'status':'matched' if matched else 'not_in_current_sample','oldCapturedAt':row['captured_at'],'newCapturedAt':current['capturedAt']}
            if matched:
                fields=[('views_display','viewsRaw'),('danmaku_display','danmakuRaw')] if platform=='bilibili' else [('heat_display','metricRaw')] if platform=='douyin' else [('displayed_heat','metricValue')]
                item['metrics']=[]
                for before,after in fields:
                    a,b=metrics.get(before),matched.get(after);an,bn=number(a),number(b)
                    item['metrics'].append({'name':before,'oldDisplay':a,'newDisplay':b,'displayNumericDelta':round(bn-an,4) if an is not None and bn is not None else None,'precision':'displayed rounded figures; not exact underlying change' if '万' in str(a)+str(b) else 'displayed integer'})
            changes.append(item)
        instant=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
        entry={'platform':platform,'scope':current['scope'],'elapsedSeconds':(instant(current['capturedAt'])-instant(previous[0]['captured_at'])).total_seconds(),'baselineSavedCount':len(previous),'currentSavedCount':len(current['entries']),'changes':changes,'cacheAssessment':'Changes observed; caching cannot be ruled out for individual values; no server freshness timestamp.'}
        if platform in ('bilibili','douyin'):
            before={r['title'] for r in previous if r['observed_metrics'].get('rank',99)<=10};after={r['title'] for r in current['entries'] if r['rank']<=10}
            entry.update(top10RetainedCount=len(before&after),newlyObservedInTop10=sorted(after-before),leftObservedTop10=sorted(before-after))
        else:
            entry['baselineCompletenessNote']='Initial baseline has only12 selected rows of30; no exhaustive initial-entry/new-entry claim.' if len(previous)<30 else 'Prior01:00 and current category30 both complete for this displayed scope; absence is not platform-wide disappearance.'
            if len(previous)==30:
                before={r['title'] for r in previous}; after={r['title'] for r in current['entries']}
                entry.update(category30RetainedCount=len(before&after),newlyObservedInCategory30=sorted(after-before),leftObservedCategory30=sorted(before-after))
        result['comparisons'].append(entry)
    return result

if __name__=='__main__':
    folder=Path(__file__).parent
    for baseline,output in [('baseline-records.json','comparison-initial.json'),('prior-0100-records.json','comparison-0100.json')]:
        result=compare(folder,baseline)
        (folder/output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
        for c in result['comparisons']: print(output,c['platform'],c['elapsedSeconds'],c.get('top10RetainedCount',c.get('category30RetainedCount')))
