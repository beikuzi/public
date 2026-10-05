"""Standard-library tests: also run using python -O -m unittest."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from validation import MASTER_SHA, EXPECTED_IDS, validate_annotations, validate_boundary_inputs, validate_regions, verify_hash


def annotations():
    return {'source_sha256': MASTER_SHA, 'timebase': 'decoded_audio_seconds', 'segments': [
        {'id': sid, 'start': 1.0, 'end': 2.0, 'speaker': 'Sintel', 'target': True, 'transcript': 'Fixture'} for sid in sorted(EXPECTED_IDS)]}


def boundaries():
    common = {'complete': True, 'source_sha256': MASTER_SHA, 'sample_rate': 48000, 'timebase': 'decoded_audio_samples'}
    audit = dict(common, segments=[{'id': sid, 'context_start_sample': 0, 'context_end_sample': 48000,
        'signals': {'center': {'speech_regions': [{'start_sample': 0, 'end_sample': 48000}]}}} for sid in sorted(EXPECTED_IDS)])
    proposals = dict(common, proposals=[{'id': sid, 'overlap': None, 'human_auditory_review': False,
        'proposal_status': 'machine_supported_candidate', 'proposed_regions': [{'start_sample': 0, 'end_sample': 48000}],
        'proposed_speech_seconds': 1.0} for sid in sorted(EXPECTED_IDS)])
    return audit, proposals


class ValidationTests(unittest.TestCase):
    def test_valid_fixtures(self):
        validate_annotations(annotations())
        validate_boundary_inputs(*boundaries())

    def test_wrong_source_rejected(self):
        ann = annotations(); ann['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_annotations(ann)

    def test_nonfinite_and_out_of_range_bounds_rejected(self):
        for value in (float('nan'), float('inf'), -1, True):
            ann = annotations(); ann['segments'][0]['start'] = value
            with self.assertRaises(ValueError): validate_annotations(ann)

    def test_duplicate_ids_rejected(self):
        ann = annotations(); ann['segments'][0]['id'] = ann['segments'][1]['id']
        with self.assertRaises(ValueError): validate_annotations(ann)

    def test_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'fixture.ckpt'; p.write_bytes(b'expected bytes')
            good = hashlib.sha256(p.read_bytes()).hexdigest(); verify_hash(p, good)
            p.write_bytes(b'tampered bytes')
            with self.assertRaises(ValueError): verify_hash(p, good)

    def test_overlap_and_boolean_samples_rejected(self):
        for regions in ([{'start_sample': 0, 'end_sample': 10}, {'start_sample': 9, 'end_sample': 12}],
                        [{'start_sample': False, 'end_sample': 10}]):
            with self.assertRaises(ValueError): validate_regions(regions)

    def test_incomplete_boundary_rejected(self):
        audit, proposals = boundaries(); audit['complete'] = False
        with self.assertRaises(ValueError): validate_boundary_inputs(audit, proposals)

    def test_duration_mismatch_rejected(self):
        audit, proposals = boundaries(); proposals['proposals'][0]['proposed_speech_seconds'] = 8
        with self.assertRaises(ValueError): validate_boundary_inputs(audit, proposals)

    def test_promoted_overlap_claim_rejected(self):
        audit, proposals = boundaries(); proposals['proposals'][0]['overlap'] = False
        with self.assertRaises(ValueError): validate_boundary_inputs(audit, proposals)

    def test_accepted_empty_boundary_rejected(self):
        audit, proposals = boundaries(); proposals['proposals'][0]['proposed_regions'] = []
        with self.assertRaises(ValueError): validate_boundary_inputs(audit, proposals)

if __name__ == '__main__':
    unittest.main()
