#!/usr/bin/env python3
"""Route A: original assets/GUI parameters; Pillow recomposition, not gameplay."""
from pathlib import Path
import argparse,ast,re,json,hashlib,subprocess
from PIL import Image,ImageDraw,ImageFont
B=Path(__file__).resolve().parents[1];SDK=B.parent/'galgame-text-pipeline/vendor/renpy-8.5.3-sdk';G=SDK/'the_question/game';O=B/'deliverables';O.mkdir(exist_ok=True)
SRC=(G/'script.rpy').read_text(encoding='utf-8-sig').splitlines()
assert hashlib.sha256((G/'script.rpy').read_bytes()).hexdigest()=='733633c0d33804e2cc728632c308370e993dc1e13d754f4383b42effa8576d19'
FONT=SDK/'renpy/common/DejaVuSans.ttf'
font=lambda size:ImageFont.truetype(str(FONT),size)
F=font(22);NF=font(30);QF=font(14)
I={n:Image.open(G/n).convert('RGBA') for n in ['images/bg club.jpg','images/sylvie blue normal.png','images/sylvie blue giggle.png','gui/textbox.png','gui/namebox.png','gui/button/quick_idle_background.png']}
EVENTS=[(0,4,164),(4.5,10,169),(10,16,175),(16,18,177),(18.5,21,182),(21,23,184),(23,30,188),(30,32,190)]
def text_at(n):
 s=SRC[n-1].strip();m=re.match(r'(?:(s|m) )?(".*")$',s);assert m;return m[1],ast.literal_eval(m[2])
def composite(dst,n,x=0,y=0,a=1):
 im=I[n]
 if a!=1:im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*a)))
 dst.alpha_composite(im,(x,y))
def wrap(s):
 out=[];line=''
 for word in s.split(' '):
  cand=(line+' '+word).strip()
  if F.getlength(cand)>744:out.append(line);line=word
  else:line=cand
 if line:out.append(line)
 return out
def quick(dst):
 d=ImageDraw.Draw(dst);labels=['Back','History','Skip','Auto','Save','Q.Save','Q.Load','Prefs'];widths=[int(QF.getlength(s)+.999)+20 for s in labels];x=(1280-sum(widths))//2
 for s,w in zip(labels,widths):
  # 4 px top padding, zero bottom padding; original default button font and transparent background.
  
  if s in ['Skip','Q.Load']:
   layer=Image.new('RGBA',dst.size);ImageDraw.Draw(layer).text((x+10,703),s,font=QF,fill=(85,85,85,127),anchor='la');dst.alpha_composite(layer)
  else:d.text((x+10,703),s,font=QF,fill='#aaaaaa',anchor='la')
  x+=w

def ui(dst,line):
 composite(dst,'gui/textbox.png',0,535);d=ImageDraw.Draw(dst);who,txt=text_at(line)
 if who:
  name='Sylvie' if who=='s' else 'Me';color='#c8ffc8' if who=='s' else '#c8c8ff'
  # Original transparent namebox is 9-sliced to content, with 5 px borders.
  d.text((245,540),name,font=NF,fill=color,anchor='la')
 for j,row in enumerate(wrap(txt)):d.text((268,585+j*26),row,font=F,fill='white',anchor='la')
 quick(dst);return dst

def frame(t):
 im=Image.new('RGBA',(1280,720),(0,0,0,255))
 if t>=4:composite(im,'images/bg club.jpg',a=min(1,(t-4)/.5))
 if t>=18:composite(im,'images/sylvie blue normal.png' if t<23 else 'images/sylvie blue giggle.png',473,20,a=min(1,(t-18)/.5))
 for start,end,line in EVENTS:
  if start<=t<end:return ui(im,line).convert('RGB')
 # During dissolve, retain the prior line, as an editorial approximation; exact engine transitions differ.
 return ui(im,164 if t<4.5 else 177).convert('RGB')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--stills',action='store_true');a=ap.parse_args()
 if a.stills:
  times=[2,7,12,19,22,25];sheet=Image.new('RGB',(1280,780),(18,18,18));d=ImageDraw.Draw(sheet)
  for i,t in enumerate(times):
   im=frame(t);im.save(O/f'frame-{t:02}.png');x=(i%2)*640;y=(i//2)*260;sheet.paste(im.resize((640,360)).crop((0,0,640,240)),(x,y));d.text((x+10,y+242),f'{t}s | Route A source-parameter recomposition',fill='white')
  # Full aspect-ratio contact sheet, no cropped contents.
  sheet=Image.new('RGB',(1280,1140),(18,18,18));d=ImageDraw.Draw(sheet)
  for i,t in enumerate(times):
   x=(i%2)*640;y=(i//2)*380;sheet.paste(frame(t).resize((640,360)),(x,y));d.text((x+10,y+362),f'{t}s | Route A recomposition',fill='white')
  sheet.save(O/'contact-sheet.jpg',quality=94);frame(25).save(O/'target-frame.png')
 else:
  p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','-','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(O/'silent.mp4')],stdin=subprocess.PIPE)
  for i in range(32*24):p.stdin.write(frame(i/24).tobytes())
  p.stdin.close();assert p.wait()==0
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(O/'silent.mp4'),'-stream_loop','-1','-i',str(G/'illurock.opus'),'-map','0:v','-map','1:a','-t','32','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(O/'route-A-the-question.mp4')],check=True)
