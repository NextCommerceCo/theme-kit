import argparse

from ntk.command import Command


class Parser:
    def __init__(self):
        self.command = Command()

    def _add_config_arguments(self, parser):
        parser.add_argument('-a', '--apikey', action="store", dest="apikey", help=argparse.SUPPRESS)
        parser.add_argument('-s', '--store', action="store", dest="store", help=argparse.SUPPRESS)
        parser.add_argument('-t', '--theme_id', action="store", type=int, dest="theme_id", help=argparse.SUPPRESS)
        parser.add_argument('-e', '--env', action="store", dest="env", default='development', help=argparse.SUPPRESS)
        parser.add_argument(
            '-sos', '--sass_output_style', action="store", dest="sass_output_style", help=argparse.SUPPRESS)
        parser.add_argument('--json', action='store_true', help='Write one stable JSON result to stdout')
        parser.add_argument('--quiet', action='store_true', help='Suppress informational diagnostics')
        parser.add_argument('--no-progress', action='store_true', help='Disable interactive progress output')

    def create_parser(self):
        option_commands = '''
options:
    -a, --apikey                 API Key used to connect to the store
    -s, --store                  Full domain of the store
    -t, --theme_id               ID of the theme
    -e, --env                    Environment to run the command (default [development])
    -sos, --sass_output_style    Specify Sass output style: nested, expanded, compact, or compressed'''

        # create the top-level parser
        parser = argparse.ArgumentParser(
            description='''
Usage:
    ntk [command] [options]

available commands:
    init         Initialize a new theme, will create the theme on the store and config.yml file
    list         List all available themes on the store
    checkout     Pull theme from the store into your current directory and create config.yml
    pull         Pull theme from the store into your current directory
    push         Push all theme files from your current direcotry to the store
    watch        Watch for changes in your current directory and push updates to the store
    sass         Process Sass files to CSS files in assets directory
    validate     Validate theme files locally or against the store
    capture      Capture deterministic desktop and mobile screenshots
''' + option_commands,
            usage=argparse.SUPPRESS,
            epilog='Use "ntk [command] --help" for more information about a command.',
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=argparse.SUPPRESS
        )
        subparsers = parser.add_subparsers(
            title='Available Commands', help=argparse.SUPPRESS, dest='command')

        # create the parser for the "init" command
        parser_init = subparsers.add_parser(
            'init',
            help='init',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk init [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_init.set_defaults(func=self.command.init)
        self._add_config_arguments(parser_init)
        parser_init.add_argument('-n', '--name', action="store", dest="name", help=argparse.SUPPRESS)

        # create the parser for the "list" command
        parser_list = subparsers.add_parser(
            'list',
            help='List all themes installed on the theme.',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk list [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_list.set_defaults(func=self.command.list)
        self._add_config_arguments(parser_list)

        # create the parser for the "checkout" command
        parser_checkout = subparsers.add_parser(
            'checkout',
            help='Download a specific theme',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk checkout [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_checkout.set_defaults(func=self.command.checkout)
        self._add_config_arguments(parser_checkout)

        # create the parser for the "pull" command
        parser_pull = subparsers.add_parser(
            'pull',
            help='Download a specific theme',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk pull [options] [Filename ...]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_pull.set_defaults(func=self.command.pull)
        parser_pull.add_argument('filenames', metavar='filenames', type=str, nargs='*', help=argparse.SUPPRESS)
        self._add_config_arguments(parser_pull)

        # create the parser for the "push" command
        parser_push = subparsers.add_parser(
            'push',
            help='Download a specific theme',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk push [options] [Filename ...]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_push.set_defaults(func=self.command.push)
        parser_push.add_argument('filenames', metavar='filenames', type=str, nargs='*', help=argparse.SUPPRESS)
        self._add_config_arguments(parser_push)

        # create the parser for the "watch" command
        parser_watch = subparsers.add_parser(
            'watch',
            help='Push updates to your theme',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk watch [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_watch.set_defaults(func=self.command.watch)
        self._add_config_arguments(parser_watch)

        # create the parser for the "sass" command
        parser_sass = subparsers.add_parser(
            'sass',
            help='Compile scss to css on your theme',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk sass [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_sass.set_defaults(func=self.command.compile_sass)
        self._add_config_arguments(parser_sass)

        parser_validate = subparsers.add_parser(
            'validate',
            help='Validate theme files',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk validate [options] [Filename ...]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_validate.set_defaults(func=self.command.validate)
        parser_validate.add_argument('filenames', metavar='filenames', type=str, nargs='*', help=argparse.SUPPRESS)
        parser_validate.add_argument(
            '--server', action='store_true', help='Validate valid local text files with the store API')
        self._add_config_arguments(parser_validate)

        parser_capture = subparsers.add_parser(
            'capture',
            help='Capture deterministic storefront screenshots',
            usage=argparse.SUPPRESS,
            description='''
Usage:
    ntk capture --url /path --output qa-output [options]
''' + option_commands,
            formatter_class=argparse.RawTextHelpFormatter)
        parser_capture.set_defaults(func=self.command.capture)
        parser_capture.add_argument('--url', required=True, help='Storefront route or absolute URL')
        parser_capture.add_argument('--output', required=True, help='Directory for PNG screenshots')
        parser_capture.add_argument(
            '--viewports', default='desktop,mobile', help='Comma-separated desktop,mobile viewports')
        parser_capture.add_argument(
            '--settle-timeout', type=int, default=30000,
            help='Milliseconds to wait for navigation, fonts, lazy media, and images')
        self._add_config_arguments(parser_capture)
        return parser
