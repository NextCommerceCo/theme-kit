import asyncio
import glob
import logging
import os
import sass

from watchfiles import awatch, Change

from ntk.conf import (
    Config, CONTENT_FILE_EXTENSIONS, MEDIA_FILE_EXTENSIONS, GLOB_PATTERN, SASS_DESTINATION, SASS_SOURCE,
    SASS_EXTENSIONS,
)
from ntk.decorator import parser_config
from ntk.exceptions import NTKRequestError
from ntk.gateway import Gateway
from ntk.utils import get_template_name, progress_bar


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
            try:
                if event_type in [Change.added, Change.modified]:
                    logging.info(f'[{self.config.env}] {event_type.name.title()} {template_name}')
                    self._push_templates([template_name], compile_sass=True)
                elif event_type == Change.deleted:
                    logging.info(f'[{self.config.env}] {event_type.name.title()} {template_name}')
                    self._delete_templates([template_name])
            except NTKRequestError as error:
                # Keep watching on a transient failure (network/throttle). Permanent errors
                # (bad key, missing theme) propagate and stop the watcher.
                logging.error(f'[{self.config.env}] {error}')

    def _push_templates(self, template_names, compile_sass=False):
        template_names = self._get_accept_files(template_names)
        template_count = len(template_names)

        logging.info(f'[{self.config.env}] Connecting to {self.config.store}')
        logging.info(f'[{self.config.env}] Uploading {template_count} files to theme id {self.config.theme_id}')

        for template_name in template_names:
            if compile_sass and get_template_name(template_name).split('/')[0] == SASS_SOURCE:
                self._compile_sass()

        for template_name in progress_bar(
                template_names, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50):

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

            response = self.gateway.create_or_update_template(
                theme_id=self.config.theme_id, template_name=relative_pathfile, content=content, files=files)

            if not response.ok:
                return

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
        for template in progress_bar(templates, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50):
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

    def _delete_templates(self, template_names):
        template_count = len(template_names)
        logging.info(f'[{self.config.env}] Connecting to {self.config.store}')
        logging.info(f'[{self.config.env}] Deleting {template_count} files from theme id {self.config.theme_id}')

        for template_name in progress_bar(
                template_names, prefix=f'[{self.config.env}] Progress:', suffix='Complete', length=50):
            template_name = get_template_name(template_name)
            response = self.gateway.delete_template(theme_id=self.config.theme_id, template_name=template_name)
            if not response.ok:
                return

    def _compile_sass(self):
        logging.info(f'[{self.config.env}] Processing {SASS_SOURCE} to {SASS_DESTINATION}.')
        try:
            sass.compile(dirname=(SASS_SOURCE, SASS_DESTINATION), output_style=self.config.sass_output_style)
            logging.info(f'[{self.config.env}] Sass successfully processed.')
        except Exception as error:
            logging.error(f'[{self.config.env}] Sass processing failed, see error below.')
            logging.error(f'[{self.config.env}] {error}')

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
        else:
            logging.warning(f'[{self.config.env}] Missing Themes in {self.config.store}')

    @parser_config()
    def pull(self, parser):
        self._pull_templates(parser.filenames)

    @parser_config(write_file=True)
    def checkout(self, parser):
        self._pull_templates([])

    @parser_config()
    def push(self, parser):
        self._push_templates(parser.filenames or [])

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
