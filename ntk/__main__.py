#!/usr/bin/env python
import logging
import sys

from requests.exceptions import HTTPError

from ntk.exceptions import NTKError
from ntk.ntk_parser import Parser
from ntk.output import Output

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def main():
    parser = Parser().create_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        if isinstance(result, dict) and not result.get('ok', True):
            sys.exit(1)
    except AttributeError:
        print('Use ntk -h or --help to see available commands')
    except NTKError as e:
        if getattr(args, 'json', False) is True:
            output = Output()
            output.configure(args)
            output.error(
                getattr(args, 'command', 'ntk'), e, error_type=e.__class__.__name__)
        else:
            logging.error(e)
        sys.exit(1)
    except (TypeError, HTTPError) as e:
        if getattr(args, 'json', False) is True:
            output = Output()
            output.configure(args)
            output.error(getattr(args, 'command', 'ntk'), e, error_type=e.__class__.__name__)
        else:
            logging.exception(e, exc_info=False)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if getattr(args, 'json', False) is True:
            output = Output()
            output.configure(args)
            output.error(getattr(args, 'command', 'ntk'), e, error_type=e.__class__.__name__)
        else:
            logging.exception(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
