from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from sahyun_bot.utils_logging import HttpDump

DEFAULT_RETRY_COUNT = 3

RETRY_ON_METHOD = frozenset(
    ['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
)

RETRY_ON_STATUS = frozenset(
    [403, 429, 500, 502, 503, 504]
)


class SessionFactory:
    def __init__(self, retry_count: int = None, **dump_kwargs):
        self.__dump = HttpDump(**dump_kwargs)
        self.__retry_count = retry_count if retry_count and retry_count > 0 else DEFAULT_RETRY_COUNT

    def with_retry(self, session: Session = None):
        session = session or Session()
        session.hooks["response"] = [self.__dump.all]

        retry = Retry(
            total=self.__retry_count,
            connect=self.__retry_count,
            read=self.__retry_count,
            method_whitelist=RETRY_ON_METHOD,
            status_forcelist=RETRY_ON_STATUS,
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
