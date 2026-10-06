#!/usr/bin/env python3
"""Private, non-executing Ren'Py legacy corpus inventory. No universal support claim."""
import argparse, collections, hashlib, importlib.util, json, pathlib, re, sys
PARSER=next(p for p in (pathlib.Path(__file__).resolve().parents[1]/'galgame-original-visuals/tools/safe_renpy.py', pathlib.Path(__file__).resolve().parents[2]/'galgame-original-visuals/tools/safe_renpy.py') if p.is_file())
spec=importlib.util.spec_from_file_location('safe_renpy',PARSER); safe=importlib.util.module_from_spec(spec);sys.modules[spec.name]=safe;spec.loader.exec_module(safe)
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('game');p.add_argument('output');p.add_argument('--edition',required=True);p.add_argument('--distribution-sha256',required=True);p.add_argument('--scope',choices=['demo','full'],required=True);a=p.parse_args()
 game=pathlib.Path(a.game);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
 sources=[]; assets=[]; errors=[]
 for path in sorted(game.rglob('*')):
  if not path.is_file() or path.is_symlink():continue
  name=str(path.relative_to(game))
  if path.suffix=='.rpyc': sources.append((name,path.read_bytes()))
  elif path.suffix=='.rpa':
   try:
    ar=safe.RPA3(path)
    for member in sorted(ar.members):
     assets.append({'archive':name,'member':member,'size':sum(s.length for s in ar.members[member])})
     if member.endswith('.rpyc'):sources.append((name+'!'+member,ar.read(member)))
   except Exception as e:errors.append({'source':name,'stage':'archive','error':str(e)})
  else:assets.append({'archive':None,'member':name,'size':path.stat().st_size})
 records=[]; file_reports=[]; speakers=collections.Counter();labels=[];counts=collections.Counter()
 for source,data in sources:
  h=sha(data)
  try:
   root,nodes=safe.safe_pickle(safe.bounded_zlib(data,allow_digest=True),inert_ast=True)
   if type(root)!=tuple or len(root)!=2 or type(root[1])!=list:raise safe.UnsafeData('unsupported script root')
   ancestry={};seen=set()
   def walk(obj,label=None,branch=()):
    if type(obj)==safe.InertNode:
     if id(obj) in seen:return
     seen.add(id(obj)); s=obj.state;kind=obj.symbol.name
     if kind=='Label':label=s.get('name')
     ancestry[obj.ordinal]=(label,branch)
     if kind=='If':
      for i,entry in enumerate(s.get('entries',[])):
       if len(entry)==2:walk(entry[1],label,branch+('if:'+str(i)+':'+str(entry[0]),))
     elif kind=='Menu':
      for i,entry in enumerate(s.get('items',[])):
       if len(entry)>=3:walk(entry[2],label,branch+('menu:'+str(i),))
     for k in ('block',):
      if k in s:walk(s[k],label,branch)
    elif type(obj) in (list,tuple):
     for v in obj:walk(v,label,branch)
   walk(root[1]); nc=collections.Counter(n.symbol.name for n in nodes)
   for n in nodes:
    s=n.state;kind=n.symbol.name;label,branch=ancestry.get(n.ordinal,(None,()))
    loc=sha((a.distribution_sha256+'\0'+source+'\0'+str(n.ordinal)).encode())[:24]
    r={'location_id':loc,'source':source,'source_sha256':h,'ordinal':n.ordinal,'kind':kind,'line':safe.simple(s.get('linenumber')),'label':safe.simple(label),'branch_path':list(branch)}
    for k in ('who','what','imspec','imgname','target','expression','expr','line','condition'):
     if k in s:r[k]=safe.simple(s[k])
    if kind=='Label':r['name']=safe.simple(s.get('name'));labels.append({'name':r['name'],'location_id':loc,'source':source})
    if kind=='Say':speakers[str(s.get('who'))]+=1
    if kind=='Menu':r['choices']=[{'text':safe.simple(i[0]),'condition':safe.simple(i[1]),'has_block':i[2] is not None} for i in s.get('items',[]) if len(i)>=3]
    if kind=='If':r['conditions']=[safe.simple(i[0]) for i in s.get('entries',[]) if len(i)==2]
    if kind in ('Python','EarlyPython','PyCode'):r['opaque_code']=True
    records.append(r);counts[kind]+=1
   file_reports.append({'source':source,'sha256':h,'status':'parsed','nodes':len(nodes),'structurally_reached_nodes':len(ancestry),'node_counts':dict(nc),'language_hint':re.search(r'(?:^|[/!])([A-Z]{2,3})/',source).group(1) if re.search(r'(?:^|[/!])([A-Z]{2,3})/',source) else 'base/unknown'})
  except Exception as e:errors.append({'source':source,'stage':'script','error':str(e)});file_reports.append({'source':source,'sha256':h,'status':'unsupported','error':str(e)})
 report={'edition':a.edition,'scope':a.scope,'distribution_sha256':a.distribution_sha256,'parser_sha256':sha(PARSER.read_bytes()),'pipeline_sha256':sha(pathlib.Path(__file__).read_bytes()),'gate':'partial' if errors or a.scope!='full' else 'static_extraction_complete_runtime_semantics_unverified','script_files_found':len(sources),'script_files_parsed':sum(r['status']=='parsed' for r in file_reports),'assets_indexed':len(assets),'record_counts':dict(counts),'speaker_identifiers':dict(speakers),'errors':errors,'limitations':['Demo scope is never whole-game coverage.','All script files parsed does not prove all runtime-generated dialogue is recovered.','Python and dynamic expressions remain inert; branch predicates are not executed.','Symbolic image names are not automatically resolved to file assets.','File/language hints are not a translation completeness guarantee.','No route execution, save compatibility, or screenshot equivalence is established.']}
 for name,obj in [('coverage.json',report),('files.json',file_reports),('assets.json',assets),('labels.json',labels)]: (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 with (out/'corpus.jsonl').open('w') as f:
  for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
