"""Conservative waveform alignment of role-labelled production dialogue to a film mix.

No speaker purity, linguistic boundary, or absence-of-overlap assertion is made.
Inputs are local audio and independently generated VAD intervals in seconds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, correlate, resample_poly, sosfiltfilt


def normalized_match(movie: np.ndarray, source: np.ndarray) -> tuple[int, float]:
    if len(source) == 0 or len(source) > len(movie):
        raise ValueError('Source window must be nonempty and no longer than movie')
    energy = float(np.sum(source.astype(np.float64) ** 2))
    if energy <= 1e-20:
        raise ValueError('Silent source window is not an alignment anchor')
    correlation = correlate(movie, source, mode='valid', method='fft')
    cumulative = np.r_[0., np.cumsum(movie.astype(np.float64) ** 2)]
    local_energy = cumulative[len(source):] - cumulative[:-len(source)]
    scores = correlation / np.sqrt(np.maximum(1e-20, local_energy * energy))
    index = int(np.argmax(np.abs(scores)))
    return index, float(scores[index])


def union_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if end < start:
            raise ValueError('Interval end precedes start')
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def group_anchors(anchors, threshold=.60, max_gap=.85, offset_tolerance=.012):
    groups = []
    for anchor in anchors:
        if abs(anchor['correlation']) < threshold:
            continue
        if (groups and
            anchor['source_start'] - groups[-1][-1]['source_start'] < max_gap and
            abs(anchor['offset'] - np.median([a['offset'] for a in groups[-1]])) < offset_tolerance):
            groups[-1].append(anchor)
        else:
            groups.append([anchor])
    return [group for group in groups if len(group) >= 2]


def read_filtered(path, rate=4000):
    audio, native_rate = sf.read(path, dtype='float32', always_2d=True)
    mono = audio.mean(axis=1)
    divisor = np.gcd(rate, native_rate)
    downsampled = resample_poly(mono, rate // divisor, native_rate // divisor)
    filt = butter(3, [100, 1700], btype='bandpass', fs=rate, output='sos')
    return sosfiltfilt(filt, downsampled).astype('float32')


def align_interiors(movie, source, speech_regions, rate=4000):
    if len(source) < rate:
        return {'anchors': [], 'matched_interiors': []}
    anchors = []
    for region in speech_regions:
        starts = np.arange(max(0, region['start']-.1),
                           max(region['start']-.099, region['end']-.6), .4)
        for start in starts:
            sample = min(round(start * rate), len(source)-rate)
            window = source[sample:sample+rate]
            if np.sum(window.astype(np.float64)**2) <= 1e-20:
                continue
            index, coefficient = normalized_match(movie, window)
            anchors.append({'source_start': sample/rate, 'movie_start': index/rate,
                            'offset': (index-sample)/rate, 'correlation': coefficient})
    interiors = []
    for group in group_anchors(anchors):
        offset = float(np.median([a['offset'] for a in group]))
        first, last = group[0]['source_start'], group[-1]['source_start']+1
        for region in speech_regions:
            start, end = max(first, region['start']), min(last, region['end'])
            if end-start >= .4:
                interiors.append({'source_start': start, 'source_end': end,
                                  'movie_start': start+offset, 'movie_end': end+offset,
                                  'offset': offset, 'anchor_count': len(group),
                                  'median_abs_correlation': float(np.median([abs(a['correlation']) for a in group]))})
    return {'anchors': anchors, 'matched_interiors': interiors}


def refine_local_offset(movie, source, source_start, source_end, offset, rate=48000):
    anchors = []
    for start in np.arange(source_start, source_end-.5, .5):
        sample = round(start*rate)
        window = source[sample:sample+rate]
        left = max(0, round((start+offset-.03)*rate))
        right = min(len(movie), left+len(window)+round(.06*rate))
        if right-left < len(window) or np.sum(window.astype(np.float64)**2) <= 1e-20:
            continue
        index, coefficient = normalized_match(movie[left:right], window)
        anchors.append({'source_sample': sample, 'movie_sample': left+index,
                        'offset_samples': left+index-sample, 'correlation': coefficient})
    return anchors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--movie', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--speech-regions', type=Path, required=True,
                        help='JSON array of {start, end} seconds, from independent VAD')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = align_interiors(read_filtered(args.movie), read_filtered(args.source),
                             json.loads(args.speech_regions.read_text()))
    result.update(schema_version=1, analysis_rate=4000, human_auditory_review=False,
                  complete_utterance_boundaries_verified=False, overlap_free_verified=False,
                  movie_sha256=hashlib.sha256(args.movie.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
