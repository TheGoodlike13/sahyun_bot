import json
import logging
import re
import time
from logging import Formatter
from typing import List

from requests import Response, PreparedRequest

from sahyun_bot.utils import debug_ex


class FormatterUTC(Formatter):
    """
    Formatter which uses UTC instead of local time. Useful for files that need to be shared across different timezones.
    """
    converter = time.gmtime


def get_logger(module_name: str) -> logging.Logger:
    """
    In normal applications, logger names match module names. However, this is no ordinary application.
    We are logging to the console for the purpose of informing the user; using weird module names there is
    detrimental. As a result, I've tried to shorten them and get rid of unnecessary characters so they appear
    more natural and reasonable in the command line.

    :returns name of logger for given module
    """
    left, dot, right = module_name.rpartition('.')
    name = right if right else left
    clear_name = name[5:] if name[:5] == 'utils' and name[5:] else name
    terse_name = clear_name.replace('_', '')
    return logging.getLogger(terse_name)


HTTP_DUMP = logging.getLogger('httdump')
HTTP_TRACE = logging.getLogger('httdump.trace')

DEFAULT_MAX_DUMP = 50 * 2 ** 10


class HttpDump:
    """
    Logging hook for HTTP requests. Set all(), basic() or detailed() as a hook to a Session object to use.

    To avoid passwords from being logger, pass any form parameters they are associated with as unsafe.
    This will cause these form parameters to be redacted from request logs.

    To avoid dumping arbitrary large response bodies, pass maximum char length (for body) which will be replaced
    with a generic message instead.
    """
    def __init__(self, unsafe: List[str] = None, max_dump: int = None):
        self.__unsafe_form_params = unsafe or []
        self.__max_dump = max_dump if max_dump and max_dump > 0 else DEFAULT_MAX_DUMP

    def all(self, response: Response, *args, **kwargs):
        self.basic(response, *args, **kwargs)
        self.detailed(response, *args, **kwargs)

    def basic(self, response: Response, *args, **kwargs):
        HTTP_DUMP.info('\n'.join(self.to_basic_info(response)))

    def detailed(self, response: Response, *args, **kwargs):
        HTTP_TRACE.debug('\n'.join(self.to_detailed_info(response)))

    def to_basic_info(self, response) -> List[str]:
        lines = ['Basic HTTP call info:']

        for r in response.history:
            self.__collect_basic(r, lines)

        self.__collect_basic(response, lines)

        return lines

    def to_detailed_info(self, response) -> List[str]:
        lines = ['Detailed HTTP call info:', '']

        for r in response.history:
            self.__collect_detailed(r, lines)

        self.__collect_detailed(response, lines)

        return lines

    def __collect_basic(self, r: Response, lines: List[str]):
        lines.append(f'> {r.request.method} {r.request.url}')

        location = r.headers.get('Location', '')
        location = f' redirects to [{location}]' if r.is_redirect else ''
        lines.append(f'< {r.status_code} {r.reason}{location} (took ~{r.elapsed}s)')

    def __collect_detailed(self, r: Response, lines: List[str]):
        self.__collect_detailed_request(r.request, lines)
        lines.append('')

        self.__collect_detailed_response(r, lines)
        lines.append('')

    def __collect_detailed_request(self, r: PreparedRequest, lines: List[str]):
        lines.append(f'> {r.method} {r.url}')

        for key, value in r.headers.items():
            lines.append(f'> {key}: {value}')

        if not r.body:
            return lines.append('> EMPTY <')

        lines.append(f'{self.__safe_body(r.body)}')

    def __safe_body(self, body: str):
        for unsafe_param in self.__unsafe_form_params:
            body = re.sub(self.__to_pattern(unsafe_param), r'\g<1>REDACTED', body)

        return body

    def __to_pattern(self, unsafe_param: str) -> str:
        return fr'({unsafe_param}=)([^&]+)'

    def __collect_detailed_response(self, r: Response, lines: List[str]):
        lines.append(f'~ {r.elapsed}s elapsed')
        lines.append('')

        lines.append(f'< {r.status_code} {r.reason}')
        for key, value in r.headers.items():
            lines.append(f'< {key}: {value}')

        if not r.text:
            return lines.append('< EMPTY >')

        try:
            if r.text.strip()[:1] in ['[', '{']:
                return lines.append(json.dumps(r.json(), indent=4))
        except Exception as e:
            if 'json' in r.headers.get('Content-Type', ''):
                lines.append('< COULD NOT PARSE JSON BODY >')
                return debug_ex(e, 'parsing JSON response body', silent=True)

        size = len(r.text)
        lines.append(r.text if size <= self.__max_dump else f'< RESPONSE BODY TOO LARGE ({size} bytes) >')
