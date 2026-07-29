import logging
import time
import requests
from urllib.parse import urljoin

from ntk.decorator import check_error
from ntk.exceptions import NTKRequestError

MAX_RETRIES = 3
# The store API rate limit is 4 requests/second (250ms apart). Wait 400ms before every
# request to stay under the limit so requests are never throttled.
REQUEST_INTERVAL_SECONDS = 0.4
# Give up on a single request after 30 seconds so a dropped connection fails instead of hanging.
REQUEST_TIMEOUT = 30

# Transport-level failures that are worth retrying rather than surfacing as a raw stack trace.
TRANSIENT_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.SSLError,
)


class Gateway:
    def __init__(self, store, apikey):
        self.store = store
        self.apikey = apikey

    def _request(self, request_type, url, apikey=None, payload={}, files={}):
        headers = {'Authorization': f'Bearer {apikey}'} if apikey else {}

        reason = 'connection failed'
        for attempt in range(MAX_RETRIES):
            # Space every request (and retry) to stay under the store rate limit.
            time.sleep(REQUEST_INTERVAL_SECONDS)
            try:
                response = requests.request(
                    request_type, url, headers=headers, data=payload, files=files, timeout=REQUEST_TIMEOUT)
            except TRANSIENT_EXCEPTIONS as error:
                reason = 'timed out' if isinstance(error, requests.exceptions.Timeout) else 'connection failed'
            else:
                if not (response.status_code == 429 and "throttled" in response.content.decode()):
                    return response
                reason = 'throttled'

            logging.warning(f'Request to {self.store} {reason} (attempt {attempt + 1}/{MAX_RETRIES}).')

        raise NTKRequestError(f'Request to {self.store} failed after {MAX_RETRIES} attempts ({reason}).')

    @check_error(error_format='Missing Themes in {store}')
    def get_themes(self):
        api_path = '/api/admin/themes/'
        url = urljoin(self.store, api_path)

        return self._request("GET", url, apikey=self.apikey)

    @check_error(error_format='Theme "{name}" creation failed.{error_msg}')
    def create_theme(self, name):
        api_path = '/api/admin/themes/'
        url = urljoin(self.store, api_path)

        payload = dict(name=name)

        return self._request("POST", url, apikey=self.apikey, payload=payload)

    @check_error(error_format='Downloading {template_name} file from theme id #{theme_id} failed.{error_msg}')
    def get_template(self, theme_id, template_name):
        api_path = f"/api/admin/themes/{theme_id}/templates/?name={template_name}"
        url = urljoin(self.store, api_path)

        return self._request("GET", url, apikey=self.apikey)

    @check_error(error_format='Downloading templates files from theme id #{theme_id} failed.{error_msg}')
    def get_templates(self, theme_id):
        api_path = f"/api/admin/themes/{theme_id}/templates/"
        url = urljoin(self.store, api_path)

        return self._request("GET", url, apikey=self.apikey)

    @check_error(error_format='Uploading {template_name} file to theme id #{theme_id} failed.{error_msg}')
    def create_or_update_template(self, theme_id, template_name, content=None, files=None):
        api_path = f"/api/admin/themes/{theme_id}/templates/"
        url = urljoin(self.store, api_path)

        payload = dict(
            name=template_name,
            content=content
        )

        return self._request("POST", url, apikey=self.apikey, payload=payload, files=files)

    @check_error(error_format='Deleting {template_name} file from theme id #{theme_id} failed.{error_msg}',
                 response_json=False)
    def delete_template(self, theme_id, template_name):
        api_path = f"/api/admin/themes/{theme_id}/templates/?name={template_name}"
        url = urljoin(self.store, api_path)

        return self._request("DELETE", url, apikey=self.apikey)
