import html
import pickle
from datetime import date, timedelta
from itertools import dropwhile
from threading import Lock
from typing import Iterator, Optional, Callable, IO, Any, List

from requests import Response, Session
from requests.cookies import RequestsCookieJar

from sahyun_bot.utils import T, NON_EXISTENT, identity, debug_ex, clean_link
from sahyun_bot.utils_logging import get_logger
from sahyun_bot.utils_session import SessionFactory
from sahyun_bot.utils_settings import parse_bool, parse_list

LOG = get_logger(__name__)

MAIN_PAGE = 'http://customsforge.com/'
LOGIN_PAGE = 'https://customsforge.com/index.php?app=core&module=global&section=login'
CDLC_PAGE = 'http://customsforge.com/page/customsforge_rs_2014_cdlc.html/_/pc-enabled-rs-2014-cdlc/{}-r{}'

LOGIN_API = 'https://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES_API = 'https://ignition.customsforge.com/search/get_content?group=updated'
CDLC_BY_DATE_API = 'https://ignition.customsforge.com/search/get_group_content?group=updated&sort=updated'
DOWNLOAD_API = 'https://customsforge.com/process.php?id={}'

DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 100
DEFAULT_COOKIE_FILE = '.cookie_jar'
TEST_COOKIE_FILE = '.cookie_jar_test'

EONS_AGO = date.fromisoformat('2010-01-01')  # this should pre-date even the oldest CDLC


