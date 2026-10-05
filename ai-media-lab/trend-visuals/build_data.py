"""Deterministic local compilation. Verified versioned inputs only; no network or fallback."""
import argparse, hashlib, json, os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent

def read_verified(entry):
    path=(ROOT/entry['path']).resolve()
    if not path.is_relative_to(ROOT/'inputs'): raise ValueError('Input path must remain under inputs/')
    raw=path.read_bytes()  # Missing input fails before any output write.
    if hashlib.sha256(raw).hexdigest()!=entry['sha256']: raise ValueError('Input hash mismatch: '+entry['path'])
    return json.loads(raw)

def instant(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('Observation timestamps require timezone')
    return dt

def compile_data():
    manifest=json.loads((ROOT/'inputs/manifest.json').read_text())
    if manifest.get('schema_version')!=1: raise ValueError('Unsupported manifest schema')
    baseline=read_verified(manifest['baseline'])
    expected=manifest['expected_baseline'];records=baseline['records'];by_id={r['id']:r for r in records}
    if len(by_id)!=len(records) or len(records)!=expected['records']: raise ValueError('Baseline record count/IDs changed')
    if sum(not r.get('excluded_from_metrics') for r in records)!=expected['coverage_records']: raise ValueError('Baseline coverage changed')
    if len(baseline['synthesis']['groups'])!=expected['synthesis_groups']: raise ValueError('Baseline synthesis changed')
    payload=deepcopy(baseline);batches=[];latest=instant(baseline['metadata']['last_checked_at'])
    for entry in manifest['temporal_batches']:
        comparison=read_verified(entry['comparison']);snapshots=[read_verified(e) for e in entry['snapshots']]
        by_platform={s['platform']:s for s in snapshots}
        if len(by_platform)!=len(snapshots): raise ValueError('Duplicate platform snapshot')
        def validate_comparison(value, prior=None):
            nonlocal latest
            for c in value['comparisons']:
                current=by_platform[c['platform']]
                if len(current['entries'])!=c['currentSavedCount']: raise ValueError('Current saved count mismatch')
                latest=max(latest,instant(current['capturedAt']))
                for change in c['changes']:
                    if prior is None:
                        r=by_id[change['baselineId']]
                        if r['platform']!=c['platform']: raise ValueError('Platform mismatch')
                        old=r['observed_metrics'].get('rank',r['observed_metrics'].get('category_rank'))
                        prior_time=r['captured_at']
                    else:
                        old_snapshot=prior[c['platform']]
                        matches=[row for row in old_snapshot['entries'] if row.get('baselineRecordId')==change['baselineId'] or row['title']==change['title']]
                        if len(matches)!=1: raise ValueError('Prior observation match must be unique')
                        old=matches[0]['rank'];prior_time=old_snapshot['capturedAt']
                        if len(old_snapshot['entries'])!=c['baselineSavedCount']: raise ValueError('Prior saved count mismatch')
                    if old!=change['oldRank'] or instant(prior_time)!=instant(change['oldCapturedAt']): raise ValueError('Baseline rank/time mismatch')
                    if instant(change['newCapturedAt'])!=instant(current['capturedAt']): raise ValueError('Current timestamp mismatch')
                    if instant(change['newCapturedAt'])<=instant(change['oldCapturedAt']): raise ValueError('Observations not chronological')
                    if change['newRank'] is not None:
                        if change['rankDelta']!=change['newRank']-change['oldRank']: raise ValueError('Rank delta mismatch')
                        matches=[row for row in current['entries'] if row.get('baselineRecordId')==change['baselineId'] or row['title']==change['title']]
                        if len(matches)!=1 or matches[0]['rank']!=change['newRank']: raise ValueError('Unmatched current item/rank')
                    else:
                        if change.get('rankDelta') is not None or change.get('metrics'): raise ValueError('Absent item must have null rank delta and no invented metrics')
                        if any(row['title']==change['title'] for row in current['entries']): raise ValueError('Absent item exists in current entries')
        validate_comparison(comparison)
        previous_comparison=None
        if entry.get('previous_comparison'):
            previous=next((b for b in batches if b['id']==entry['previous_batch_id']),None)
            if previous is None: raise ValueError('Prior batch missing or not ordered')
            previous_comparison=read_verified(entry['previous_comparison'])
            validate_comparison(previous_comparison,{s['platform']:s for s in previous['snapshots']})
        additional_comparisons=[]
        for extra in entry.get('additional_comparisons',[]):
            prior=next((b for b in batches if b['id']==extra['baseline_batch_id']),None)
            if prior is None: raise ValueError('Additional comparison prior batch missing')
            extra_value=read_verified(extra['comparison'])
            validate_comparison(extra_value,{s['platform']:s for s in prior['snapshots']})
            additional_comparisons.append({'baseline_batch_id':extra['baseline_batch_id'],'comparison':extra_value})
        for value in [comparison,previous_comparison]+[v['comparison'] for v in additional_comparisons]:
            if value is not None:
                for c in value['comparisons']:
                    for change in c['changes']:
                        if change['newRank'] is None: change.setdefault('metrics',None)
        # Only bounded, collected evidence reaches the public payload, not browser/tool logs.
        clean_snapshots=[{k:s[k] for k in ['platform','sourceUrl','capturedAt','captureWindowStart','platformDataTimestamp','scope','rankingRuleDisplay','metricLabel','metricMeaning','entries','limitations','trackedAbsent','observedRankingRowCount','serverFreshness'] if k in s} for s in snapshots]
        batch={'id':entry['id'],'comparison':comparison,'snapshots':clean_snapshots}
        if previous_comparison is not None: batch.update(previous_comparison=previous_comparison,previous_batch_id=entry['previous_batch_id'])
        if additional_comparisons: batch['additional_comparisons']=additional_comparisons
        batches.append(batch)
    payload['metadata']['baseline_last_checked_at']=baseline['metadata']['last_checked_at']
    payload['metadata']['baseline_snapshot_date']=baseline['metadata']['snapshot_date']
    payload['metadata']['latest_observation_at']=latest.isoformat()
    payload['metadata']['last_checked_at']=latest.isoformat()
    payload['metadata']['updated_date']=latest.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    payload['temporal']={'schema_version':1,'initial_record_count':len(records),'initial_coverage_count':expected['coverage_records'],'baseline_provenance':manifest['baseline_provenance'],'batches':batches,'boundary':'后续榜单观察独立保存，不增加初始样本覆盖数；浏览器观察时间不等于服务器刷新时间，缓存新鲜度未知。'}
    if payload['records']!=baseline['records']: raise ValueError('Initial records must remain unchanged')
    return payload

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    payload=compile_data();encoded=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    if not args.check:
        target=ROOT/'dist/data.json';temporary=target.with_suffix('.json.tmp')
        temporary.write_text(encoded);os.replace(temporary,target)
    print(json.dumps({'validated':True,'written':not args.check,'initial_records':len(payload['records']),'temporal_batches':len(payload['temporal']['batches']),'latest_observation_at':payload['metadata']['latest_observation_at']}))
if __name__=='__main__':main()
