import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from utp.core import Engine, protect, restore
from utp.providers import MockProvider, BaiduProvider, TranslationError, baidu_signature, OpenAICompatibleProvider
from utp.__main__ import process_request, drain
from utp.storage import private_dir


class Recording(MockProvider):
    def __init__(self): self.calls = 0
    def translate(self, *args):
        self.calls += 1
        return super().translate(*args)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.provider = Recording()
        self.engine = Engine({}, self.provider, self.root)
    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()
    def test_format_preservation(self):
        source = '  Hello {PlayerName}!\r\n<Style color="red">Welcome</> %02d\\n  '
        result, status = self.engine.translate(source)
        self.assertEqual(result, '  你好 {PlayerName}!\r\n<Style color="red">欢迎</> %02d\\n  ')
        self.assertEqual(status, 'translated')
    def test_token_mutation_rejected(self):
        masked, values, nonce = protect('Hello {name}')
        with self.assertRaises(TranslationError): restore(masked.replace('ZXQKEEP', 'oops'), values, nonce)
    def test_dedup(self):
        request = {'version':1,'texts':[{'id':'a','text':'Hello'},{'id':'b','text':'Hello'}]}
        result = process_request(self.engine, request)
        self.assertEqual(self.provider.calls, 1)
        self.assertEqual(result['results'][0]['original_sha256'],hashlib.sha256(b'Hello').hexdigest())
        self.assertEqual(self.engine.translate('Hello')[1], 'cache')
    def test_no_plaintext_persistent_cache(self):
        self.engine.translate('Hello')
        self.assertNotIn('cache', [r[0] for r in self.engine.db.execute("SELECT name FROM sqlite_master WHERE type='table'")])
    def test_skip(self):
        for s in ('','  ','123.45%','{value}','{count, plural, one {x} other {y}}'):
            self.assertEqual(self.engine.translate(s), (s,'skipped'))
    def test_remote_opt_in(self):
        self.provider.remote = True
        with self.assertRaisesRegex(TranslationError, 'disabled'): self.engine.translate('Hello')
        self.assertEqual(self.provider.calls, 0)
    def test_budget_fail_closed(self):
        self.provider.remote = True
        self.engine.allow_remote = True
        self.engine.daily_chars = 1
        with self.assertRaisesRegex(TranslationError, 'budget'): self.engine.translate('Hello')
        self.assertEqual(self.provider.calls, 0)
    def test_invalid_ids(self):
        for ids in (['same','same'],['../x','b']):
            with self.assertRaises(TranslationError):
                process_request(self.engine,{'version':1,'texts':[{'id':i,'text':'Hello'} for i in ids]})
    def test_file_queue(self):
        (self.root/'inbox').mkdir()
        (self.root/'inbox'/'one.json').write_text(json.dumps({'version':1,'texts':[{'id':'a','text':'Start game'}]}))
        self.assertEqual(drain(self.engine,self.root),1)
        self.assertFalse((self.root/'inbox'/'one.json').exists())
        self.assertEqual(json.loads((self.root/'outbox'/'one.json').read_text())['results'][0]['text'],'开始游戏')
    def test_symlink_rejected(self):
        link = self.root/'link'
        try: link.symlink_to(self.root, target_is_directory=True)
        except (OSError,NotImplementedError): self.skipTest('Symlinks unavailable')
        with self.assertRaises(TranslationError): private_dir(link)
    def test_baidu_signature(self):
        self.assertEqual(baidu_signature('app','你好 & x','salt','secret'), hashlib.md5('app你好 & xsaltsecret'.encode('utf-8')).hexdigest())
    def test_baidu_queue_refuses_persistence(self):
        with patch.dict('os.environ',{'BAIDU_APP_ID':'fake','BAIDU_SECRET_KEY':'fake'}):
            self.engine.provider = BaiduProvider()
            with self.assertRaisesRegex(TranslationError, 'file-queue'):
                drain(self.engine, self.root)
            self.assertFalse((self.root/'outbox').exists())
    def test_baidu_form_and_response(self):
        with patch.dict('os.environ',{'BAIDU_APP_ID':'fake','BAIDU_SECRET_KEY':'fake'}), patch('utp.providers.post_json', return_value={'trans_result':[{'dst':'你好'}]}) as post:
            self.assertEqual(BaiduProvider().translate('Hello','auto','zh'),'你好')
            self.assertIn(b'q=Hello',post.call_args.args[1])
    def test_baidu_error_redacted(self):
        with patch.dict('os.environ',{'BAIDU_APP_ID':'fake','BAIDU_SECRET_KEY':'fake'}), patch('utp.providers.post_json', return_value={'error_code':'54004','error_msg':'private'}):
            with self.assertRaises(TranslationError) as error: BaiduProvider().translate('Hello','auto','zh')
            self.assertNotIn('private',str(error.exception))
    def test_endpoint_rejected(self):
        for url in ('http://example.test/v1','https://user:pass@example.test','https://example.test?key=abc'):
            with self.assertRaises(TranslationError): OpenAICompatibleProvider({'base_url':url,'model':'demo'})
    def test_auto_target_rejected(self):
        with self.assertRaises(TranslationError): Engine({'target':'auto'},self.provider,self.root)

if __name__ == '__main__': unittest.main()
