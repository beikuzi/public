import unittest
from export_public_evidence import export_initial, export_v2

class PublicExportTests(unittest.TestCase):
    def test_initial_drops_transcripts_and_embeddings(self):
        row = {'id': 'srt_001', 'transcript': 'Do not publish this fixture', 'embedding': [1, 2], 'output_path': '/private/fixture', 'training_ready': False}
        exported = export_initial({'segments': [row]})['segments'][0]
        self.assertEqual(exported, {'id': 'srt_001', 'training_ready': False})

    def test_v2_drops_top_level_private_fields(self):
        source = {'transcripts': ['Do not publish'], 'local_path': '/private/fixture', 'experiments': {'fixture': {'anchors': {}, 'summary': {}, 'segments': [{'id': 'srt_001', 'transcript': 'Do not publish', 'overlap': None}]}}}
        exported = export_v2(source)
        self.assertNotIn('transcripts', exported)
        self.assertNotIn('local_path', exported)
        self.assertEqual(exported['experiments']['fixture']['segments'], [{'id': 'srt_001', 'overlap': None}])

if __name__ == '__main__':
    unittest.main()
