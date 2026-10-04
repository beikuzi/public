"""Freeze six visible-caption references; select preprocessing on frames1–2 only."""
import pathlib,json,time,subprocess,statistics
from PIL import Image,ImageOps
import numpy as np
from jiwer import cer
from pipeline import norm
root=pathlib.Path('outputs/ocr_improved');root.mkdir(exist_ok=True)
refs={1:'中国政府早就通过大外宣，把他们的文化意识、政治意识，一点一点输入到很多国家',2:'报刊杂志基本上都被各地的中国大使馆给收买了',3:'你很难看到中国按照官方的要求之外的报纸，几乎没有了',4:'在这么一个大环境下，我想不只是一个政治问题',5:'或者说经济是一个正面，还有一个反面',6:'这也是极权主义的通病，它不会局限在自己的社会，它总需要敌人，然后需要扩张，这是没办法的'}
(root/'references.json').write_text(json.dumps({'reference_kind':'assistant visual transcription checked on original848x480 frames; not human gold or speech transcript','development_frames':[1,2],'held_out_frames':[3,4,5,6],'text':refs},ensure_ascii=False,indent=2))

def prepare(i,kind):
 im=Image.open(root/f'originals/frame_{i:03d}.png').convert('RGB').crop((100,350,745,435))
 if kind=='gray':im=ImageOps.grayscale(im)
 if kind.startswith('white'):
  threshold=int(kind[5:]);v=np.array(im);im=Image.fromarray(np.where(v.min(axis=2)>threshold,0,255).astype('uint8'))
 return ImageOps.expand(im.resize((im.width*3,im.height*3)),border=20,fill='white')
def recognize(i,kind,psm):
 t=time.perf_counter();im=prepare(i,kind);path=root/f'{kind}_psm{psm}_{i}.png';im.save(path)
 p=subprocess.run(['tesseract',str(path),'stdout','--tessdata-dir','models/tesseract','-l','chi_sim','--psm',str(psm)],check=True,capture_output=True,text=True);elapsed=time.perf_counter()-t
 return {'frame':i,'kind':kind,'psm':psm,'seconds':elapsed,'text':p.stdout,'cer':cer(norm(refs[i]),norm(p.stdout))}
candidates=[]
for kind in ['original','gray','white160','white180','white200','white220']:
 for psm in [6,7]:
  rows=[recognize(i,kind,psm) for i in [1,2]]
  score=cer(''.join(norm(refs[i]) for i in [1,2]),''.join(norm(r['text']) for r in rows))
  candidates.append({'kind':kind,'psm':psm,'development_cer':score,'rows':rows})
selected=min(candidates,key=lambda x:x['development_cer']);(root/'development.json').write_text(json.dumps({'candidates':candidates,'selected':{'kind':selected['kind'],'psm':selected['psm']}},ensure_ascii=False,indent=2));print('LOCKED',selected['kind'],selected['psm'],selected['development_cer'],flush=True)
held=[recognize(i,selected['kind'],selected['psm']) for i in [3,4,5,6]]
baseline=json.loads(pathlib.Path('outputs/ocr/results.json').read_text());base=[r for r in baseline if r['repeat']==0 and int(pathlib.Path(r['image']).stem.split('_')[-1]) in [3,4,5,6]]
denominator=sum(len(norm(refs[i])) for i in [3,4,5,6]);baseline_cer=sum(cer(norm(refs[int(pathlib.Path(r['image']).stem.split('_')[-1])]),norm(r['text']))*len(norm(refs[int(pathlib.Path(r['image']).stem.split('_')[-1])])) for r in base)/denominator;heldcer=sum(r['cer']*len(norm(refs[r['frame']])) for r in held)/denominator
result={'reference_kind':'assistant-read visible captions, not human gold','held_out_frames':[3,4,5,6],'reference_characters':sum(len(norm(refs[i])) for i in [3,4,5,6]),'selected_preprocessing':selected['kind'],'selected_psm':selected['psm'],'baseline_heldout_cer':baseline_cer,'improved_heldout_cer':heldcer,'baseline_mean_seconds':statistics.mean(r['elapsed_seconds'] for r in base),'improved_mean_seconds':statistics.mean(r['seconds'] for r in held),'rows':held,'warning':'4 frames from same video/font, selected after2 development frames; not representative generalization. Baseline480px JPEG vs improved848px PNG+crop; cannot isolate which change caused improvement. Improved timings include preprocessing and file save.'}
(root/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
