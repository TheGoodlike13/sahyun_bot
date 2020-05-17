import json
import logging
import os
import re
import time
from typing import TypeVar, List
from urllib.parse import urlparse, parse_qs

from requests import Session, Response, PreparedRequest
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# general purpose generic variable to be used in generic functions
T = TypeVar('T')

# if next(it, NON_EXISTENT) is NON_EXISTENT: <do stuff if 'it' was empty>
NON_EXISTENT = object()


def identity(o: T) -> T:
    return o


def debug_ex(e: Exception,
             trying_to: str = 'do something (check traceback)',
             *args,
             log: logging.Logger = logging.root,
             silent: bool = False):
    if silent:
        log.debug('Error while trying to %s: %s: %s', trying_to.format(*args), type(e).__name__, e, exc_info=True)
    else:
        log.error('Error while trying to %s: %s: %s', trying_to.format(*args), type(e).__name__, e)
        log.debug('Traceback:', exc_info=True)


HTTP_LOG = logging.getLogger('dumhttp')
MAX_SIZE_TO_LOG = 50 * 2 ** 10


def logging_hook(response: Response, *args, **kwargs):
    log_basic(response)
    log_detailed(response)


def log_basic(response: Response):
    lines = ['Basic HTTP call info:']
    for r in response.history:
        collect_basic_lines(r, lines)
    collect_basic_lines(response, lines)
    HTTP_LOG.info('\n'.join(lines))


def collect_basic_lines(r: Response, lines: List[str]):
    lines.append('> {} {}'.format(r.request.method, r.request.url))
    location = ' redirects to [{}]'.format(r.headers.get('Location', '')) if r.is_redirect else ''
    lines.append('< {} {}{} (took ~{}s)'.format(r.status_code, r.reason, location, r.elapsed))


def log_detailed(response):
    lines = ['Detailed HTTP call info:', '']
    for r in response.history:
        collect_lines(r, lines)
    collect_lines(response, lines)
    HTTP_LOG.debug('\n'.join(lines))


def collect_lines(response: Response, lines: List[str]):
    collect_request_lines(response.request, lines)
    lines.append('')
    collect_response_lines(response, lines)
    lines.append('')


def collect_request_lines(r: PreparedRequest, lines: List[str]):
    lines.append('> {} {}'.format(r.method, r.url))
    for key, value in r.headers.items():
        lines.append('> {} {}'.format(key, value))

    if not r.body:
        return lines.append('> EMPTY <')

    safe_body = re.sub(r'(ips_password=)([^&]+)', r'\g<1>********', r.body)
    lines.append('> {}'.format(safe_body))


def collect_response_lines(r: Response, lines: List[str]):
    lines.append('~ {}s elapsed'.format(r.elapsed))
    lines.append('')

    lines.append('< {} {}'.format(r.status_code, r.reason))
    for key, value in r.headers.items():
        lines.append('< {} {}'.format(key, value))

    if not r.text:
        return lines.append('< EMPTY >')

    try:
        return lines.append(json.dumps(r.json(), indent=4))
    except Exception as e:
        if 'json' in r.headers.get('Content-Type', ''):
            lines.append('< COULD NOT PARSE JSON BODY >')
            return debug_ex(e, 'parsing JSON response body')

    size = len(r.text)
    lines.append(r.text if size <= MAX_SIZE_TO_LOG else '< RESPONSE BODY TOO LARGE ({} bytes) >'.format(size))


RETRY_ON_METHOD = frozenset(
    ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
)

RETRY_ON_STATUS = frozenset(
    [429, 500, 502, 503, 504]
)


def retry_session(retry_count: int = 3,
                  session: Session = None) -> Session:
    session = session or Session()
    session.hooks["response"] = [logging_hook]

    retry = Retry(
        total=retry_count,
        connect=retry_count,
        read=retry_count,
        method_whitelist=RETRY_ON_METHOD,
        status_forcelist=RETRY_ON_STATUS,
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class WithRetry:
    @staticmethod
    def get(url: str, **kwargs) -> Response:
        with retry_session() as session:
            return session.get(url, **kwargs)

    @staticmethod
    def post(url: str, **kwargs) -> Response:
        with retry_session() as session:
            return session.post(url, **kwargs)


class FormatterUTC(logging.Formatter):
    converter = time.gmtime


def nuke_from_orbit(reason: str):
    logging.critical('Forcing shutdown of the application. Reason: {}'.format(reason))
    # noinspection PyProtectedMember
    os._exit(1)


YOUTUBE_SHORT_LINK = 'https://youtu.be/{}'


def clean_link(link: str) -> str:
    try:
        url_parts = urlparse(link or '')
        if 'youtube.com' in url_parts.netloc:
            video_id = parse_qs(url_parts.query).get('v', None)
            if video_id:
                return YOUTUBE_SHORT_LINK.format(video_id[0])
        elif url_parts.scheme == 'http':
            return link[:4] + 's' + link[4:]
    except ValueError:
        pass

    return link
