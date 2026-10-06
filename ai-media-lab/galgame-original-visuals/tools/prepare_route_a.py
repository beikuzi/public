#!/usr/bin/env python3
"""Materialize the exact original assets locally. Does not execute game code."""
from pathlib import Path
from safe_renpy import RPA3
B=Path(__file__).resolve().parents[1]
A=RPA3(B/'local-game/Katawa Shoujo Act 1 v5-linux-x86/game/data.rpa')
names=['ui/bg-say.png','ui/ctc_strip.png','font/wqy-microhei.ttc','font/playtime.ttf','vfx/shizu_out_serious_legs.png','bgs/misc_sky_ni.jpg','vfx/cityscape.png','vfx/hillouette.png','vfx/hillpair1.png','vfx/hillpair2.png','vfx/tr-pronoise.png','sprites/shizu/close/shizu_behind_frustrated_close.png','sprites/shizu/close/shizu_out_serious_close.png','sfx/fireworks.ogg','bgm/Aria.ogg']+['vfx/fw%d.png'%n for n in range(1,10)]
(B/'inspection').mkdir(exist_ok=True)
for name in names:
 p=B/'assets'/name
 if p.exists():
  if p.is_symlink() or p.read_bytes()!=A.read(name):raise ValueError('existing asset differs: '+name)
 else:A.extract([name],B/'assets')
import inspect_original
print('Original resources and inert source inspection prepared.')
