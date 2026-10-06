#!/usr/bin/env python3
"""Version-pinned source-line inventory for vendor The Question 8.5.3 only."""
import pathlib, hashlib, json, re
BASE=pathlib.Path(__file__).resolve().parents[1]
GAME=BASE/'vendor/renpy-8.5.3-sdk/the_question/game'
OUT=BASE/'private/the-question-8.5.3';OUT.mkdir(parents=True,exist_ok=True)
DIST='eb0a9be7f0fb13632fe25ceade9a8bed5a1b4d6b6e83bd19eeeb29e1a1bb4a45'
def sha(b):return hashlib.sha256(b).hexdigest()
files=[];records=[];labels=[];commands=[];assets=[]
for p in sorted(GAME.rglob('*')):
 if not p.is_file():continue
 name=p.relative_to(GAME).as_posix();data=p.read_bytes()
 if p.suffix=='.rpy':
  text=data.decode('utf-8-sig'); lines=text.splitlines();files.append({'path':name,'sha256':sha(data),'bytes':len(data),'lines':len(lines),'status':'full_source_preserved'})
  label=None
  for n,line in enumerate(lines,1):
   loc=sha((DIST+'\0'+name+'\0'+str(n)).encode())[:24]
   if re.match(r'^label \w+:',line):label=line.split()[1][:-1];labels.append({'source':name,'line':n,'name':label,'location_id':loc})
   row={'location_id':loc,'source':name,'line':n,'label':label,'raw':line};records.append(row)
   if name=='script.rpy' and re.match(r'\s*(scene|show|hide|with|jump|menu|if|return|play)\b',line):commands.append(row)
 else:assets.append({'path':name,'sha256':sha(data),'bytes':len(data)})
compiled={p.relative_to(GAME).with_suffix('.rpy').as_posix() for p in GAME.rglob('*.rpyc')};source={f['path'] for f in files};missing=sorted(compiled-source)
script=GAME/'script.rpy'; lines=script.read_text(encoding='utf-8-sig').splitlines()
target=next(r for r in records if r['source']=='script.rpy' and r['raw'].strip()=='s "Will you marry me?"')
branch={'start':{'choice_0':'rightaway','choice_1':'later'},'rightaway':{'choice_0':'game','choice_1':'book'},'game':{'jump':'marry','book':False},'book':{'jump':'marry','book':True},'marry':{'conditional_extra_line':'book == True','terminal':'good ending'},'later':{'terminal':'bad ending'}}
scene={'edition':'The Question bundled with RenPy 8.5.3','language':'English/base','distribution_sha256':DIST,'source_sha256':sha(script.read_bytes()),'location_id':target['location_id'],'label':'marry','line':target['line'],'short_excerpt':'Will you marry me?','choice_path':['To ask her right away.',"It's a videogame."],'state':{'book':False},'expected_visuals':{'background':'images/bg club.jpg','sprite':'images/sylvie blue giggle.png','speaker':'Sylvie','transition':'dissolve completed','window':'ADV dialogue'},'asset_sha256':{a['path']:a['sha256'] for a in assets if a['path'] in ['images/bg club.jpg','images/sylvie blue giggle.png']},'runtime_frame_verified':False}
report={'edition':scene['edition'],'scope':'complete short example visual novel, not commercial-length title','distribution_sha256':DIST,'download_bytes':153611590,'official_checksum_match':True,'gate':'available_source_complete_scene_mapped','source_files':len(files),'source_lines_preserved':len(records),'compiled_without_source':missing,'english_story_files':1,'english_story_lines':len(lines),'english_labels':[r['name'] for r in labels if r['source']=='script.rpy'],'translations':sorted(p.name for p in (GAME/'tl').iterdir() if p.is_dir() and p.name!='None'),'script_assets':len(assets),'limitations':['100% means all supplied source files preserved, not all paths executed or translations linguistically verified.','Only the small English baseline story branch graph is manually verified.','Line index is not a universal RenPy parser.','No screenshot or save compatibility result is implied.']}
assert not missing
# Typed English dialogue/choice index for this simple single-line source only.
story=[]
for r in records:
 if r['source']!='script.rpy': continue
 stripped=r['raw'].strip()
 if stripped.startswith('#'): continue
 m=re.fullmatch(r'(?:(s|m) )?("(?:[^"\\]|\\.)*")(:)?',stripped)
 if m: story.append({**r,'kind':'choice' if m[3] else 'dialogue','speaker_identifier':m[1],'text_literal':m[2]})
(OUT/'story-index.json').write_text(json.dumps(story,ensure_ascii=False,indent=2))
(OUT/'characters.json').write_text(json.dumps({'s':'Sylvie','m':'Me','null':'narrator'},indent=2))
for name,obj in [('coverage.json',report),('source-files.json',files),('assets.json',assets),('labels.json',labels),('commands.json',commands),('branch-map.json',branch),('scene-contract.json',scene)]: (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
with (OUT/'source-lines.jsonl').open('w') as f:
 for row in records:f.write(json.dumps(row,ensure_ascii=False)+'\n')
(BASE/'reports/the-question-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(BASE/'reports/the-question-scene-contract.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2));print(json.dumps(scene,indent=2))
