#!/usr/bin/env python3
"""Original-asset / source-parameter reconstruction, NOT engine capture.
No replacement art or UI; inert AST JSON input only; never executes game code.
"""
import json,math,random,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
B=Path(__file__).resolve().parents[1]; A=B/'assets';OUT=B/'deliverables';OUT.mkdir(exist_ok=True)
W,H,FPS,DUR=800,600,24,90
I={p.relative_to(A).as_posix():Image.open(p).convert('RGBA') for p in A.rglob('*') if p.suffix in ['.jpg','.png']}
F=ImageFont.truetype(str(A/'font/wqy-microhei.ttc'),22)
scene=json.loads((B/'inspection/script-a1-sunday-ZHS.rpyc.json').read_text())
texts={n['linenumber']:n['what'] for n in scene if n['class']=='Say'}
# Seven brief excerpts in ascending source order. Omitted lines are cuts.
EVENTS=[(0,9,2103),(11,20,2147),(20,26,2151),(28,44,2165),(44,49,2173),(55,68,2196),(73,86,2247)]
def ease(v):return .5-.5*math.cos(math.pi*max(0,min(1,v)))
def opacity(im,a):
 out=im.copy();out.putalpha(im.getchannel('A').point(lambda v:int(v*max(0,min(1,a)))));return out

def paste(dst,im,x=0,y=0,scale=1,alpha=1):
 if isinstance(im,str):im=I[im]
 if scale!=1:im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.BILINEAR)
 if alpha!=1:im=opacity(im,alpha)
 dst.alpha_composite(im,(int(x),int(y)))

def night(im):
 a=np.array(im).astype(float);rgb=a[:,:,:3];lum=rgb@np.array([.2126,.7152,.0722]);rgb=(.6*rgb+.4*lum[:,:,None])*np.array([.6,.6,.7]);a[:,:,:3]=np.clip(rgb,0,255);return Image.fromarray(a.astype('uint8'))
S1=night(I['sprites/shizu/close/shizu_behind_frustrated_close.png']);S2=night(I['sprites/shizu/close/shizu_out_serious_close.png'])
EPIC=Image.new('RGBA',(874,836));paste(EPIC,S2);paste(EPIC,night(I['vfx/shizu_out_serious_legs.png']),2,600)
SIL=Image.new('RGBA',EPIC.size,(0,0,0));SIL.putalpha(EPIC.getchannel('A'))
# Reproduce the original probabilistic fireworks states, using a fixed seed for reproducibility.
rng=random.Random(20261005);FW=[]
for i in range(1,10):
 cur=0;ev=[]
 while cur<24:
  while rng.randrange(21)<20:cur+=.1
  sparkle=bool(rng.randrange(2));ev.append((cur,sparkle));cur+=6.2
 FW.append(ev)
noise=np.tile(np.asarray(I['vfx/tr-pronoise.png'].convert('L')), (10,13))[:600,:800]/255.
def fireworks(dst,t):
 for idx,events in enumerate(FW,1):
  for start,spark in events:
   p=t-start
   if p<0 or p>=6.2:continue
   if p<.1:
    paste(dst,Image.new('RGBA',(800,600),(255,255,255,102)),alpha=min(1,p/.04))
   elif p<.2:
    q=(p-.1)/.04;paste(dst,Image.new('RGBA',(800,600),(255,255,255,102)),alpha=1-min(1,q));paste(dst,f'vfx/fw{idx}.png',alpha=min(1,q))
   else:
    q=max(0,min(1,(p-.2)/3))
    if not spark:paste(dst,f'vfx/fw{idx}.png',alpha=1-q)
    else:
     fw=I[f'vfx/fw{idx}.png'].copy();al=np.asarray(fw.getchannel('A')).astype(float);mask=1-np.clip((np.rint(noise*255)+int(288*q)-256)/32,0,1)
     fw.putalpha(Image.fromarray((al*mask).astype('uint8')));paste(dst,fw)

def scenery(t):
 dst=Image.new('RGBA',(800,600),(0,0,0,255))
 # Source line 2041 Fullpan already elapsed by line 2103. Right endpoint, no custom crop.
 paste(dst,'bgs/misc_sky_ni.jpg',-200,0)
 if 9<=t<11:paste(dst,S1,185,0,alpha=min(1,(t-9)/.5))
 elif 11<=t<26:
  paste(dst,S2,-37,0)
  if t<11.5:dst=Image.blend(scenery(10.99),dst,(t-11)/.5)
 elif t>=26:
  q=ease((t-26)/2);scale=1.5-.5*q
  city=I['vfx/cityscape.png'];paste(dst,city,-200*(1-q),600-city.height*scale*q,scale)
  dark=0 if t<50 else (min(1,(t-50)/5) if t<68 else max(0,1-(t-68)/5))
  if dark:paste(dst,Image.new('RGBA',(800,600),(0,0,0,204)),alpha=dark)
  if 50<=t<73:
   fwlayer=Image.new('RGBA',(800,600));fireworks(fwlayer,t-50);paste(dst,fwlayer,alpha=1 if t<68 else 1-(t-68)/5)
  hill='vfx/hillouette.png' if t<49 else 'vfx/hillpair1.png'
  paste(dst,hill,0,600-210*q)
  if 49<=t<49.5:
   old=Image.new('RGBA',(800,600));paste(old,'vfx/hillouette.png',0,390);paste(dst,old,alpha=1-(t-49)/.5)
  if t>=68:paste(dst,'vfx/hillpair2.png',0,390,alpha=min(1,(t-68)/5))
  if t<49:
   scale=1-.9*q;ep=Image.blend(EPIC,SIL,max(0,min(1,(t-26-.2)/1.8)));paste(dst,ep,400-874*scale/2,600*(.695+.04*q)-836*scale/2,scale)
 return dst