class CustomsForgeClient:
    """
    Implements customsforge API for CDLCs. (Should be) thread-safe.

    To access the API, logging in is required. This is attempted exactly once for every API call that returns
    a redirect indicating lack (or invalid) credentials. Cookies resulting from login can be stored to avoid
    this process in subsequent executions.
    """
    def __init__(self,
                 api_key: str,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 timeout: int = DEFAULT_TIMEOUT,
                 cookie_jar_file: Optional[str] = DEFAULT_COOKIE_FILE,
                 username: str = None,
                 password: str = None,
                 get_today: Callable[[], date] = date.today):
        self.__api_key = api_key
        self.__batch_size = batch_size if Verify.batch_size(batch_size) else DEFAULT_BATCH_SIZE
        self.__timeout = timeout if timeout > 0 else DEFAULT_TIMEOUT
        self.__cookie_jar_file = cookie_jar_file

        self.__username = username
        self.__password = password
        self.__login_rejected = False
        self.__prevent_multiple_login_lock = Lock()

        self.__sessions = SessionFactory(unsafe=['ips_password'])
        self.__cookies = RequestsCookieJar()
        self.__with_cookie_jar('rb', lambda f: self.__cookies.update(pickle.load(f)))
        # no error, since cookie file probably doesn't exist; we'll try to write it later and log any error then

        self.__get_today = get_today

    def login(self, username: str = None, password: str = None) -> bool:
        """
        Tries to log in using given credentials. They are stored for future use (e.g. automatic re-log).

        If no credentials are passed into the method, tries to use already stored credentials, if any.

        If some cases it is possible to determine that login failed due to invalid credentials. In such cases
        this method will avoid logging in until new credentials are passed into it.

        :returns true if login succeeded, false otherwise
        """
        with self.__prevent_multiple_login_lock:
            if not self.__has_credentials(username, password):
                return False

            form = {
                'ips_username': self.__username,
                'ips_password': self.__password,
                'auth_key': self.__api_key,
                'rememberMe': '1',
                'referer': MAIN_PAGE,
            }
            with self.__sessions.with_retry() as session:
                r = self.__call('login', session.post, LOGIN_API, data=form, cookies=None, try_login=False)

            if not r:  # this indicates an error - repeated attempts may still succeed
                return False

            if not r.is_redirect or not r.headers.get('Location', '') == MAIN_PAGE:
                LOG.error('Login failed. Please check your credentials.')
                self.__login_rejected = True
                return False

            self.__with_cookie_jar('wb', lambda f: pickle.dump(r.cookies, f), trying_to='update cookie jar')
            self.__cookies = r.cookies
            return True

    def ping(self) -> bool:
        """
        :returns true if a simple call to customsforge succeeded (including login), false otherwise
        """
        with self.__sessions.with_retry() as session:
            return self.__date_count(session=session) is not None

    def dates(self, since: date = None) -> Iterator[str]:
        """
        Generates all dates which had an updated CDLC, since the date given, in ascending order.
        If no date is given, starts at the beginning.

        The dates are returned in ISO format strings, intended to be used by other APIs.
        """
        with self.__sessions.with_retry() as session:
            yield from self.__dates(since, session)

    def cdlcs(self, since: date = None, since_exact: int = 0) -> Iterator[dict]:
        """
        Generates all CDLCs which are available in customsforge, since the date and/or exact time given.
        Exact time takes precedence over the date, unless it is 0 (or negative).
        If no date or exact time is given, starts at the beginning.

        The order of CDLCs as they are returned in ascending with respect to the last time they were updated.
        CDLCs are returned as dicts containing information, such as artist, title, id, link, etc.
        Refer to To.cdlcs method for specifics.
        """
        since_exact = since_exact or 0
        since = self.__estimate_date(since_exact) if since_exact else since

        with self.__sessions.with_retry() as session:
            for d in self.__dates(since, session):
                lazy_cdlcs = self.__lazy_all(trying_to='find CDLCs',
                                             call=session.get,
                                             url=CDLC_BY_DATE_API,
                                             params={'filter': d},
                                             convert=To.cdlcs)

                yield from dropwhile(lambda c: c['snapshot_timestamp'] < since_exact, lazy_cdlcs)

    def direct_link(self, cdlc_id: Any) -> str:
        """
        :returns link to the direct download of the CDLC with given id, if such exists, empty string otherwise
        """
        url = DOWNLOAD_API.format(cdlc_id)

        with self.__sessions.with_retry() as session:
            r = self.__call('get direct link', session.get, url)

        return r.headers.get('Location', '') if r and r.is_redirect else ''

    def calculate_date_skip(self, since: date, date_count: int):
        """
        :returns how many dates can be skipped to arrive closer to expected date; this is usually a generous estimate,
        but can become outdated; therefore, only estimate right before calling for dates
        """
        passed_since = self.__get_today() - since
        # we subtract one to include the date, one to account for time passing, one to avoid timezone shenanigans
        skip_estimate = date_count - passed_since.days - 3
        return skip_estimate if skip_estimate > 0 else 0

    def __has_credentials(self, username: str, password: str):
        if username and password:
            self.__username = username
            self.__password = password
            self.__login_rejected = False

        if self.__login_rejected:
            LOG.debug('Login rejected. Please provide new credentials to try again.')
            return False

        if not self.__username and not self.__password:
            LOG.error('No credentials have been provided.')
            self.__login_rejected = True
            return False

        return True

    def __dates(self, since: date, session: Session):
        since = since or EONS_AGO

        lazy_dates = self.__lazy_all(trying_to='find dates for CDLC updates',
                                     call=session.get,
                                     url=DATES_API,
                                     convert=To.dates,
                                     skip=self.__estimate_date_skip(since, session))

        yield from dropwhile(lambda d: date.fromisoformat(d) < since, lazy_dates)

    def __estimate_date_skip(self, since: date, session: Session) -> int:
        if since <= EONS_AGO:
            return 0

        date_count = self.__date_count(session)
        if not date_count:
            return 0

        return self.calculate_date_skip(since, date_count)

    def __estimate_date(self, epoch_seconds: int) -> date:
        # we subtract one day to account for timezone shenanigans
        return date.fromtimestamp(epoch_seconds) - timedelta(days=1) if epoch_seconds > 0 else EONS_AGO

    def __date_count(self, session: Session) -> Optional[int]:
        date_count = self.__lazy_all(trying_to='total count of dates',
                                     call=session.get,
                                     url=DATES_API,
                                     convert=To.date_count,
                                     batch=1)
        return next(date_count, None)

    def __call(self,
               trying_to: str,
               call: Callable[..., Response],
               url: str,
               try_login: bool = True,
               **kwargs) -> Optional[Response]:
        kwargs.setdefault('cookies', self.__cookies)

        try:
            r = call(url=url, timeout=self.__timeout, allow_redirects=False, **kwargs)
        except Exception as e:
            return debug_ex(e, trying_to, LOG)

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            LOG.debug('Cannot %s: automatic login to customsforge failed.', trying_to)
            return None

        kwargs.pop('cookies', None)
        return self.__call(trying_to, call, url, try_login=False, **kwargs)

    def __lazy_all(self,
                   convert: Callable[[Any], Iterator[T]],
                   skip: int = 0,
                   batch: int = None,
                   **call_params) -> Iterator[T]:
        batch = batch if Verify.batch_size(batch) else self.__batch_size

        while True:
            params = call_params.setdefault('params', {})
            params['skip'] = skip
            params['take'] = batch

            r = self.__call(**call_params)
            if not r or not r.text:
                break

            try:
                it = convert(r.json())
                first = next(it, NON_EXISTENT)
                if first is NON_EXISTENT:
                    break

                yield first
                yield from it
            except Exception as e:
                trying_to = call_params['trying_to']
                return debug_ex(e, f'parse response of <{trying_to}> as JSON', LOG)

            skip += batch

    def __with_cookie_jar(self,
                          options: str,
                          on_file: Callable[[IO], T] = identity,
                          trying_to: str = None) -> T:
        if self.__cookie_jar_file:
            try:
                f = open(self.__cookie_jar_file, options)
            except Exception as e:
                if trying_to:
                    debug_ex(e, trying_to, LOG)
            else:
                with f:
                    return on_file(f)


