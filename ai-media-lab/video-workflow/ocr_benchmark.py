import pathlib,subprocess,time,json
from PIL import Image
root=pathlib.Path('outputs/ocr');root.mkdir(exist_ok=True)
rows=[]
for i in [1,2,3,4,5,6,7]:
    src=pathlib.Path(f'outputs/ma_jian/frames/uniform_{i:03d}.jpg');im=Image.open(src);w,h=im.size;crop=im.crop((0,int(h*.7),w,h)).resize((w*3,int(h*.3)*3));path=root/f'crop_{i}.png';crop.save(path)
    for rep in range(2):
        t=time.perf_counter();p=subprocess.run(['tesseract',str(path),'stdout','--tessdata-dir','models/tesseract','-l','chi_sim','--psm','6'],capture_output=True,text=True,check=True);elapsed=time.perf_counter()-t
        rows.append({'image':str(src),'crop':str(path),'repeat':rep,'elapsed_seconds':elapsed,'text':p.stdout})
(root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(rows,ensure_ascii=False,indent=2))
