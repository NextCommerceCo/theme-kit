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
from ntk.exceptions import NTKError
from ntk.ntk_parser import Parser
from ntk.output import Output
from ntk.utils import get_template_name, progress_bar
from ntk.validation import _template_errors, validate_local_file


class TestToolingContract(unittest.TestCase):
    def test_store_normalizes_bare_hostname_and_rejects_paths(self):
        self.assertEqual(Config.normalize_store('store.example.com/'), 'https://store.example.com')
        self.assertEqual(Config.normalize_store('http://store.example.com'), 'https://store.example.com')
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
        output.json = False
        self.assertFalse(output.error('push', 'broken')['ok'])

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

    def test_local_validation_covers_media_paths_and_product_inheritance(self):
        self.assertEqual(_template_errors('{% endblock %}'), ['endblock has no matching block'])
        self.assertEqual(
            _template_errors('{% block alpha %}{% endblock beta %}'),
            ['endblock beta closes block alpha'],
        )
        with tempfile.TemporaryDirectory() as directory:
            old_directory = os.getcwd()
            try:
                os.chdir(directory)
                os.makedirs('templates/catalogue')
                product_path = 'templates/catalogue/product.custom.html'
                with open(product_path, 'w', encoding='utf-8') as output_file:
                    output_file.write('{% extends "templates/catalogue/product.html" %}')
                with open('image.png', 'wb') as output_file:
                    output_file.write(b'png')
                self.assertEqual(validate_local_file(product_path)['status'], 'invalid')
                self.assertEqual(validate_local_file('image.png')['status'], 'valid')
                self.assertEqual(validate_local_file('missing.json')['status'], 'invalid')
                self.assertEqual(validate_local_file('unsupported.txt')['status'], 'invalid')
                with open('bad.js', 'w', encoding='utf-8') as output_file:
                    output_file.write('\ufeffconst bad = "\x00";')
                js_result = validate_local_file('bad.js')
                self.assertEqual(js_result['status'], 'invalid')
                self.assertEqual(len(js_result['errors']), 2)
            finally:
                os.chdir(old_directory)

    @patch('ntk.utils.os.path.relpath', side_effect=ValueError)
    def test_template_name_handles_windows_cross_drive_path(self, _relpath):
        self.assertTrue(get_template_name('/tmp/theme.json').endswith('tmp/theme.json'))

    @patch('ntk.command.Gateway')
    @patch('ntk.command.Config.read_config')
    def test_validate_reports_local_rejections_and_server_results(self, _read_config, gateway):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'settings.json')
            with open(path, 'w', encoding='utf-8') as output_file:
                output_file.write('{}')
            command = Command()
            command.config.apikey = 'key'
            command.config.store = 'https://store.example.com'
            command.config.theme_id = 42
            command._get_accept_files = MagicMock(return_value=[path])
            gateway.return_value.validate_template.return_value.ok = True
            parser = SimpleNamespace(
                env='development', apikey=None, store=None, theme_id=None,
                sass_output_style=None, filenames=[path, 'bad.tmp'], server=False,
                json=False, quiet=True, no_progress=True,
            )
            local_result = command.validate(parser)
            self.assertFalse(local_result['ok'])
            self.assertEqual(local_result['results'][0]['status'], 'invalid')

            parser.filenames = [path]
            parser.server = True
            server_result = command.validate(parser)
            self.assertTrue(server_result['ok'])
            self.assertEqual(server_result['mode'], 'server')
            gateway.return_value.validate_template.assert_called_once()

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
                parser.viewports = 'tablet'
                with self.assertRaises(TypeError):
                    command.capture(parser)

        self.assertTrue(result['ok'])
        self.assertEqual([page.viewport['width'] for page in pages], [1440, 390])
        self.assertTrue(all('preview_theme=42' in page.goto_calls[0][0] for page in pages))
        self.assertTrue(all(page.goto_calls[0][1]['timeout'] == 1234 for page in pages))

    @patch('ntk.command.Config.read_config')
    def test_optional_sass_failures_are_actionable(self, _read_config):
        command = Command()
        with patch('ntk.command.sass', None):
            with patch('ntk.command.importlib.import_module', side_effect=ImportError):
                with self.assertRaises(NTKError):
                    command._compile_sass()
        compiler = MagicMock()
        compiler.compile.side_effect = RuntimeError('compile failed')
        with patch('ntk.command.sass', compiler):
            with self.assertRaises(NTKError):
                command._compile_sass()

    @patch('ntk.command.Gateway')
    @patch('ntk.command.Config.read_config')
    def test_transfer_failures_are_returned_per_file(self, _read_config, gateway):
        command = Command()
        command.output.quiet = True
        response = gateway.return_value.create_or_update_template.return_value
        response.ok = False
        response.status_code = 500
        with tempfile.TemporaryDirectory() as directory:
            old_directory = os.getcwd()
            try:
                os.chdir(directory)
                os.makedirs('templates')
                with open('templates/index.html', 'w', encoding='utf-8') as output_file:
                    output_file.write('ok')
                command._get_accept_files = MagicMock(return_value=[os.path.abspath('templates/index.html')])
                pushed = command._push_templates(['templates/index.html'])
            finally:
                os.chdir(old_directory)
        self.assertEqual(pushed[0]['status'], 'failed')

        delete_response = gateway.return_value.delete_template.return_value
        delete_response.ok = False
        delete_response.status_code = 503
        deleted = command._delete_templates(['templates/index.html'])
        self.assertEqual(deleted[0]['status'], 'failed')

    @patch('ntk.command.Config.read_config')
    def test_capture_without_optional_dependency_is_actionable(self, _read_config):
        command = Command()
        parser = SimpleNamespace(
            env='development', apikey=None, store='store.example.com', theme_id=42,
            sass_output_style=None, json=False, quiet=True, no_progress=True,
            url='/', output='qa-output', viewports='desktop', settle_timeout=1000,
        )
        with patch.dict('sys.modules', {'playwright.sync_api': None}):
            with self.assertRaises(NTKError):
                command.capture(parser)

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
