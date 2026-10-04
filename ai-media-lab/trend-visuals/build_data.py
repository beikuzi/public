import json,pathlib
root=pathlib.Path(__file__).parent
src=pathlib.Path('/workspace/shared/trend-observatory')
records=[]
for name in ['bili-xhs','weibo-douyin','wechat','x','douyin-official-snapshot','weibo-official-snapshot']:
 d=json.loads((src/'research'/f'{name}.json').read_text())
 for i,r in enumerate(d['records']):
  r={k:v for k,v in r.items() if k not in ['source_ref','raw_files']}
  r['id']=r.get('id',f'BX{i+1:02d}')
  r['platform']={'Bilibili':'bilibili','Xiaohongshu':'xiaohongshu','X':'x'}.get(r['platform'],r['platform'])
  r['background']=r['id']=='X03'
  r['excluded_from_metrics']=r['id'] in ['X03','X13']
  records.append(r)
payload={'snapshot':'2026-10-04','records':records}
s=src/'analysis'/'synthesis.json'
if s.exists():
 payload['synthesis']=json.loads(s.read_text())
 for group in payload['synthesis'].get('groups',[]):
  if group['id']=='review-cost':
   group['evidence_ids']=list(dict.fromkeys(group['evidence_ids']+['X14','X15']))
   group['limitations']=['小红书材料仍为二手；X08及两条回复已直接读取，但回复可见样本很少。','Karpathy相关转载可能同源，不能按独立支持证据叠加。']

(root/'dist'/'data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
manifest=json.loads((root/'.openai/hosting.json').read_text());manifest['static']={'directory':'dist'}
(root/'.openai/hosting.json').write_text(json.dumps(manifest,indent=2))
styles={'editorial':'白昼编辑室','transit':'轨道信号站','console':'夜航控制台','atlas':'纸片研究所'}
platforms={'summary':'跨平台综述','bilibili':'Bilibili','xiaohongshu':'小红书','weibo':'微博','douyin':'抖音','x':'X','wechat':'微信公众号'}
for st,sn in styles.items():
 for p,pn in platforms.items():
  path=root/'dist'/st/p;path.mkdir(parents=True,exist_ok=True)
  title=sn+' · '+pn+'｜澄镜'
  html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'''+title+'''</title><meta name="description" content="六平台公开讨论样本与可追溯观点证据，含微博与抖音官方榜单次快照。非全量舆情统计。"><meta name="theme-color" content="#f4f1ea"><link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/app.css"><script src="/app.js" defer></script></head><body data-style="'''+st+'" data-platform="'+p+'''"><a class="skip" href="#main">跳转至内容</a><div id="app"><p class="loading">正在载入公开证据…</p></div><dialog id="evidence"></dialog><dialog id="compare"></dialog><div id="toast" role="status"></div></body></html>'''
  (path/'index.html').write_text(html)
print(str(len(records))+' evidence records, 28 workspace routes generated')
