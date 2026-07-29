
import logging
import os
from urllib.parse import urlparse
import yaml

CONFIG_FILE_NAME = './config.yml'
CONFIG_FILE = os.path.abspath(CONFIG_FILE_NAME)

CONTENT_FILE_EXTENSIONS = ['.html', '.json', '.css', '.js']
MEDIA_FILE_EXTENSIONS = [
    '.woff2', '.gif', '.ico', '.png', '.jpg', '.jpeg', '.svg', '.eot', '.tff', '.ttf', '.woff',
    '.webp', '.mp4', '.webm', '.mp3', '.pdf',
]

SASS_EXTENSIONS = ['.scss']

SASS_SOURCE = 'sass'
SASS_DESTINATION = 'assets'
SASS_OUTPUT_STYLES = ['nested', 'expanded', 'compact', 'compressed']

GLOB_PATTERN = [
    "assets/**/*.html",
    "assets/**/*.json",
    "assets/**/*.css",
    "assets/**/*.scss",
    "assets/**/*.js",

    "assets/**/*.woff2",
    "assets/**/*.gif",
    "assets/**/*.ico",
    "assets/**/*.png",
    "assets/**/*.jpg",
    "assets/**/*.jpeg",
    "assets/**/*.svg",
    "assets/**/*.eot",
    "assets/**/*.tff",
    "assets/**/*.ttf",
    "assets/**/*.woff",
    "assets/**/*.webp",
    "assets/**/*.mp4",
    "assets/**/*.webm",
    "assets/**/*.mp3",
    "assets/**/*.pdf",
    "checkout/**/*.html",
    "configs/**/*.json",
    "layouts/**/*.html",
    "partials/**/*.html",
    "templates/**/*.html",
    "locales/**/*.json",

    f"{SASS_SOURCE}/**/*.scss",
]


class Config(object):
    apikey = None
    store = None
    theme_id = None
    sass_output_style = None

    env = 'development'

    apikey_required = True
    store_required = True
    theme_id_required = True

    def __init__(self, **kwargs):
        self.read_config()
        for name, value in kwargs.items():
            setattr(self, name, value)

    def parser_config(self, parser, write_file=False):
        self.env = parser.env
        self.read_config()
        if getattr(parser, 'apikey', None):
            self.apikey = parser.apikey

        if getattr(parser, 'theme_id', None):
            self.theme_id = parser.theme_id

        if getattr(parser, 'store', None):
            self.store = parser.store

        if getattr(parser, 'sass_output_style', None):
            self.sass_output_style = parser.sass_output_style

        self.save(write_file)

    def validate_config(self):
        error_msgs = []
        if self.apikey_required and not self.apikey:
            error_msgs.append('-a/--apikey')
        if self.store_required and not self.store:
            error_msgs.append('-s/--store')
        if self.theme_id_required and not self.theme_id:
            error_msgs.append('-t/--theme_id')
        if error_msgs:
            message = ', '.join(error_msgs)
            pluralize = 'is' if len(error_msgs) == 1 else 'are'
            raise TypeError(f'[{self.env}] argument {message} {pluralize} required.')

        if self.store:
            self.store = self.normalize_store(self.store)

        if self.sass_output_style and self.sass_output_style not in SASS_OUTPUT_STYLES:
            raise TypeError(
                f'[{self.env}] argument -sos/--sass_output_style is unsupported '
                'output_style; choose one of nested, expanded, compact, and compressed')

        return True

    @staticmethod
    def normalize_store(store):
        store = store.strip().rstrip('/')
        if '://' not in store:
            store = f'https://{store}'
        parsed = urlparse(store)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path not in ('', '/'):
            raise TypeError(
                'Store must be an absolute http(s) origin, for example https://store.example.com.'
            )
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise TypeError(
                'Store must be an absolute http(s) origin, for example https://store.example.com.'
            )
        return f'{parsed.scheme}://{parsed.netloc}'

    def read_config(self, update=True):
        configs = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as yamlfile:
                configs = yaml.load(yamlfile, Loader=yaml.FullLoader)
                yamlfile.close()
            if configs and configs.get(self.env) and update:
                self.apikey = configs[self.env].get('apikey')
                self.store = configs[self.env].get('store')
                self.theme_id = configs[self.env].get('theme_id')
                if configs[self.env].get('sass'):
                    self.sass_output_style = configs[self.env]['sass'].get('output_style')

        return configs

    def write_config(self):
        configs = self.read_config(update=False)

        new_config = {
            'apikey': self.apikey,
            'store': self.store,
            'theme_id': self.theme_id,
            'sass': {
                'output_style': self.sass_output_style or 'nested'  # default sass output style is nested
            }
        }
        # If the config has been changed, then the config will be saved to config.yml.
        if configs.get(self.env) != new_config:
            configs[self.env] = new_config
            with open(CONFIG_FILE, 'w') as yamlfile:
                yaml.dump(configs, yamlfile)
                yamlfile.close()
            logging.info(f'[{self.env}] Configuration was updated.')

    def save(self, write_file=True):
        if self.validate_config() and write_file:
            self.write_config()