def wrap(text,width=742):
 out=[];s=''
 for c in text:
  if F.getlength(s+c)>width and s:out.append(s);s=c
  else:s+=c
 if s:out.append(s)
 return out

def ui(dst,t,start,line):
 paste(dst,'ui/bg-say.png',0,440)
 draw=ImageDraw.Draw(dst)
 if line==2173:
  draw.text((14,450),'久夫',font=F,fill='#629276');draw.text((15,450),'久夫',font=F,fill='#629276')
 txt=texts[line];txt=('“'+txt+'”') if line==2173 else txt
 n=min(len(txt),max(0,int((t-start)*70)))
 # Original vbox = name line 27 px + 15 px spacing; dialogue x=14+14 indent.
 yy=492
 for row in wrap(txt):
  shown=row[:n];n=max(0,n-len(row));draw.text((28,yy),shown,font=F,fill='white');yy+=27
 if t-start>=len(txt)/70:
  k=int((t-start-len(txt)/70)/.03)%64;ctc=I['ui/ctc_strip.png'].crop(((k%8)*16,(k//8)*16,(k%8+1)*16,(k//8+1)*16));paste(dst,ctc,772,560)
 return dst

def frame(t):
 dst=scenery(min(t,85.99))
 for start,end,line in EVENTS:
  if start<=t<end:ui(dst,t,start,line);break
 if 9<=t<11:paste(dst,'ui/bg-say.png',0,440)
 if 26<=t<28:ui(dst,t,20,2151)
 if 49<=t<50:ui(dst,t,44,2173)
 if t>=86:
  dst=Image.new('RGBA',(800,600),(15,17,22,255));d=ImageDraw.Draw(dst)
  for y,s,size in [(100,'片轮少女 · 第一章 v5',30),(166,'原素材／原UI参数重构 · 非实机录屏',22),(218,'原作：Four Leaf Studios',22),(261,'中文：arroz / janz / echo / leon 等',20),(304,'音乐：Blue123 / Nicol Armarfi',20),(365,'非官方、非商业节选 · 完整署名见随附文件',19),(415,'katawa-shoujo.com/download',20)]:
   f=ImageFont.truetype(str(A/'font/wqy-microhei.ttc'),size);d.text(((800-f.getlength(s))/2,y),s,font=f,fill='white')
 canvas=Image.new('RGB',(1280,720),'black');canvas.paste(dst.convert('RGB').resize((960,720),Image.Resampling.LANCZOS),(160,0));return canvas
if __name__=='__main__':
 if '--stills' in sys.argv:
  times=[4,10,14,23,27,32,46,60,78];ims=[]
  for t in times:
   im=frame(t);im.save(OUT/f'frame-{t:02d}.jpg',quality=94);ims.append(im)
  sheet=Image.new('RGB',(1280,3*265),(18,20,24));d=ImageDraw.Draw(sheet)
  for j,(t,im) in enumerate(zip(times,ims)):
   x=(j%3)*426;y=(j//3)*265;sheet.paste(im.resize((426,240)),(x,y));d.text((x+8,y+242),f'{t:02d}s | original assets / source parameters',fill='white')
  sheet.save(OUT/'contact-sheet.jpg',quality=95)
 else:
  p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','-','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(OUT/'silent.mp4')],stdin=subprocess.PIPE)
  for i in range(FPS*DUR):
   p.stdin.write(frame(i/FPS).tobytes())
   if i%(FPS*10)==0:print(i/FPS,flush=True)
  p.stdin.close();assert p.wait()==0
  # Source order: Aria starts before the selected arm gesture; fade music out at fireworks; return afterward.
  filt='[1:a]atrim=0:77,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=2,afade=t=out:st=36:d=5,volume=0.8,adelay=9000|9000[m1];[1:a]atrim=0:22,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=5,afade=t=out:st=19:d=3,volume=0.8,adelay=68000|68000[m2];[2:a]atrim=0:23,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1,afade=t=out:st=18:d=5,adelay=50000|50000[f];[m1][m2][f]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[a]'
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'silent.mp4'),'-stream_loop','-1','-i',str(A/'bgm/Aria.ogg'),'-stream_loop','-1','-i',str(A/'sfx/fireworks.ogg'),'-filter_complex',filt,'-map','0:v','-map','[a]','-t','90','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT/'galgame-original-visuals-route-A.mp4')],check=True)
