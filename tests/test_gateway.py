import unittest
from unittest.mock import call, MagicMock, patch

import requests

from ntk.exceptions import NTKAuthError, NTKConnectionError, NTKNotFoundError
from ntk.gateway import Gateway, MAX_RETRIES


class TestGateway(unittest.TestCase):
    def setUp(self):
        self.store = 'http://simple.com'
        self.apikey = 'apikey'

        self.gateway = Gateway(self.store, self.apikey)
        self.mock_img_file = MagicMock()

    #####
    # _request
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request(self, mock_request):
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_request.return_value = mock_response_200

        request_type = 'POST'
        url = 'http://simple.com/api/admin/themes/5/templates/'
        payload = {
            'name': 'assets/base.html',
            'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
        }
        files = {'file': ('assets/image.jpg', self.mock_img_file)}

        self.gateway._request(request_type, url, apikey=self.apikey, payload=payload, files=files)

        expected_calls = [
            call(
                'POST', 'http://simple.com/api/admin/themes/5/templates/',
                headers={'Authorization': 'Bearer apikey'},
                data={
                    'name': 'assets/base.html', 'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'},
                files=files)
        ]
        assert mock_request.mock_calls == expected_calls

    @patch('ntk.gateway.time.sleep', autospec=True)
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_with_rate_limit_should_retry(self, mock_request, mock_sleep):
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.content.decode.return_value = "throttled"

        # Mock the response for the second call with status code 200
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_request.side_effect = [mock_response_429, mock_response_200]

        request_type = 'POST'
        url = 'http://simple.com/api/admin/themes/5/templates/'
        payload = {
            'name': 'assets/base.html',
            'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
        }
        files = {'file': ('assets/image.jpg', self.mock_img_file)}

        self.gateway._request(request_type, url, apikey=self.apikey, payload=payload, files=files)

        assert mock_request.call_count == 2

        expected_calls = [
            call(
                'POST', 'http://simple.com/api/admin/themes/5/templates/',
                headers={'Authorization': 'Bearer apikey'},
                data={
                    'name': 'assets/base.html', 'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
                }, files=files),
            call(
                'POST', 'http://simple.com/api/admin/themes/5/templates/',
                headers={'Authorization': 'Bearer apikey'},
                data={
                    'name': 'assets/base.html', 'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
                }, files=files)
        ]
        assert mock_request.mock_calls == expected_calls

    @patch('ntk.gateway.time.sleep', autospec=True)
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_rate_limit_gives_up_after_max_retries(self, mock_request, mock_sleep):
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.content.decode.return_value = "throttled"

        mock_request.return_value = mock_response_429

        response = self.gateway._request('GET', 'http://simple.com/api/admin/themes/', apikey=self.apikey)

        assert mock_request.call_count == MAX_RETRIES
        assert response is mock_response_429

    @patch('ntk.gateway.time.sleep', autospec=True)
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_retries_transient_error_then_succeeds(self, mock_request, mock_sleep):
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_request.side_effect = [requests.exceptions.ConnectionError(), mock_response_200]

        response = self.gateway._request('GET', 'http://simple.com/api/admin/themes/', apikey=self.apikey)

        assert mock_request.call_count == 2
        assert response is mock_response_200

    @patch('ntk.gateway.time.sleep', autospec=True)
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_raises_after_persistent_transient_error(self, mock_request, mock_sleep):
        # A Timeout is one of the broadened transient exceptions that should be retried, not surfaced raw.
        mock_request.side_effect = requests.exceptions.Timeout()

        with self.assertRaises(NTKConnectionError):
            self.gateway._request('GET', 'http://simple.com/api/admin/themes/', apikey=self.apikey)

        assert mock_request.call_count == MAX_RETRIES

    #####
    # 401 / 404 handling (check_error decorator)
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_401_raises_auth_error(self, mock_request):
        mock_request.return_value.status_code = 401

        with self.assertRaises(NTKAuthError) as error:
            self.gateway.get_themes()

        self.assertEqual(str(error.exception), 'Invalid API key for http://simple.com.')

    @patch('ntk.gateway.requests.request', autospec=True)
    def test_request_404_raises_not_found_error_with_url(self, mock_request):
        mock_request.return_value.status_code = 404
        mock_request.return_value.url = 'http://simple.com/api/admin/themes/6/templates/'

        with self.assertRaises(NTKNotFoundError) as error:
            self.gateway.get_templates(theme_id=6)

        self.assertIn('http://simple.com/api/admin/themes/6/templates/', str(error.exception))

    #####
    # get_themes
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_get_themes(self, mock_request):
        # check if call request failed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'text/html'}

        with self.assertLogs(level='INFO') as log:
            self.gateway.get_themes()

        expected_logging = [
            'INFO:root:Missing Themes in http://simple.com'
        ]
        self.assertEqual(log.output, expected_logging)

        # check if call request completed
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}
        self.gateway.get_themes()

        expected_call = call('GET', 'http://simple.com/api/admin/themes/',
                             headers={'Authorization': 'Bearer apikey'}, data={}, files={})
        self.assertIn(expected_call, mock_request.mock_calls)

    ####
    # create_theme
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_create_theme(self, mock_request):
        # check if call request failed
        mock_request.return_value.headers = {'content-type': 'text/html'}

        with self.assertLogs(level='INFO') as log:
            self.gateway.create_theme(name="Test Init Theme")

        expected_logging = [
            'INFO:root:Theme "Test Init Theme" creation failed.'
        ]
        self.assertEqual(log.output, expected_logging)

        # check if call request completed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}
        payload = {
            "name": "Test Init Theme"
        }
        self.gateway.create_theme(name="Test Init Theme")

        expected_call = call('POST', 'http://simple.com/api/admin/themes/',
                             headers={'Authorization': 'Bearer apikey'}, data=payload, files={})
        self.assertIn(expected_call, mock_request.mock_calls)

    #####
    # get_templates
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_get_templates(self, mock_request):
        # check if call request failed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'text/html'}

        with self.assertLogs(level='INFO') as log:
            self.gateway.get_templates(theme_id=6)

        expected_logging = [
            'INFO:root:Downloading templates files from theme id #6 failed.'
        ]
        self.assertEqual(log.output, expected_logging)

        # check if call request completed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}

        self.gateway.get_templates(theme_id=6)

        expected_call = call('GET', 'http://simple.com/api/admin/themes/6/templates/',
                             headers={'Authorization': 'Bearer apikey'}, data={}, files={})
        self.assertIn(expected_call, mock_request.mock_calls)

    #####
    # get_template
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_get_template(self, mock_request):
        template_name = 'assets/custom.css'
        # check if call request failed
        with self.assertLogs(level='INFO') as log:
            mock_request.return_value.ok = False
            mock_request.return_value.json.return_value = {
                'detail': 'You do not have permission to perform this action.'}
            self.gateway.get_template(theme_id=6, template_name=template_name)

        expected_logging = [
            'INFO:root:Downloading assets/custom.css file from theme id #6 failed. -> You do not have permission to perform this action.' # noqa
        ]
        self.assertEqual(log.output, expected_logging)

        # check if call request completed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}

        self.gateway.get_template(theme_id=6, template_name=template_name)

        expected_call = call('GET', f'http://simple.com/api/admin/themes/6/templates/?name={template_name}',
                             headers={'Authorization': 'Bearer apikey'}, data={}, files={})
        self.assertIn(expected_call, mock_request.mock_calls)

    #####
    # create_or_update_template
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_create_or_update_template(self, mock_request):
        # check if call request failed
        with self.assertLogs(level='INFO') as log:
            mock_request.return_value.ok = False
            mock_request.return_value.json.return_value = {
                'detail': 'You do not have permission to perform this action.'}
            self.gateway.create_or_update_template(theme_id=6, template_name='asset/custom.css')

        expected_logging = [
            'INFO:root:Uploading asset/custom.css file to theme id #6 failed. -> You do not have permission to perform this action.' # noqa
        ]
        print(log.output)
        self.assertEqual(log.output, expected_logging)

        # check if call request completed
        mock_request.return_value.ok = True
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}
        payload = {
            'name': 'assets/base.html',
            'content': '{% load i18n %}\n\n<div class="mt-2">My home page</div>'
        }
        files = {'file': ('assets/image.jpg', self.mock_img_file)}

        self.gateway.create_or_update_template(
            theme_id=6, template_name=payload['name'], content=payload['content'], files=files)

        expected_call = call('POST', 'http://simple.com/api/admin/themes/6/templates/',
                             headers={'Authorization': 'Bearer apikey'}, data=payload, files=files)
        self.assertIn(expected_call, mock_request.mock_calls)

    #####
    # delete_template
    #####
    @patch('ntk.gateway.requests.request', autospec=True)
    def test_delete_template(self, mock_request):
        mock_request.return_value.headers = {'content-type': 'application/json; charset=utf-8'}
        # check if call request failed
        with self.assertLogs(level='INFO') as log:
            mock_request.return_value.ok = False
            mock_request.return_value.json.return_value = {
                'name': ['This field is required.', 'Please enter filenames.']
            }
            self.gateway.delete_template(theme_id=6, template_name='asset/custom.css')

        expected_logging = [
            'INFO:root:Deleting asset/custom.css file from theme id #6 failed. -> "name" : '
            'This field is required. Please enter filenames.'
        ]
        self.assertEqual(log.output, expected_logging)

        # check if call request complated
        mock_request.return_value.ok = True
        self.gateway.delete_template(theme_id=6, template_name='asset/custom.css')

        expected_call = call('DELETE', 'http://simple.com/api/admin/themes/6/templates/?name=asset/custom.css',
                             headers={'Authorization': 'Bearer apikey'}, data={}, files={})
        self.assertIn(expected_call, mock_request.mock_calls)
