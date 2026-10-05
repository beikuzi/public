"""Separate contiguous annotated source spans with context; never concatenate first.

Fresh output directories only. Segment IDs are filenames, not paths. A failure
leaves diagnostics in place; use a new output directory for a deliberate retry.
"""
import argparse, hashlib, json, math, re, subprocess, time
from pathlib import Path
from scipy.io import wavfile
from separate import separate, MODEL_SHA256

SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')

def validate_segments(annotations, duration, context, include_unknown=False):
    if not math.isfinite(context) or not 0 <= context <= 30:
        raise ValueError('context must be finite and between 0 and 30 seconds')
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('source duration must be finite and positive')
    selected = []
    seen = set()
    for segment in annotations['segments']:
        identifier = segment.get('id')
        if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier):
            raise ValueError('Segment IDs must contain only letters, digits, underscores or hyphens, and start with a letter or digit')
        if identifier in seen:
            raise ValueError('Duplicate segment ID')
        seen.add(identifier)
        start, end = segment['start'], segment['end']
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError('Segment times must be numeric')
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration:
            raise ValueError('Segment bounds outside source')
        if segment.get('target') and not segment.get('review_quarantine') and (segment.get('quality') == 'noisy' or (include_unknown and segment.get('quality') == 'unknown')):
            selected.append(segment)
    if not selected:
        raise ValueError('No eligible target segments to process')
    return selected

def prepare_output_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Output directory must not be a symbolic link')
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError('Output directory must be absent or empty; existing files will never be overwritten')
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()

def write_report(out, report):
    # This report is owned by this invocation, inside its initially empty directory.
    temp = out / 'segments_report.json.tmp'
    temp.write_text(json.dumps(report, indent=2))
    temp.replace(out / 'segments_report.json')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source'); parser.add_argument('annotations'); parser.add_argument('output_dir')
    parser.add_argument('--context', type=float, default=1.0)
    parser.add_argument('--include-unknown', action='store_true', help='Explicit diagnostic processing of unknown-quality spans; never relabels them as noisy or clean')
    args = parser.parse_args()
    source = Path(args.source).resolve()
    annotations = json.loads(Path(args.annotations).read_text())
    actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual_hash != annotations['source_sha256']:
        raise ValueError('Source SHA mismatch')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_streams', '-of', 'json', str(source)]))
    if not probe.get('streams'):
        raise ValueError('Source has no audio stream')
    info = probe['streams'][0]
    sr, duration = int(info['sample_rate']), float(info['duration'])
    selected = validate_segments(annotations, duration, args.context, args.include_unknown)
    out = prepare_output_directory(args.output_dir)
    rows = []; wall = time.perf_counter()
    for segment in selected:
        first = max(0, round((segment['start'] - args.context) * sr))
        last = min(round(duration * sr), round((segment['end'] + args.context) * sr))
        raw = out / (segment['id'] + '_context.wav')
        processed = out / (segment['id'] + '_context_vocals.wav')
        if raw.exists() or processed.exists():
            raise FileExistsError('Output appeared during processing; refusing overwrite')
        subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(source), '-map', '0:a:0', '-af', f'atrim=start_sample={first}:end_sample={last},asetpts=PTS-STARTPTS', '-ac', '2', '-c:a', 'pcm_f32le', str(raw)], check=True)
        got_sr, samples = wavfile.read(raw)
        if got_sr != sr or len(samples) != last - first:
            raise ValueError('Decoded context length mismatch')
        metrics = separate(raw, processed)
        rows.append({'segment_id': segment['id'], 'input_quality_label': segment.get('quality'), 'output_path': str(processed), 'output_source_start': first / sr, 'output_source_start_sample': first, 'output_source_end_sample': last, 'sample_rate': sr, 'samples': last - first, 'source_sha256': actual_hash, 'model': 'HDEMUCS_HIGH_MUSDB_PLUS', 'model_version': 'torchaudio 2.8.0+cpu', 'model_sha256': MODEL_SHA256, 'method': f'Neural vocal-stem separation of contiguous source with {args.context:g}s context; trim annotated target interval only after separation', 'limitations': ['All vocals, not target-speaker isolation', 'Annotation boundaries and overlap require separate verification', 'No auditory review; residual background and artifacts possible'], 'metrics': metrics})
        write_report(out, {'schema_version': 1, 'complete': False, 'segments': rows})
        print(segment['id'], round(metrics['wall_seconds'], 2), flush=True)
    result = {'schema_version': 1, 'complete': True, 'context_seconds': args.context, 'source_sha256': actual_hash, 'wall_seconds': time.perf_counter() - wall, 'segments': rows}
    write_report(out, result)
    print('DONE', len(rows), round(result['wall_seconds'], 2), flush=True)

if __name__ == '__main__':
    main()
