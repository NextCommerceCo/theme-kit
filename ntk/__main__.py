#!/usr/bin/env python
import logging
import sys

from requests.exceptions import HTTPError

from ntk.exceptions import NTKError
from ntk.ntk_parser import Parser

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def main():
    parser = Parser().create_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError:
        print('Use ntk -h or --help to see available commands')
    except NTKError as e:
        # print new line for support error on process progress bar
        print()
        logging.error(e)
        sys.exit(1)
    except (TypeError, HTTPError) as e:
        # print new line for support error on process progress bar
        print()
        logging.exception(e, exc_info=False)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
