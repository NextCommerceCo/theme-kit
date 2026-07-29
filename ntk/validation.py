import json
import os
import re

from ntk.conf import CONTENT_FILE_EXTENSIONS, MEDIA_FILE_EXTENSIONS
from ntk.utils import get_template_name


TAG_RE = re.compile(r'{%\s*(block|endblock)\b(?:\s+([\w.-]+))?[^%]*%}')


def _template_errors(content):
    errors = []
    stack = []
    for tag, name in TAG_RE.findall(content):
        if tag == 'block':
            stack.append(name)
        elif not stack:
            errors.append('endblock has no matching block')
        else:
            opened = stack.pop()
            if name and name != opened:
                errors.append(f'endblock {name} closes block {opened}')
    errors.extend(f'block {name} is not closed' for name in stack)
    return errors


def validate_local_file(path):
    relative_path = get_template_name(path)
    extension = os.path.splitext(path)[1].lower()
    if extension in MEDIA_FILE_EXTENSIONS:
        return {'path': relative_path, 'status': 'valid', 'errors': [], 'content': None}
    if extension not in CONTENT_FILE_EXTENSIONS:
        return {
            'path': relative_path,
            'status': 'invalid',
            'errors': [f'unsupported extension {extension}'],
            'content': None,
        }
    try:
        with open(path, 'r', encoding='utf-8') as source_file:
            content = source_file.read()
    except (OSError, UnicodeDecodeError) as error:
        return {'path': relative_path, 'status': 'invalid', 'errors': [str(error)], 'content': None}

    errors = []
    if extension == '.json':
        try:
            json.loads(content)
        except json.JSONDecodeError as error:
            errors.append(f'invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}')
    elif extension == '.html':
        errors.extend(_template_errors(content))
        if relative_path.startswith('templates/catalogue/product.'):
            if "extends 'templates/catalogue/product.html'" in content or (
                    'extends "templates/catalogue/product.html"' in content):
                errors.append('custom product templates must be standalone or extend layouts/base.html')
    elif extension == '.js':
        if content.startswith('\ufeff'):
            errors.append('JavaScript must be UTF-8 without a byte-order mark')
        if '\x00' in content:
            errors.append('JavaScript must not contain NUL bytes')
    return {
        'path': relative_path,
        'status': 'invalid' if errors else 'valid',
        'errors': errors,
        'content': content,
    }