class Verify:
    @staticmethod
    def batch_size(batch_size: int) -> bool:
        return batch_size and 0 < batch_size <= DEFAULT_BATCH_SIZE


class To:
    @staticmethod
    def dates(dates_api_response) -> Iterator[str]:
        date_groups = dates_api_response[0]
        if not date_groups:
            return

        for date_group in date_groups:
            yield date_group['grp']

    @staticmethod
    def date_count(dates_api_response) -> Iterator[str]:
        yield dates_api_response[1][0]['total']

    @staticmethod
    def cdlcs(cdlcs_by_date) -> Iterator[dict]:
        if not cdlcs_by_date:
            return

        for c in cdlcs_by_date:
            yield To.cdlc(c)

    @staticmethod
    def cdlc(c) -> dict:
        cdlc_id = c['id']
        return {
            'id': cdlc_id,
            'artist': read(c, 'artist'),
            'title': read(c, 'title'),
            'album': read(c, 'album'),
            'tuning': read(c, 'tuning'),
            'instrument_info': read_all(c, 'instrument_info'),
            'parts': read_all(c, 'parts'),
            'platforms': read_all(c, 'platforms'),
            'has_dynamic_difficulty': read_bool(c, 'dd'),
            'is_official': read_bool(c, 'official'),

            'author': read(c, 'member'),
            'version': read(c, 'version'),

            'download': DOWNLOAD_API.format(cdlc_id),
            'info': CDLC_PAGE.format(read(c, 'furl'), cdlc_id),
            'video': read_link(c, 'music_video'),
            'art': read_link(c, 'album_art'),

            'snapshot_timestamp': c['updated'],
        }


def read(data: dict, key: str) -> str:
    value = data[key]
    return html.unescape(value.strip()) if value else ''


def read_all(data: dict, key: str) -> List[str]:
    return parse_list(read(data, key))


def read_bool(data: dict, key: str) -> bool:
    return parse_bool(read(data, key))


def read_link(data: dict, key: str) -> str:
    return clean_link(read(data, key))
