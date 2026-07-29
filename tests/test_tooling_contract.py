import io
import json
import os
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ntk.command import Command
from ntk.conf import Config
from ntk.ntk_parser import Parser
from ntk.output import Output
from ntk.utils import progress_bar
from ntk.validation import validate_local_file


class TestToolingContract(unittest.TestCase):
    def test_store_normalizes_bare_hostname_and_rejects_paths(self):
        self.assertEqual(Config.normalize_store('store.example.com/'), 'https://store.example.com')
        with self.assertRaises(TypeError):
            Config.normalize_store('https://store.example.com/admin')

    def test_machine_output_has_stable_envelope(self):
        output = Output()
        output.json = True
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            payload = output.result('push', results=[], count=0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload['schema_version'], '1')
        self.assertTrue(payload['ok'])

    def test_progress_is_ascii_stderr_and_disabled_when_requested(self):
        stream = io.StringIO()
        self.assertEqual(list(progress_bar([1], enabled=True, stream=stream, length=2)), [1])
        self.assertIn('##', stream.getvalue())
        self.assertNotIn('\u2588', stream.getvalue())
        stream = io.StringIO()
        self.assertEqual(list(progress_bar([1], enabled=False, stream=stream)), [1])
        self.assertEqual(stream.getvalue(), '')

    def test_parser_exposes_validate_capture_and_machine_flags(self):
        parser = Parser().create_parser()
        validate = parser.parse_args(['validate', '--json', '--server', 'templates/index.html'])
        self.assertTrue(validate.json)
        self.assertTrue(validate.server)
        capture = parser.parse_args([
            'capture', '--url', '/', '--output', 'qa-output', '--viewports', 'desktop,mobile', '--no-progress'
        ])
        self.assertEqual(capture.viewports, 'desktop,mobile')
        self.assertTrue(capture.no_progress)

    def test_local_validation_detects_json_and_template_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = os.path.join(directory, 'bad.json')
            html_path = os.path.join(directory, 'bad.html')
            with open(json_path, 'w', encoding='utf-8') as output_file:
                output_file.write('{')
            with open(html_path, 'w', encoding='utf-8') as output_file:
                output_file.write('{% block content %}')
            self.assertEqual(validate_local_file(json_path)['status'], 'invalid')
            self.assertEqual(validate_local_file(html_path)['status'], 'invalid')

    @patch('ntk.command.Config.read_config')
    def test_capture_uses_fixed_viewports_and_settle_contract(self, _read_config):
        pages = []

        class FakePage:
            def __init__(self, viewport):
                self.viewport = viewport
                self.goto_calls = []
                self.screenshot_calls = []

            def goto(self, url, **kwargs):
                self.goto_calls.append((url, kwargs))

            def evaluate(self, script):
                return None

            def wait_for_function(self, script, **kwargs):
                return None

            def screenshot(self, **kwargs):
                self.screenshot_calls.append(kwargs)

            def close(self):
                return None

        class FakeBrowser:
            def new_page(self, viewport):
                page = FakePage(viewport)
                pages.append(page)
                return page

            def close(self):
                return None

        fake_playwright = SimpleNamespace(
            chromium=SimpleNamespace(launch=lambda **kwargs: FakeBrowser())
        )

        class FakeContext:
            def __enter__(self):
                return fake_playwright

            def __exit__(self, *args):
                return None

        sync_api = types.ModuleType('playwright.sync_api')
        sync_api.sync_playwright = lambda: FakeContext()
        playwright = types.ModuleType('playwright')
        with tempfile.TemporaryDirectory() as output_dir:
            with patch.dict('sys.modules', {'playwright': playwright, 'playwright.sync_api': sync_api}):
                command = Command()
                parser = SimpleNamespace(
                    env='development', apikey=None, store='store.example.com', theme_id=42,
                    sass_output_style=None, json=False, quiet=True, no_progress=True,
                    url='products/example?skip_cache=1', output=output_dir,
                    viewports='desktop,mobile', settle_timeout=1234,
                )
                result = command.capture(parser)

        self.assertTrue(result['ok'])
        self.assertEqual([page.viewport['width'] for page in pages], [1440, 390])
        self.assertTrue(all('preview_theme=42' in page.goto_calls[0][0] for page in pages))
        self.assertTrue(all(page.goto_calls[0][1]['timeout'] == 1234 for page in pages))

    @patch('ntk.command.Gateway')
    @patch('ntk.command.Config.read_config')
    def test_push_reports_invalid_explicit_file_and_fails(self, _read_config, gateway):
        command = Command()
        command.config.apikey = 'key'
        command.config.store = 'https://store.example.com'
        command.config.theme_id = 1
        command._get_accept_files = MagicMock(return_value=[])
        parser = SimpleNamespace(
            env='development', apikey=None, store=None, theme_id=None, sass_output_style=None,
            filenames=['templates/index.html.tmp'], json=False, quiet=True, no_progress=True,
        )
        result = command.push(parser)
        self.assertFalse(result['ok'])
        self.assertEqual(result['results'][0]['status'], 'rejected')
        gateway.return_value.create_or_update_template.assert_not_called()


if __name__ == '__main__':
    unittest.main()
