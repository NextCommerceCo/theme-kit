import asyncio
import glob
import importlib
import logging
import os
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from watchfiles import awatch, Change

from ntk.conf import (
    Config, CONTENT_FILE_EXTENSIONS, MEDIA_FILE_EXTENSIONS, GLOB_PATTERN, SASS_DESTINATION, SASS_SOURCE,
    SASS_EXTENSIONS,
)
from ntk.decorator import parser_config
from ntk.gateway import Gateway
from ntk.output import Output
from ntk.utils import get_template_name, progress_bar
from ntk.validation import validate_local_file


# Kept as an injectable seam for tests. The native dependency is imported only
# when the Sass command actually runs.
sass = None


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('watchfiles').setLevel(logging.WARNING)


class Command:
    def __init__(self):
        self.config = Config()
        self.gateway = Gateway(store=self.config.store, apikey=self.config.apikey)
        self.output = Output()

    def _get_accept_files(self, template_names):
        files = []
        glob_list = map(lambda x: os.path.abspath(x), GLOB_PATTERN)
        for pattern in glob_list:
            files.extend(glob.glob(pattern, recursive=True))

        if template_names:
            filenames = list(map(lambda x: os.path.abspath(x), template_names))
            template_names = list(filter(lambda x: x in files, filenames))
        else:
            template_names = files

        return template_names

    def _handle_files_change(self, changes):
        valid_extensions = tuple(CONTENT_FILE_EXTENSIONS + MEDIA_FILE_EXTENSIONS + SASS_EXTENSIONS)
        for event_type, pathfile in changes:
            if not pathfile.endswith(valid_extensions):
                continue
            template_name = get_template_name(pathfile)
            if event_type in [Change.added, Change.modified]:
                logging.info(f'[{self.config.env}] {event_type.name.title()} {template_name}')
                self._push_templates([template_name], compile_sass=True)
            elif event_type == Change.deleted:
                logging.info(f'[{self.config.env}] {event_type.name.title()} {template_name}')
                self._delete_templates([template_name])

    def _push_templates(self, template_names, compile_sass=False):
        requested = list(template_names or [])
        template_names = self._get_accept_files(template_names)
        template_count = len(template_names)

        logging.info(f'[{self.config.env}] Connecting to {self.config.store}')
        logging.info(f'[{self.config.env}] Uploading {template_count} files to theme id {self.config.theme_id}')

        for template_name in template_names:
            if compile_sass and get_template_name(template_name).split('/')[0] == SASS_SOURCE:
                self._compile_sass()

        results = []
        accepted = {os.path.abspath(name) for name in template_names}
        for requested_name in requested:
            if os.path.abspath(requested_name) not in accepted:
                results.append({
                    'path': get_template_name(requested_name),
                    'status': 'rejected',
                    'reason': 'unsupported extension or file not found',
                })

        for template_name in progress_bar(
                template_names, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50,
                enabled=self.output.progress_enabled):

            relative_pathfile = get_template_name(template_name)
            template_name = get_template_name(template_name)

            files = {}
            content = ''
            if relative_pathfile.endswith(tuple(MEDIA_FILE_EXTENSIONS)):
                files = {'file': (relative_pathfile, open(relative_pathfile, 'rb'))}
            else:
                with open(relative_pathfile, "r", encoding="utf-8") as f:
                    content = f.read()
                    f.close()

            try:
                response = self.gateway.create_or_update_template(
                    theme_id=self.config.theme_id, template_name=relative_pathfile, content=content, files=files)
            finally:
                if files:
                    files['file'][1].close()

            time.sleep(0.07)
            if not response.ok:
                results.append({
                    'path': relative_pathfile,
                    'status': 'failed',
                    'status_code': response.status_code,
                })
                continue
            results.append({'path': relative_pathfile, 'status': 'uploaded'})
        return results

    def _pull_templates(self, template_names):
        templates = []
        if template_names:
            for filename in template_names:
                template_name = get_template_name(filename)
                response = self.gateway.get_template(theme_id=self.config.theme_id, template_name=template_name)
                templates.append(response.json())
        else:
            response = self.gateway.get_templates(theme_id=self.config.theme_id)
            templates = response.json()

        if not isinstance(templates, list):
            return

        template_count = len(templates)
        logging.info(f'[{self.config.env}] Connecting to {self.config.store}')
        logging.info(f'[{self.config.env}] Pulling {template_count} files from theme id {self.config.theme_id} ')
        current_files = []
        results = []
        for template in progress_bar(
                templates, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50,
                enabled=self.output.progress_enabled):
            template_name = str(template['name'])
            current_pathfile = os.path.abspath(template_name)
            current_files.append(current_pathfile.replace('\\', '/'))

            # create directories
            dirs = os.path.dirname(current_pathfile)
            if not os.path.exists(dirs):
                os.makedirs(dirs)

            # write file
            if template['file']:
                response = self.gateway._request("GET", template['file'])
                with open(current_pathfile, "wb") as media_file:
                    media_file.write(response.content)
                    media_file.close()
            else:
                with open(current_pathfile, "w", encoding="utf-8") as template_file:
                    template_file.write(template.get('content'))
                    template_file.close()

            time.sleep(0.08)
            results.append({'path': template_name, 'status': 'downloaded'})
        return results

    def _delete_templates(self, template_names):
        template_count = len(template_names)
        logging.info(f'[{self.config.env}] Connecting to {self.config.store}')
        logging.info(f'[{self.config.env}] Deleting {template_count} files from theme id {self.config.theme_id}')

        results = []
        for template_name in progress_bar(
                template_names, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50,
                enabled=self.output.progress_enabled):
            template_name = get_template_name(template_name)
            response = self.gateway.delete_template(theme_id=self.config.theme_id, template_name=template_name)
            if not response.ok:
                results.append({'path': template_name, 'status': 'failed', 'status_code': response.status_code})
                continue
            results.append({'path': template_name, 'status': 'deleted'})
        return results

    def _compile_sass(self):
        logging.info(f'[{self.config.env}] Processing {SASS_SOURCE} to {SASS_DESTINATION}.')
        compiler = sass
        if compiler is None:
            try:
                compiler = importlib.import_module('sass')
            except ImportError as error:
                raise NTKError(
                    'Sass support is optional. Install next_theme_kit[sass] to use `ntk sass`.'
                ) from error
        try:
            compiler.compile(dirname=(SASS_SOURCE, SASS_DESTINATION), output_style=self.config.sass_output_style)
            logging.info(f'[{self.config.env}] Sass successfully processed.')
        except Exception as error:
            raise NTKError(f'[{self.config.env}] Sass processing failed: {error}') from error

    @parser_config(theme_id_required=False)
    def init(self, parser):
        if parser.name:
            response = self.gateway.create_theme(name=parser.name)
            theme = response.json()
            if theme and theme.get('id'):
                self.config.theme_id = theme['id']
                self.config.save()
                logging.info(
                    f'[{self.config.env}] Theme [{theme["id"]}] "{theme["name"]}" has been created successfully.')
                return self.output.result('init', theme=theme)
        else:
            raise TypeError(f'[{self.config.env}] argument -n/--name is required.')

    @parser_config(theme_id_required=False)
    def list(self, parser):
        response = self.gateway.get_themes()
        themes = response.json()
        if themes and themes.get('results'):
            logging.info(f'[{self.config.env}] Available themes:')
            for theme in themes['results']:
                theme_active = " (Active)" if theme.get("active") else ""
                logging.info(f'[{self.config.env}] \t[{theme.get("id")}] \t{theme.get("name")}{theme_active}')
            return self.output.result('list', themes=themes['results'], count=len(themes['results']))
        else:
            logging.warning(f'[{self.config.env}] Missing Themes in {self.config.store}')
            return self.output.result('list', themes=[], count=0)

    @parser_config()
    def pull(self, parser):
        results = self._pull_templates(parser.filenames)
        return self.output.result('pull', results=results, count=len(results))

    @parser_config(write_file=True)
    def checkout(self, parser):
        results = self._pull_templates([])
        return self.output.result('checkout', results=results, count=len(results))

    @parser_config()
    def push(self, parser):
        results = self._push_templates(parser.filenames or [])
        ok = all(item['status'] == 'uploaded' for item in results)
        return self.output.result('push', ok=ok, results=results, count=len(results))

    @parser_config()
    def watch(self, parser):
        current_pathfile = os.path.abspath(".")

        logging.info(f'[{self.config.env}] Current store {self.config.store}')
        logging.info(f'[{self.config.env}] Current theme id {self.config.theme_id}')
        logging.info(f'[{self.config.env}] Preview theme URL {self.config.store}?preview_theme={self.config.theme_id}')
        logging.info(f'[{self.config.env}] Watching for file changes in {current_pathfile}')
        logging.info(f'[{self.config.env}] Press Ctrl + C to stop')

        async def main():
            async for changes in awatch('.'):
                self._handle_files_change(changes)

        asyncio.run(main())

    @parser_config()
    def compile_sass(self, parser):
        logging.info(f'[{self.config.env}] Sass output style {self.config.sass_output_style}.')
        self._compile_sass()
        return self.output.result('sass', output=SASS_DESTINATION)

    @parser_config(apikey_required=False, store_required=False, theme_id_required=False)
    def validate(self, parser):
        if parser.server and (not self.config.store or not self.config.apikey or not self.config.theme_id):
            raise TypeError(
                '`ntk validate --server` requires -a/--apikey, -s/--store, and -t/--theme_id.'
            )
        requested = list(parser.filenames or [])
        paths = self._get_accept_files(requested)
        accepted = {os.path.abspath(path) for path in paths}
        results = []
        for requested_name in requested:
            if os.path.abspath(requested_name) not in accepted:
                results.append({
                    'path': get_template_name(requested_name),
                    'status': 'invalid',
                    'errors': ['unsupported extension or file not found'],
                })
        for path in paths:
            result = validate_local_file(path)
            if parser.server and result['status'] == 'valid' and result.get('content') is not None:
                response = self.gateway.validate_template(
                    theme_id=self.config.theme_id,
                    template_name=result['path'],
                    content=result['content'],
                )
                if not response.ok:
                    result['status'] = 'invalid'
                    result['errors'] = response.json() if response.headers.get(
                        'content-type', '').startswith('application/json') else [response.text]
            result.pop('content', None)
            results.append(result)
        ok = bool(results) and all(item['status'] == 'valid' for item in results)
        return self.output.result(
            'validate', ok=ok, mode='server' if parser.server else 'local', results=results, count=len(results)
        )

    @parser_config(apikey_required=False, theme_id_required=False)
    def capture(self, parser):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise NTKError(
                'Capture support is optional. Install next_theme_kit[capture] and run `playwright install chromium`.'
            ) from error

        split_url = urlsplit(urljoin(f'{self.config.store}/', parser.url.lstrip('/')))
        query = dict(parse_qsl(split_url.query, keep_blank_values=True))
        if self.config.theme_id and 'preview_theme' not in query:
            query['preview_theme'] = str(self.config.theme_id)
        capture_url = urlunsplit((
            split_url.scheme, split_url.netloc, split_url.path, urlencode(query), split_url.fragment
        ))
        viewports = {
            'desktop': {'width': 1440, 'height': 1000},
            'mobile': {'width': 390, 'height': 844},
        }
        requested_viewports = [item.strip() for item in parser.viewports.split(',') if item.strip()]
        unknown = [item for item in requested_viewports if item not in viewports]
        if unknown:
            raise TypeError(f'Unknown viewport(s): {", ".join(unknown)}')
        os.makedirs(parser.output, exist_ok=True)
        results = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for name in requested_viewports:
                    viewport = viewports[name]
                    page = browser.new_page(viewport=viewport)
                    page.goto(capture_url, wait_until='networkidle', timeout=parser.settle_timeout)
                    page.evaluate("document.fonts && document.fonts.ready")
                    page.evaluate("""
                        async () => {
                          for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
                            window.scrollTo(0, y);
                            await new Promise(resolve => setTimeout(resolve, 50));
                          }
                          window.scrollTo(0, 0);
                        }
                    """)
                    page.wait_for_function(
                        "[...document.images].every(image => image.complete)", timeout=parser.settle_timeout
                    )
                    output_path = os.path.abspath(os.path.join(parser.output, f'{name}.png'))
                    page.screenshot(path=output_path, full_page=True)
                    results.append({
                        'viewport': name,
                        'width': viewport['width'],
                        'height': viewport['height'],
                        'path': output_path,
                        'status': 'captured',
                    })
                    page.close()
            finally:
                browser.close()
        return self.output.result('capture', url=capture_url, results=results, count=len(results))
