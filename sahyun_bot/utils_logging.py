import json
import logging
import re
import time
from logging import Formatter
from typing import List

from requests import Response, PreparedRequest

from sahyun_bot.utils import debug_ex


class FormatterUTC(Formatter):
    converter = time.gmtime


HTTP_DUMP = logging.getLogger('dumhttp')

DEFAULT_MAX_DUMP = 50 * 2 ** 10


# noinspection PyMethodMayBeStatic
class HttpDump:
    def __init__(self, unsafe: List[str] = None, max_dump: int = None):
        self.__unsafe_form_params = unsafe or []
        self.__max_dump = max_dump if max_dump and max_dump > 0 else DEFAULT_MAX_DUMP

    def all(self, response: Response, *args, **kwargs):
        self.basic(response, *args, **kwargs)
        self.detailed(response, *args, **kwargs)

    def basic(self, response: Response, *args, **kwargs):
        HTTP_DUMP.info('\n'.join(self.to_basic_info(response)))

    def detailed(self, response: Response, *args, **kwargs):
        HTTP_DUMP.debug('\n'.join(self.to_detailed_info(response)))

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
        lines.append('> {} {}'.format(r.request.method, r.request.url))

        location = ' redirects to [{}]'.format(r.headers.get('Location', '')) if r.is_redirect else ''
        lines.append('< {} {}{} (took ~{}s)'.format(r.status_code, r.reason, location, r.elapsed))

    def __collect_detailed(self, r: Response, lines: List[str]):
        self.__collect_detailed_request(r.request, lines)
        lines.append('')

        self.__collect_detailed_response(r, lines)
        lines.append('')

    def __collect_detailed_request(self, r: PreparedRequest, lines: List[str]):
        lines.append('> {} {}'.format(r.method, r.url))

        for key, value in r.headers.items():
            lines.append('> {}: {}'.format(key, value))

        if not r.body:
            return lines.append('> EMPTY <')

        lines.append('{}'.format(self.__safe_body(r.body)))

    def __safe_body(self, body: str):
        for unsafe_param in self.__unsafe_form_params:
            body = re.sub(self.__to_pattern(unsafe_param), r'\g<1>REDACTED', body)

        return body

    def __to_pattern(self, unsafe_param: str) -> str:
        return r'({}=)([^&]+)'.format(unsafe_param)

    def __collect_detailed_response(self, r: Response, lines: List[str]):
        lines.append('~ {}s elapsed'.format(r.elapsed))
        lines.append('')

        lines.append('< {} {}'.format(r.status_code, r.reason))
        for key, value in r.headers.items():
            lines.append('< {}: {}'.format(key, value))

        if not r.text:
            return lines.append('< EMPTY >')

        try:
            if r.text.strip()[:1] in ['[', '{']:
                return lines.append(json.dumps(r.json(), indent=4))
        except Exception as e:
            if 'json' in r.headers.get('Content-Type', ''):
                lines.append('< COULD NOT PARSE JSON BODY >')
                return debug_ex(e, 'parsing JSON response body')

        size = len(r.text)
        lines.append(r.text if size <= self.__max_dump else '< RESPONSE BODY TOO LARGE ({} bytes) >'.format(size))
