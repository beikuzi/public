"""Fail-closed provenance checks. No security or data check relies on assert."""
import hashlib
import math
from pathlib import Path

MASTER_SHA = 'bcdfe981cb705d2dbf5a4d6341172865be41eb745cea5ceb6c58bf123b095750'
STEREO_SHA = '49b279400b6fcad23f6a8862ae65a2a22f21f249cd7576b09991880da221412b'
CHECKPOINT_SHA = '0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2'
DURATION = 888
SR = 48000
EXPECTED_IDS = {f'srt_{i:03d}' for i in range(1, 27)}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def verify_hash(path, expected):
    require(sha256_file(path) == expected, f'Integrity mismatch: {Path(path).name}')

def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)

def validate_annotations(ann):
    require(ann.get('source_sha256') == MASTER_SHA, 'Annotation source mismatch')
    require(ann.get('timebase') == 'decoded_audio_seconds', 'Unsupported annotation timebase')
    rows = ann.get('segments', [])
    require(len(rows) == 26 and {r.get('id') for r in rows} == EXPECTED_IDS, 'Incomplete or duplicate annotation IDs')
    for row in rows:
        a, b = row.get('start'), row.get('end')
        require(finite_number(a) and finite_number(b) and 0 <= a < b <= DURATION, 'Invalid annotation bounds')
        require(row.get('speaker') in ('Sintel', 'Shaman'), 'Unknown speaker label')
        require(type(row.get('target')) is bool, 'Invalid target flag')
        require(isinstance(row.get('transcript'), str), 'Missing caption text')

def validate_runtime_inputs(root, ann):
    validate_annotations(ann)
    verify_hash(root / 'embedding_model.ckpt', CHECKPOINT_SHA)
    verify_hash(root.parent / 'source/sintel-master-51.flac', MASTER_SHA)
    verify_hash(root.parent / 'source/sintel-master-st.flac', STEREO_SHA)

def validate_regions(regions, lower=0, upper=DURATION * SR):
    require(isinstance(regions, list), 'Regions must be a list')
    last = lower
    for region in regions:
        a, b = region.get('start_sample'), region.get('end_sample')
        require(type(a) is int and type(b) is int and lower <= a < b <= upper, 'Invalid sample bounds')
        require(a >= last, 'Unsorted or overlapping speech regions')
        last = b

def validate_boundary_inputs(audit, proposals):
    for data, key in ((audit, 'segments'), (proposals, 'proposals')):
        require(data.get('complete') is True, 'Incomplete boundary evidence')
        require(data.get('source_sha256') == MASTER_SHA, 'Boundary source mismatch')
        require(data.get('sample_rate') == SR and data.get('timebase') == 'decoded_audio_samples', 'Boundary timebase mismatch')
        rows = data.get(key, [])
        require(len(rows) == 26 and {r.get('id') for r in rows} == EXPECTED_IDS, 'Incomplete or duplicate boundary IDs')
    for row in audit['segments']:
        lower, upper = row.get('context_start_sample'), row.get('context_end_sample')
        validate_regions([{'start_sample': lower, 'end_sample': upper}])
        for signal in row.get('signals', {}).values():
            validate_regions(signal.get('speech_regions'), lower, upper)
    for row in proposals['proposals']:
        regions = row.get('proposed_regions')
        validate_regions(regions)
        require(row.get('overlap') is None and row.get('human_auditory_review') is False, 'Unexpected promoted boundary claim')
        if row.get('proposal_status') == 'machine_supported_candidate':
            require(bool(regions), 'Accepted proposal has no speech')
            duration = sum(r['end_sample'] - r['start_sample'] for r in regions) / SR
            require(finite_number(row.get('proposed_speech_seconds')) and abs(duration - row['proposed_speech_seconds']) < 1e-6, 'Proposal duration mismatch')

def validate_context(root, context):
    require(context.get('complete') is True and context.get('source_sha256') == STEREO_SHA, 'Neural context source mismatch')
    seen = set()
    for row in context.get('segments', []):
        sid = row.get('segment_id')
        require(sid in EXPECTED_IDS and sid not in seen, 'Invalid neural context ID')
        seen.add(sid)
        require(row.get('source_sha256') == STEREO_SHA and row.get('sample_rate') == SR, 'Neural context provenance mismatch')
        a, b = row.get('output_source_start_sample'), row.get('output_source_end_sample')
        validate_regions([{'start_sample': a, 'end_sample': b}])
        require(row.get('samples') == b - a, 'Neural context length mismatch')
        expected = (root.parent / 'separation/contextual' / f'{sid}_context_vocals.wav').resolve()
        require(expected.is_relative_to(root.parent.resolve()), 'Neural context path escapes workspace')
        require(Path(row['output_path']).resolve() == expected and expected.is_file(), 'Untrusted neural context path')
