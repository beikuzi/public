#!/usr/bin/env python3
"""Asset-local, noncommercial fan clip. Never bundles game assets or full dialogue.
Loads seven exact strings from a local official demo, parsed without execution.
Pillow/FFmpeg output; timing and composites are editorial reconstructions.
"""
import argparse,json,math,pickletools,subprocess,zlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageEnhance,ImageFilter
from safe_renpy import RPA3,bounded_zlib
W,H,FPS,DURATION=1280,720,24,90
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F=lambda n,b=False:ImageFont.truetype(BOLD if b else FONT,n)
STRING_OPS={'BINUNICODE','SHORT_BINUNICODE','UNICODE','STRING','BINSTRING','SHORT_BINSTRING'}
IDS=[1469,1492,1493,1504,1506,1522,1540]
ASSETS=['bgs/misc_sky_ni.jpg','bgs/school_roof_ni.jpg','vfx/cityscape.png','vfx/hillouette.png','vfx/hillpair1.png','vfx/hillpair2.png','sprites/shizu/close/shizu_behind_frustrated_close.png','sprites/shizu/close/shizu_out_serious_close.png','sfx/fireworks.ogg']+['vfx/fw%d.png'%i for i in range(1,10)]
def ease(x):return (1-math.cos(math.pi*max(0,min(1,x))))/2

def wrap(s,font,width):
 lines=[];row=''
 for c in s:
  if font.getlength(row+c)>width and row:lines.append(row);row=c
  else:row+=c
 if row:lines.append(row)
 return lines

