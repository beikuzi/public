import ctypes, pathlib, wave, importlib.util
root=pathlib.Path(importlib.util.find_spec('piper').origin).parent
lib=ctypes.CDLL(str(root/'espeakbridge.so'))
lib.espeak_Initialize.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
sr=lib.espeak_Initialize(2,0,str(root).encode(),0)
print('sr',sr)
lib.espeak_SetVoiceByName.argtypes=[ctypes.c_char_p]
print('voice',lib.espeak_SetVoiceByName(b'cmn'))
CB=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.POINTER(ctypes.c_short),ctypes.c_int,ctypes.c_void_p)
frames=[]
@CB
def cb(data,n,events):
 if data and n: frames.append(ctypes.string_at(data,n*2))
 return 0
lib.espeak_SetSynthCallback(cb)
text='第一步，把想法写成脚本。每一页只讲一个重点。'.encode('utf-8')
lib.espeak_Synth.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p]
print('synth',lib.espeak_Synth(text,len(text)+1,0,1,0,1,None,None))
lib.espeak_Synchronize()
print('bytes',sum(map(len,frames)))
with wave.open('/workspace/shared/html-video-workflow/test.wav','wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(frames))
