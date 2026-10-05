"""Export scalar audit evidence only; never embeddings, audio, or transcripts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fields(value, names):
    return {name: value[name] for name in names if name in value}


def export_initial(value):
    result = fields(value, ['method', 'summary', 'coverage', 'model_url', 'model_sha256', 'source_annotation_sha256', 'software', 'limitations', 'additional_limitations'])
    result['segments'] = [fields(row, ['id', 'start', 'end', 'speaker', 'target', 'duration_seconds', 'lexical_word_count', 'anchor', 'acoustic_results', 'triage', 'reasons', 'speaker_overlap', 'training_ready', 'human_auditory_review']) for row in value['segments']]
    result['publication_note'] = 'Scalar diagnostics and IDs only. Original transcripts, embeddings, audio, model weights, and local files are excluded. No ground-truth accuracy is claimed.'
    return result


def export_v2(value):
    result = fields(value, ['source_sha256', 'boundary_proposals_sha256', 'limitations'])
    result['experiments'] = {}
    for name, experiment in value['experiments'].items():
        result['experiments'][name] = {'anchors': experiment['anchors'], 'summary': experiment['summary'], 'segments': [fields(row, ['id', 'speaker', 'enrollment', 'evaluation_partition', 'original_caption_seconds', 'model_detected_speech_seconds', 'boundary_status', 'acoustic_results', 'acoustic_similarity_gates_pass', 'triage', 'reasons', 'overlap', 'human_auditory_review', 'training_ready']) for row in experiment['segments']]}
    result['publication_note'] = 'Two exploratory experiments; non-enrolled is not equivalent to human-validated independent ground truth. Scalar evidence only, no audio or embeddings.'
    return result


def main():
    for source, destination, exporter in [('verification.json', 'evidence-initial.public.json', export_initial), ('verification-v2.json', 'evidence-v2.public.json', export_v2)]:
        result = exporter(json.loads((ROOT / source).read_text()))
        payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if any(token in payload for token in ['/workspace/', '/home/', '/root/', '"transcript"', '"asr_text"', '"output_path"']):
            raise ValueError('Public export includes prohibited content')
        (ROOT / destination).write_text(payload)

if __name__ == '__main__':
    main()
