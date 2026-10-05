import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


class HttpTests(unittest.TestCase):
    def test_local_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            config.write_text('{"provider":"mock"}')
            with socket.socket() as probe:
                probe.bind(('127.0.0.1',0))
                port = probe.getsockname()[1]
            proc = subprocess.Popen([sys.executable,'-m','utp','--config',str(config),'--runtime',str(root/'runtime'),'--serve','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                token_file = root/'runtime'/'local-token.txt'
                deadline = time.monotonic() + 5
                while not token_file.exists() and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(token_file.exists())
                token = token_file.read_text()
                url = f'http://127.0.0.1:{port}/v1/chat/completions'
                def request(text, key=token, origin=None):
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
                    if origin: headers['Origin']=origin
                    return urllib.request.urlopen(urllib.request.Request(url,data=json.dumps({'messages':[{'role':'user','content':text}]}).encode(),headers=headers),timeout=3)
                # Token file is created just before listener startup.
                while True:
                    try:
                        with request('Hello') as response:
                            self.assertEqual(json.load(response)['choices'][0]['message']['content'],'你好')
                        break
                    except urllib.error.URLError:
                        if time.monotonic() >= deadline: raise
                        time.sleep(.02)
                with self.assertRaises(urllib.error.HTTPError) as invalid:
                    request('Hello',key='wrong')
                self.assertEqual(invalid.exception.code,401)
                with self.assertRaises(urllib.error.HTTPError) as browser:
                    request('Hello',origin='https://untrusted.example')
                self.assertEqual(browser.exception.code,404)
                wrapper='Translate the following text to Chinese. Preserve any formatting, special characters, and placeholders like {0}, %s, etc. Only output the translation, nothing else.\n\nText to translate:\n'
                with request(wrapper+'Hello {Name}') as response:
                    self.assertEqual(json.load(response)['choices'][0]['message']['content'],'你好 {Name}')
                # Raw game text containing this phrase must not be truncated.
                with request('Hello\nText to translate:\nWelcome') as response:
                    self.assertEqual(json.load(response)['choices'][0]['message']['content'],'你好\nText to translate:\n欢迎')
                if os.name == 'posix':
                    self.assertEqual(token_file.stat().st_mode & 0o777,0o600)
            finally:
                proc.terminate()
                proc.communicate(timeout=5)

if __name__ == '__main__': unittest.main()
