import os
import unittest
from unittest.mock import call, MagicMock, mock_open, patch

from watchfiles import Change

from ntk import conf
from ntk.command import Command


class TestCommand(unittest.TestCase):
    @patch("os.path.exists", autospec=True)
    @patch("yaml.load", autospec=True)
    @patch('ntk.command.Gateway', autospec=True)
    def setUp(self, mock_gateway, mock_load_yaml, mock_patch_exists):
        mock_patch_exists.return_value = True

        mock_load_yaml.return_value = {
            'sandbox': {
                'apikey': 'abc123f0122395acd',
                'store': 'https://sandbox.com',
                'theme_id': 999
            }
        }

        config = {
            'env': 'development',
            'apikey': 'abcd1234',
            'theme_id': 1234,
            'store': 'http://development.com',
            'sass_output_style': 'nested'
        }
        with patch('builtins.open', mock_open(read_data='yaml data')):
            self.parser = MagicMock(**config)
            self.command = Command()

            self.mock_file = mock_open(read_data='{% load i18n %}\n\n<div class=\"mt-2\">My home page</div>')
            self.mock_gateway = mock_gateway

    #####
    # init
    #####
    def test_init_command_without_config_file_should_be_required_name_api_key_store_theme_id(self):
        with self.assertRaises(TypeError) as error:
            self.parser.name = None
            self.parser.apikey = None
            self.parser.store = None
            self.parser.theme_id = None
            self.command.init(self.parser)
        self.assertEqual(str(error.exception), '[development] argument -a/--apikey, -s/--store are required.')

    @patch("ntk.command.Config.write_config", autospec=True)
    def test_init_command_with_name_and_configs_should_be_call_create_theme_and_save_config(self, mock_write_config):
        self.mock_gateway.return_value.create_theme.return_value.ok = True
        self.mock_gateway.return_value.create_theme.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.create_theme.return_value.json.return_value = {
            'id': 1234,
            'name': 'Test Init Theme',
            'active': False
        }
        with self.assertLogs(level='INFO') as cm:
            self.parser.name = 'Test Init Theme'
            self.parser.theme_id = None
            self.command.init(self.parser)

            expected_gateway_calls = [
                call(store=None, apikey=None),
                call().create_theme(name='Test Init Theme'),
                call().create_theme().json()
            ]
            self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        expected_logging = ['INFO:root:[development] Theme [1234] "Test Init Theme" has been created successfully.']
        self.assertEqual(cm.output, expected_logging)

        mock_write_config.assert_called_once()

    #####
    # list
    #####
    def test_list_command_without_config_file_should_be_required_api_key_store(self):
        with self.assertRaises(TypeError) as error:
            self.parser.apikey = None
            self.parser.store = None
            self.parser.theme_id = None
            self.command.list(self.parser)
        self.assertEqual(str(error.exception), '[development] argument -a/--apikey, -s/--store are required.')

    @patch("ntk.command.Config.write_config", autospec=True)
    def test_list_command_with_configs_should_be_show_theme_id_and_theme_name(self, mock_write_config):
        self.mock_gateway.return_value.get_themes.return_value.ok = True
        self.mock_gateway.return_value.get_themes.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.get_themes.return_value.json.return_value = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    'id': 1234,
                    'name': 'Default Theme',
                    'active': True
                },
                {
                    'id': 1235,
                    'name': 'Test Init Theme',
                    'active': False
                }
            ]
        }
        with self.assertLogs(level='INFO') as cm:
            self.command.list(self.parser)
            expected_gateway_calls = [
                call(store=None, apikey=None),
                call().get_themes(),
                call().get_themes().json()
            ]

            self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        expected_logging = [
            'INFO:root:[development] Available themes:',
            'INFO:root:[development] \t[1234] \tDefault Theme (Active)',
            'INFO:root:[development] \t[1235] \tTest Init Theme'
        ]
        self.assertEqual(cm.output, expected_logging)

        mock_write_config.assert_not_called()

    @patch("ntk.command.Config.write_config", autospec=True)
    def test_list_command_with_missing_theme_should_be_raise_message(
        self, mock_write_config
    ):
        self.mock_gateway.return_value.get_themes.return_value.ok = True
        self.mock_gateway.return_value.get_themes.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.get_themes.return_value.json.return_value = {
            "count": 0,
            "next": None,
            "previous": None,
            "results": []
        }
        with self.assertLogs(level='INFO') as cm:
            self.command.list(self.parser)
            expected_gateway_calls = [
                call(store=None, apikey=None),
                call().get_themes(),
                call().get_themes().json()
            ]

            self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        expected_logging = [
            'WARNING:root:[development] Missing Themes in http://development.com'
        ]
        self.assertEqual(cm.output, expected_logging)

        mock_write_config.assert_not_called()

    #####
    # checkout
    #####
    def test_checkout_command_without_config_file_should_be_required_api_key_store_and_theme_id(self):
        with self.assertRaises(TypeError) as error:
            self.parser.apikey = None
            self.parser.store = None
            self.parser.theme_id = None
            self.command.checkout(self.parser)
        self.assertEqual(
            str(error.exception), '[development] argument -a/--apikey, -s/--store, -t/--theme_id are required.')

    @patch("builtins.open", autospec=True)
    @patch("ntk.command.Config.write_config", autospec=True)
    def test_checkout_command_with_theme_id_and_configs_should_be_download_file_correctly(
        self, mock_write_config, mock_open_file
    ):
        self.mock_gateway.return_value.get_templates.return_value.ok = True
        self.mock_gateway.return_value.get_templates.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.get_templates.return_value.json.return_value = [
            {
                "theme": 1234,
                "name": "assets/image.png",
                "content": "",
                "file": "https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png"
            },
            {
                "theme": 1234,
                "name": "layout/base.html",
                "content": "{% load i18n %}\n\n<div class=\"mt-2\">My home page</div>",
                "file": None
            }
        ]
        self.mock_gateway.return_value._request.return_value.content = b'\xc2\x89'

        self.parser.filenames = None
        self.command.checkout(self.parser)

        expected_gateway_calls = [
            call(store=None, apikey=None),
            call().get_templates(theme_id=1234),
            call().get_templates().json(),
            # get image file
            call()._request('GET', 'https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png')
        ]

        self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        # create assets/image.png
        self.assertIn(call(os.path.abspath('assets/image.png'), 'wb'), mock_open_file.mock_calls)
        self.assertIn(call().__enter__().write(b'\xc2\x89'), mock_open_file.mock_calls)

        # create layout/base.html
        self.assertIn(
            call(os.path.abspath('layout/base.html'), 'w', encoding='utf-8'), mock_open_file.mock_calls)
        self.assertIn(call().__enter__().write(
            '{% load i18n %}\n\n<div class="mt-2">My home page</div>'), mock_open_file.mock_calls)

        mock_write_config.assert_called_once()

    #####
    # pull
    #####
    def test_pull_command_without_config_file_should_be_required_api_key_store_and_theme_id(self):
        with self.assertRaises(TypeError) as error:
            self.parser.apikey = None
            self.parser.store = None
            self.parser.theme_id = None
            self.command.pull(self.parser)
        self.assertEqual(
            str(error.exception), '[development] argument -a/--apikey, -s/--store, -t/--theme_id are required.')

    @patch("builtins.open", autospec=True)
    @patch("ntk.command.Config.write_config", autospec=True)
    def test_pull_command_with_configs_and_without_filename_should_be_download_all_files(
        self, mock_write_config, mock_open_file
    ):
        self.mock_gateway.return_value.get_templates.return_value.json.return_value = [
            {
                "theme": 1234,
                "name": "assets/image.png",
                "content": "",
                "file": "https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png"
            },
            {
                "theme": 1234,
                "name": "layout/base.html",
                "content": "{% load i18n %}\n\n<div class=\"mt-2\">My home page</div>",
                "file": None
            }
        ]
        self.mock_gateway.return_value._request.return_value.content = b'\xc2\x89'

        self.parser.filenames = None
        self.command.pull(self.parser)

        expected_gateway_calls = [
            call(store=None, apikey=None),
            call().get_templates(theme_id=1234),
            call().get_templates().json(),
            # get image file
            call()._request('GET', 'https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png')
        ]

        self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        # create assets/image.png
        self.assertIn(call(os.path.abspath('assets/image.png'), 'wb'), mock_open_file.mock_calls)
        self.assertIn(call().__enter__().write(b'\xc2\x89'), mock_open_file.mock_calls)

        # create layout/base.html
        self.assertIn(
            call(os.path.abspath('layout/base.html'), 'w', encoding='utf-8'), mock_open_file.mock_calls)
        self.assertIn(call().__enter__().write(
            '{% load i18n %}\n\n<div class="mt-2">My home page</div>'), mock_open_file.mock_calls)
        mock_write_config.assert_not_called()

    @patch("builtins.open", autospec=True)
    @patch("ntk.command.Config.write_config", autospec=True)
    def test_pull_command_with_configs_and_filenames_should_be_download_only_file_in_filenames(
        self, mock_write_config, mock_open_file
    ):
        self.mock_gateway.return_value.get_template.return_value.ok = True
        self.mock_gateway.return_value.get_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.get_template.return_value.json.return_value = {
            "theme": 1234,
            "name": "assets/image.png",
            "content": "",
            "file": "https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png"
        }
        self.mock_gateway.return_value._request.return_value.content = b'\xc2\x89'

        self.parser.filenames = ["assets/image.png"]
        self.command.pull(self.parser)

        expected_gateway_calls = [
            call(store=None, apikey=None),
            call().get_template(theme_id=1234, template_name='assets/image.png'),
            call().get_template().json(),
            call()._request('GET', 'https://d36qje162qkq4w.cloudfront.net/media/sandbox/themes/5/assets/image.png')
        ]

        self.assertEqual(self.mock_gateway.mock_calls, expected_gateway_calls)

        # create assets/image.png
        self.assertIn(call(os.path.abspath('assets/image.png'), 'wb'), mock_open_file.mock_calls)
        self.assertIn(call().__enter__().write(b'\xc2\x89'), mock_open_file.mock_calls)

        mock_write_config.assert_not_called()

    #####
    # push
    #####
    def test_push_command_without_config_file_should_be_required_api_key_store_and_theme_id(self):
        with self.assertRaises(TypeError) as error:
            self.parser.apikey = None
            self.parser.store = None
            self.parser.theme_id = None
            self.command.push(self.parser)
        self.assertEqual(
            str(error.exception), '[development] argument -a/--apikey, -s/--store, -t/--theme_id are required.')

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    def test_push_command_with_configs_and_without_filenames_should_upload_all_files(
        self, mock_get_accept_files
    ):
        mock_get_accept_files.return_value = [
            f'{os.getcwd()}/layout/base.html',
        ]
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)
        self.parser.filenames = None
        with patch("builtins.open", self.mock_file):
            self.command.push(self.parser)
        expected_call = call().create_or_update_template(
            theme_id=1234,
            template_name='layout/base.html',
            content='{% load i18n %}\n\n<div class="mt-2">My home page</div>',
            files={}
        )
        self.assertIn(expected_call, self.mock_gateway.mock_calls)

    @patch("ntk.command.glob.glob", autospec=True)
    def test_push_command_ignores_invalid_file_extensions_when_filenames_provided(
        self, mock_glob
    ):
        """Push should silently skip files with unrecognised extensions (e.g. .tmp)."""
        valid_file = os.path.abspath('templates/index.html')
        mock_glob.return_value = [valid_file]
        self.command.config.parser_config(self.parser)
        self.parser.filenames = ['templates/index.html', 'templates/index.html.tmp']
        with patch("builtins.open", self.mock_file):
            self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
            self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
                'content-type': 'application/json; charset=utf-8'}
            self.command.push(self.parser)
        # Only the .html file should have been uploaded
        upload_calls = [
            c for c in self.mock_gateway.mock_calls
            if 'create_or_update_template' in str(c) and 'template_name' in str(c)
        ]
        self.assertEqual(len(upload_calls), 1)
        self.assertIn('templates/index.html', str(upload_calls[0]))
        self.assertNotIn('.tmp', str(upload_calls[0]))

    @patch("ntk.command.glob.glob", autospec=True)
    def test_get_accept_files_with_no_filenames_returns_only_glob_matched_files(
        self, mock_glob
    ):
        """_get_accept_files with no filenames should return only files matched by GLOB_PATTERN."""
        from ntk.conf import GLOB_PATTERN
        valid_files = [
            os.path.abspath('templates/index.html'),
            os.path.abspath('assets/style.css'),
            os.path.abspath('assets/logo.png'),
        ]
        # Return valid files on first glob call, empty list for all subsequent pattern calls
        mock_glob.side_effect = [valid_files] + [[] for _ in range(len(GLOB_PATTERN) - 1)]
        result = self.command._get_accept_files([])
        self.assertEqual(result, valid_files)

    @patch("ntk.command.glob.glob", autospec=True)
    def test_get_accept_files_filters_invalid_extensions_from_provided_filenames(
        self, mock_glob
    ):
        """_get_accept_files should exclude filenames that don't match any GLOB_PATTERN."""
        from ntk.conf import GLOB_PATTERN
        valid_file = os.path.abspath('templates/index.html')
        mock_glob.side_effect = [[valid_file]] + [[] for _ in range(len(GLOB_PATTERN) - 1)]
        result = self.command._get_accept_files([
            'templates/index.html',
            'templates/index.html.tmp',
            'assets/style.bak',
        ])
        self.assertEqual(result, [valid_file])

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    def test_push_command_with_filenames_should_upload_only_specified_files(
        self, mock_get_accept_files
    ):
        mock_get_accept_files.return_value = [
            f'{os.getcwd()}/layout/base.html',
        ]
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)
        self.parser.filenames = ['layout/base.html']
        with patch("builtins.open", self.mock_file):
            self.command.push(self.parser)
        expected_call = call().create_or_update_template(
            theme_id=1234,
            template_name='layout/base.html',
            content='{% load i18n %}\n\n<div class="mt-2">My home page</div>',
            files={}
        )
        self.assertIn(expected_call, self.mock_gateway.mock_calls)

    #####
    # watch (_handle_files_change)
    #####
    @patch("ntk.command.Command._get_accept_files", autospec=True)
    def test_watch_command_should_call_gateway_with_correct_arguments_belong_to_files_change(
        self, mock_get_accept_file
    ):
        mock_get_accept_file.return_value = [
            f'{os.getcwd()}/assets/base.html',
            f'{os.getcwd()}/layout/base.html'
        ]
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.status_code = 200
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.mock_gateway.return_value.delete_template.return_value.ok = True
        self.mock_gateway.return_value.delete_template.return_value.status_code = 204
        self.mock_gateway.return_value.delete_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)
        changes = {
            (Change.added, './assets/base.html'),
            (Change.modified, './layout/base.html'),
            (Change.deleted, './layout/base.html'),
        }
        with patch("builtins.open", self.mock_file):
            self.command._handle_files_change(changes)
            content = '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
            # Change.added
            expected_call_added = call().create_or_update_template(
                theme_id=1234, template_name='assets/base.html', content=content, files={})
            self.assertIn(expected_call_added, self.mock_gateway.mock_calls)
            # Change.modified
            expected_call_modified = call().create_or_update_template(
                theme_id=1234, template_name='layout/base.html', content=content, files={})
            self.assertIn(expected_call_modified, self.mock_gateway.mock_calls)
            # Change.deleted
            expected_call_deleted = call().delete_template(
                theme_id=1234, template_name='layout/base.html')
            self.assertIn(expected_call_deleted, self.mock_gateway.mock_calls)

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    @patch("builtins.open", autospec=True)
    def test_watch_command_with_create_image_file_should_call_gateway_with_correct_arguments(
        self, mock_open_file, mock_get_accept_file
    ):
        mock_get_accept_file.return_value = [
            f'{os.getcwd()}/assets/image.jpg',
        ]
        mock_open_file.return_value = mock_img_file = MagicMock()
        self.command.config.parser_config(self.parser)
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        changes = [
            (Change.added, './assets/image.jpg'),
        ]
        self.command._handle_files_change(changes)
        # Change.added image
        expected_call_added = call().create_or_update_template(
            theme_id=1234,
            template_name='assets/image.jpg',
            content='',
            files={'file': ('assets/image.jpg', mock_img_file)}
        )
        self.assertIn(expected_call_added, self.mock_gateway.mock_calls)

    @patch("ntk.command.Command._push_templates", autospec=True)
    def test_watch_logs_and_continues_when_push_raises_ntk_error(self, mock_push_templates):
        """A transient NTKError during watch should be logged, not kill the watcher."""
        from ntk.exceptions import NTKAuthError
        mock_push_templates.side_effect = NTKAuthError('Invalid API key for http://development.com.')
        self.command.config.parser_config(self.parser)
        changes = [
            (Change.modified, './templates/index.html'),
        ]
        # Should not raise — the error is caught inside _handle_files_change.
        with self.assertLogs(level='ERROR') as log:
            self.command._handle_files_change(changes)
        self.assertTrue(
            any('Invalid API key for http://development.com.' in line for line in log.output))

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    @patch("ntk.command.Command._compile_sass", autospec=True)
    def test_watch_command_with_sass_directory_should_call_compile_sass(
        self, mock_get_accept_file, mock_compile_sass
    ):
        mock_get_accept_file.return_value = [
            'sass/theme.scss',
        ]
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}

        changes = {
            (Change.modified, 'sass/theme.scss'),
        }

        with patch("builtins.open", self.mock_file):
            self.command._handle_files_change(changes)
            mock_compile_sass.assert_called_once()

    @patch("ntk.command.asyncio.run")
    @patch("ntk.command.awatch", autospec=True)
    def test_watch_command_uses_asyncio_run(self, mock_awatch, mock_asyncio_run):
        mock_asyncio_run.side_effect = lambda coro: coro.close()
        self.command.config.parser_config(self.parser)
        with patch("os.getcwd", return_value="/fake/path"):
            self.command.watch(self.parser)
        mock_asyncio_run.assert_called_once()

    #####
    # watch (_handle_files_change) - file extension filtering
    #####
    def test_watch_ignores_tmp_files_on_added(self):
        """Temporary files created by editors should be silently ignored."""
        self.command.config.parser_config(self.parser)
        changes = [(Change.added, './assets/js/theme.js.tmp.5.1772698646248')]
        self.command._handle_files_change(changes)
        self.mock_gateway.return_value.create_or_update_template.assert_not_called()

    def test_watch_ignores_tmp_files_on_deleted(self):
        """Temporary files deleted by editors should not trigger a theme delete."""
        self.command.config.parser_config(self.parser)
        changes = [(Change.deleted, './partials/block_cart_footer.html.tmp.5.1772698662671')]
        self.command._handle_files_change(changes)
        self.mock_gateway.return_value.delete_template.assert_not_called()

    def test_watch_ignores_unknown_extensions(self):
        """Files with unrecognised extensions (.bak, .swp, .pyc, .tmp) should be ignored."""
        self.command.config.parser_config(self.parser)
        changes = [
            (Change.added, './assets/style.bak'),
            (Change.modified, './templates/home.swp'),
            (Change.deleted, './layouts/base.pyc'),
            (Change.added, './assets/app.js.tmp'),
        ]
        self.command._handle_files_change(changes)
        self.mock_gateway.return_value.create_or_update_template.assert_not_called()
        self.mock_gateway.return_value.delete_template.assert_not_called()

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    def test_watch_routes_content_extensions_to_push(self, mock_get_accept_files):
        """All content file extensions (.html, .json, .css, .js) should be pushed."""
        content_files = [
            './templates/index.html',
            './configs/settings.json',
            './assets/style.css',
            './assets/app.js',
        ]
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)

        for filepath in content_files:
            self.mock_gateway.reset_mock()
            mock_get_accept_files.return_value = [os.path.abspath(filepath.lstrip('./'))]
            changes = [(Change.added, filepath)]
            with patch("builtins.open", self.mock_file):
                self.command._handle_files_change(changes)
            self.mock_gateway.return_value.create_or_update_template.assert_called_once()

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    @patch("builtins.open", autospec=True)
    def test_watch_routes_media_extensions_to_push(self, mock_open_file, mock_get_accept_files):
        """All media file extensions should be pushed as binary files."""
        media_files = [
            './assets/font.woff2',
            './assets/icon.gif',
            './assets/favicon.ico',
            './assets/photo.png',
            './assets/photo.jpg',
            './assets/photo.jpeg',
            './assets/logo.svg',
            './assets/font.eot',
            './assets/font.tff',
            './assets/font.ttf',
            './assets/font.woff',
            './assets/hero.webp',
            './assets/video.mp4',
            './assets/video.webm',
            './assets/audio.mp3',
            './assets/doc.pdf',
        ]
        mock_open_file.return_value = MagicMock()
        self.mock_gateway.return_value.create_or_update_template.return_value.ok = True
        self.mock_gateway.return_value.create_or_update_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)

        for filepath in media_files:
            self.mock_gateway.reset_mock()
            mock_get_accept_files.return_value = [os.path.abspath(filepath.lstrip('./'))]
            changes = [(Change.added, filepath)]
            self.command._handle_files_change(changes)
            self.mock_gateway.return_value.create_or_update_template.assert_called_once()

    @patch("ntk.command.Command._get_accept_files", autospec=True)
    def test_watch_routes_valid_deleted_files_to_delete(self, mock_get_accept_files):
        """Valid file types that are deleted should trigger a theme delete."""
        self.mock_gateway.return_value.delete_template.return_value.ok = True
        self.mock_gateway.return_value.delete_template.return_value.headers = {
            'content-type': 'application/json; charset=utf-8'}
        self.command.config.parser_config(self.parser)
        mock_get_accept_files.return_value = []

        valid_deleted_files = [
            './templates/index.html',
            './assets/style.css',
            './assets/app.js',
            './configs/settings.json',
            './assets/logo.png',
        ]
        for filepath in valid_deleted_files:
            self.mock_gateway.reset_mock()
            changes = [(Change.deleted, filepath)]
            self.command._handle_files_change(changes)
            self.mock_gateway.return_value.delete_template.assert_called_once()

    #####
    # sass
    #####
    @patch("ntk.command.sass")
    def test_compile_sass_command_error_should_return_log_we_expect(self, mock_sass):
        self.command.config.parser_config(self.parser)
        self.command._compile_sass()

        mock_sass.compile.assert_called_once_with(
            dirname=(conf.SASS_SOURCE, conf.SASS_DESTINATION), output_style='nested')
