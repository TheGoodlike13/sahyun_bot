import logging
import time
from configparser import ConfigParser
from typing import Callable, Optional, TypeVar

from requests import Session, Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# general purpose generic variable to be used in generic functions
T = TypeVar('T')

# if next(it, NON_EXISTENT) is NON_EXISTENT: <do stuff if 'it' was empty>
NON_EXISTENT = object()

config = ConfigParser()


def identity(o: T) -> T:
    return o


# noinspection PyProtectedMember
def parse_bool(s: str, fallback: bool = None) -> bool:
    try:
        return config._convert_to_boolean(s)
    except ValueError:
        if fallback:
            return fallback

        raise


# noinspection PyBroadException
def read_config(section: str,
                key: str,
                fallback: T = None,
                allow_empty: bool = False,
                convert: Callable[[str], T] = identity) -> Optional[T]:
    value = config.get(section, key, fallback=fallback)
    if value is None or value is fallback or not allow_empty and not value:
        return fallback

    try:
        return convert(value.strip())
    except Exception as e:
        debug_ex(logging.root, e, 'convert config value [{}]->{}: {}', section, key, value, silent=True)
        return fallback


def debug_ex(log: logging.Logger, e: Exception, message: str, *args, silent: bool = False):
    if silent:
        log.debug('Error while trying to %s: %s: %s', message.format(*args), type(e).__name__, e, exc_info=True)
    else:
        log.error('Error while trying to %s: %s: %s', message.format(*args), type(e).__name__, e)
        log.debug('Traceback:', exc_info=True)


RETRY_ON_METHOD = frozenset(
    ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
)

RETRY_ON_STATUS = frozenset(
    [429, 500, 502, 503, 504]
)


def retry_session(retry_count: int = 3,
                  session: Session = None) -> Session:
    session = session or Session()
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