def main():
 global FONT,BOLD
 ap=argparse.ArgumentParser();ap.add_argument('--game',required=True,type=Path);ap.add_argument('--work',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--stills',action='store_true');ap.add_argument('--music',default='bgm/Aria.ogg');ap.add_argument('--font',default=FONT);ap.add_argument('--bold-font',default=BOLD);args=ap.parse_args();FONT=args.font;BOLD=args.bold_font
 game=args.game;assets=args.work/'assets';assets.mkdir(parents=True,exist_ok=True);args.output.parent.mkdir(parents=True,exist_ok=True)
 archive=RPA3(game/'data.rpa')
 for name in ASSETS+[args.music]:
  existing=assets/name
  if existing.exists():
   if existing.is_symlink() or existing.read_bytes()!=archive.read(name):raise ValueError('existing asset does not match official archive: '+name)
  else:archive.extract([name],assets)
 raw=(game/'ZHS/script-a1-sunday-ZHS.rpyc').read_bytes();ss=[a for op,a,pos in pickletools.genops(bounded_zlib(raw,allow_digest=True)) if op.name in STRING_OPS]
 text=[ss[i] for i in IDS]
 images={n:Image.open(assets/n).convert('RGBA') for n in ASSETS if n.endswith(('.png','.jpg'))}
 for key in list(images):
  if key.startswith('sprites/'):
   rr,gg,bb,aa=images[key].split();images[key]=Image.merge('RGBA',(rr.point(lambda x:int(x*.74)),gg.point(lambda x:int(x*.80)),bb.point(lambda x:int(x*.97)),aa))
 white=(244,243,238);gold=(225,200,147)
 def bg(name,t,zoom=.025):
  im=images[name];s=max(W/im.width,H/im.height)*(1+zoom*t);im=im.resize((int(im.width*s),int(im.height*s)),Image.Resampling.LANCZOS);x=(im.width-W)//2;y=(im.height-H)//2;return im.crop((x,y,x+W,y+H))
 def paste(im,key,x,y,scale=1,alpha=1):
  a=images[key];a=a.resize((int(a.width*scale),int(a.height*scale)),Image.Resampling.LANCZOS)
  if alpha<1:a.putalpha(a.getchannel('A').point(lambda v:int(v*max(0,alpha))))
  im.alpha_composite(a,(int(x),int(y)))
 def panorama(t,fireworks=False,pair=1):
  im=bg('bgs/misc_sky_ni.jpg',t,.015)
  paste(im,'vfx/cityscape.png',-10,427,1.46)
  if fireworks:
   for j in range(5):
    phase=(t*1.17+j*1.71)%5.8
    if phase<3.5:
     n=1+int((t//5.8+j*2)%9);key=f'vfx/fw{n}.png';a=images[key]
     scale=1.35*(.90+.10*ease(phase/.7));opacity=min(1,phase/.3)*max(0,1-(phase-1.5)/2)
     paste(im,key,-40+j*13,-85+j*11,scale,opacity*.85)
  paste(im,f'vfx/hillpair{pair}.png',0,411,1.6)
  return im
 def scene(t):
  if t<14:
   im=bg('bgs/school_roof_ni.jpg',t/14,.035)
   paste(im,'sprites/shizu/close/shizu_behind_frustrated_close.png',715,50,1.02,.95)
  elif t<25:
   im=bg('bgs/misc_sky_ni.jpg',(t-14)/11,.025)
   paste(im,'sprites/shizu/close/shizu_out_serious_close.png',160,40,1.1,.95)
  else:im=panorama((t-25),46<=t<68,1 if t<63 else 2)
  return im
 def centered(d,y,s,size,color=white,bold=False):
  font=F(size,bold);d.text(((W-font.getlength(s))/2,y),s,font=font,fill=color)
 def frame(t):
  im=scene(t)
  # Brief soft crossfade makes each scene change intentional.
  for cut in [14,25,46,68]:
   if cut<=t<cut+.8:im=Image.blend(scene(cut-.001),im,ease((t-cut)/.8))
  d=ImageDraw.Draw(im)
  # Persistent honest identity, distinct from the original game's UI.
  d.rounded_rectangle((32,24,480,62),radius=8,fill=(8,14,25,170))
  d.text((45,31),'KATAWA SHOUJO · ACT 1  /  非官方节选重构',font=F(17),fill=white)
  if t<5:
   veil=Image.new('RGBA',(W,H),(4,9,19,150));im=Image.alpha_composite(im,veil);d=ImageDraw.Draw(im)
   centered(d,218,'抬头，看见此刻',60,gold,True)
   centered(d,302,'一个没有说出口的鼓励',26)
   centered(d,378,'祭典之夜，他仍被内疚与忧郁困住。',23)
   centered(d,416,'静音伸出双臂，邀他看看眼前的世界。',23)
   centered(d,620,'原作简体中文 · 片段经删节 · 代码重构演出，非实机录像',18,(180,187,200))
  elif t<72:
   ranges=[(5,14,0),(14,21,1),(21,25,2),(25,41,3),(41,46,4),(46,58,5),(58,72,6)]
   start,end,idx=next(v for v in ranges if v[0]<=t<v[1]);content=text[idx]
   # Reveal by character; leave most of each shot for comfortable reading.
   reveal=min(len(content),int(max(0,t-start-.2)*22)+1);shown=content[:reveal]
   box=Image.new('RGBA',(W,H));bd=ImageDraw.Draw(box)
   bd.rounded_rectangle((44,505,1236,680),radius=12,fill=(5,13,26,224),outline=(165,154,125,150),width=1)
   bd.rectangle((44,519,48,657),fill=gold)
   bd.text((70,523),'久夫 · '+('对白' if idx==4 else '内心旁白'),font=F(20,True),fill=gold)
   for j,line in enumerate(wrap(shown,F(29),1100)):
    bd.text((70,562+j*43),line,font=F(29),fill=white)
   opacity=ease(min((t-start)/.25,(end-t)/.25));box.putalpha(box.getchannel('A').point(lambda x:int(x*opacity)));im=Image.alpha_composite(im,box);d=ImageDraw.Draw(im)
   d.text((W-152,691),f'{idx+1:02d} / 07  节选',font=F(15),fill=(170,178,194))
  elif t<80:
   im=Image.alpha_composite(im,Image.new('RGBA',(W,H),(2,8,19,140)));d=ImageDraw.Draw(im)
   centered(d,245,'片段读后',20,gold)
   centered(d,302,'有些鼓励没有答案，',39,white,True)
   centered(d,365,'只是把我们的目光带回世界。',39,white,True)
   centered(d,450,'以上为编者感想，不是原作台词。',18,(183,190,205))
  else:
   im=Image.alpha_composite(im,Image.new('RGBA',(W,H),(2,8,19,216)));d=ImageDraw.Draw(im)
   centered(d,135,'KATAWA SHOUJO  /  片轮少女',37,gold,True)
   centered(d,197,'原作：Four Leaf Studios · 第一章 v5',23)
   centered(d,239,'BGM：Aria de l’etoile（原场景曲目）',21)
   centered(d,270,'原作音乐：Blue123 / Nicol Armarfi',18)
   centered(d,302,'中文翻译：arroz / janz / echo / leon 及中文本地化团队',21)
   centered(d,341,'完整原作与翻译署名，见随附 ORIGINAL_CREDITS.txt',19,(184,190,204))
   centered(d,392,'非官方、非商业粉丝短片 · 保留原作版权与署名',21)
   centered(d,429,'官方免费游戏：katawa-shoujo.com/download',20)
   centered(d,498,'由原作图像、音乐与 7 条原文，重新编排镜头与节奏。',19)
   centered(d,535,'并非原始实机录像；无配音；未使用生成式图像。',19)
  # A restrained progress line and cinematic fade-in/out.
  d=ImageDraw.Draw(im);d.rectangle((0,H-3,int(W*t/DURATION),H),fill=gold)
  fade=min(1,t/.8,(DURATION-t)/1.5)
  if fade<1:im=Image.blend(Image.new('RGBA',(W,H),(0,0,0,255)),im,max(0,fade))
  return im.convert('RGB')
 if args.stills:
  for t in [2.5,10,20,31,42,49,59,68,76,84]:frame(t).save(args.work/f'frame_{t:g}.jpg',quality=93)
  return
 silent=args.work/'silent.mp4'
 command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(silent)]
 proc=subprocess.Popen(command,stdin=subprocess.PIPE)
 try:
  for i in range(DURATION*FPS):
   proc.stdin.write(frame(i/FPS).tobytes())
   if i%(FPS*10)==0:print('rendered',i/FPS,'s',flush=True)
 finally:proc.stdin.close()
 if proc.wait():raise RuntimeError('ffmpeg video encoding failed')
 audiofilter='[1:a]atrim=0:90,asetpts=PTS-STARTPTS,volume=1.24,afade=t=in:st=0:d=2,afade=t=out:st=85:d=5[m];[2:a]atrim=0:17,asetpts=PTS-STARTPTS,volume=0.50,afade=t=in:st=0:d=1,afade=t=out:st=14:d=3,adelay=46000|46000[f];[m][f]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]'
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),'-stream_loop','-1','-i',str(assets/args.music),'-i',str(assets/'sfx/fireworks.ogg'),'-filter_complex',audiofilter,'-map','0:v','-map','[a]','-t','90','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(args.output)],check=True)
 print('completed',args.output,flush=True)
if __name__=='__main__':main()
