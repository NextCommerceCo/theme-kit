import functools
import logging

from ntk.exceptions import NTKAuthError, NTKNotFoundError

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


def parser_config(*args, **kwargs):
    """Decorator for parser config values from command arguments."""

    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(self, parser, **func_kwargs):
            for name, value in kwargs.items():
                setattr(self.config, name, value)

            self.config.parser_config(parser, write_file=kwargs.get('write_file', False))
            self.gateway.store = self.config.store
            self.gateway.apikey = self.config.apikey

            func(self, parser, **func_kwargs)

        return _wrapper

    return _decorator


def check_error(error_format='{error_default} -> {error_msg}', response_json=True, **kwargs):
    """Decorator for check response error from request API"""

    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(self, *func_args, **func_kwargs):
            response = func(self, *func_args, **func_kwargs)

            if response.status_code == 401:
                raise NTKAuthError(f'Invalid API key for {self.store}.')

            if response.status_code == 404:
                raise NTKNotFoundError(
                    f'Not found: {response.url} — check the store URL and theme id.')

            error_default = f'{func.__name__.capitalize().replace("_", " ")} of {self.store} failed.'
            error_msg = ""
            content_type = response.headers.get('content-type', '').lower()
            if response.ok and not response_json:
                return response
            elif response.ok and content_type.startswith('application/json'):
                return response
            elif content_type.startswith('application/json'):
                result = response.json()
                error_msg = " -> "
                for key, value in result.items():
                    if isinstance(value, list):
                        error_msg += f'"{key}" : {" ".join(value)}'
                    else:
                        error_msg += value

            error_log = error_format.format(
                **vars(self), **func_kwargs, error_default=error_default, error_msg=error_msg
            )

            logging.info(f'{error_log}')

            return response

        return _wrapper

    return _decorator
