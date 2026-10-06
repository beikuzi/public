import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from safe_renpy import *
base=Path(__file__).resolve().parents[1];game=base/'local-game/Katawa Shoujo Act 1 v5-linux-x86/game'
a=RPA3(game/'data.rpa')
(base/'inspection/assets.txt').write_text('\n'.join(a.members))
for p in game.rglob('*.rpyc'):
 if p.parent != game and p.parent.name!='ZHS':continue
 try:
  _,nodes=safe_pickle(bounded_zlib(p.read_bytes(),allow_digest=True),inert_ast=True)
  def simple(x):
   if isinstance(x,InertNode):return {'class':x.symbol.name,'line':x.state.get('linenumber')}
   if isinstance(x,tuple):return [simple(v) for v in x]
   if isinstance(x,list):return [simple(v) for v in x]
   if isinstance(x,dict):return {k:simple(v) for k,v in x.items()}
   if isinstance(x,bytes):return repr(x)
   return x
  out=[{'class':n.symbol.name,**simple(n.state)} for n in nodes]
  (base/'inspection'/(p.name+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
 except Exception as e:print(p.name,e)
