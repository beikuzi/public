"""Optional offline vetted VITS backends; requires explicitly supplied vetted local files."""
import hashlib,json,pathlib

class NeuralVoice:
    def __init__(self, model_dir, speaker=10, speed=1.0, model_type="aishell3"):
        if model_type not in {"aishell3","melo"}:raise ValueError("Unsupported neural model type")
        if not model_dir:raise ValueError('--model-dir is required for neural backends; no automatic download')
        root=pathlib.Path(model_dir).expanduser().resolve()
        if not root.is_dir():raise ValueError('The supplied local model directory does not exist')
        expected=json.loads((pathlib.Path(__file__).parent/f'provenance/{model_type}-files.sha256.json').read_text())
        for filename,digest in expected.items():
            path=root/filename
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError(f'Model provenance/hash check failed: {filename}')
        import sherpa_onnx as s
        self.model_sha256=expected['model.onnx']
        config=s.OfflineTtsConfig(model=s.OfflineTtsModelConfig(vits=s.OfflineTtsVitsModelConfig(model=str(root/'model.onnx'),lexicon=str(root/'lexicon.txt'),tokens=str(root/'tokens.txt')),num_threads=2,provider='cpu'),rule_fsts=','.join(str(root/f) for f in ['phone.fst','date.fst','number.fst']))
        if not config.validate():raise ValueError('Invalid vetted VITS model configuration')
        self.engine=s.OfflineTts(config);self.sr=self.engine.sample_rate
        if not 0<=speaker<self.engine.num_speakers:raise ValueError('Speaker index out of range')
        self.speaker=speaker;self.speed=speed
    def say(self,text):
        import numpy as np
        audio=self.engine.generate(text,sid=self.speaker,speed=self.speed)
        samples=np.asarray(audio.samples)
        if audio.sample_rate!=self.sr or not len(samples) or not np.isfinite(samples).all():
            raise RuntimeError('Neural TTS returned invalid audio')
        if np.abs(samples).max()>=1:raise RuntimeError('Neural TTS source audio clips')
        return np.round(samples*32767).astype('<i2').tobytes()
