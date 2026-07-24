import requests
from urllib.parse import urljoin

from ntk.decorator import check_error


class Gateway:
    def __init__(self, store, apikey):
        self.store = store
        self.apikey = apikey

    def _request(self, request_type, url, apikey=None, payload={}, files={}):
        headers = {}
        if apikey:
            headers = {'Authorization': f'Bearer {apikey}'}

        try:
            response = requests.request(request_type, url, headers=headers, data=payload, files=files)
        except requests.exceptions.ConnectionError:
            return self._request(request_type, url, apikey, payload, files)
        if response.status_code == 429 and "throttled" in response.content.decode():
            return self._request(request_type, url, apikey, payload, files)
        return response

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
