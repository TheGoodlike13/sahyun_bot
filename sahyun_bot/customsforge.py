import html
import logging
import pickle
from datetime import date
from threading import Lock
from typing import Iterator, Optional, Callable, IO, Any, List
from urllib.parse import urlparse, parse_qs

from requests import Response
from requests.cookies import RequestsCookieJar

from sahyun_bot.utils import T, NON_EXISTENT, identity, parse_bool, debug_ex, WithRetry

LOG = logging.getLogger(__name__.rpartition('.')[2])

MAIN_PAGE = 'http://customsforge.com/'
LOGIN_PAGE = 'https://customsforge.com/index.php?app=core&module=global&section=login'

LOGIN_API = 'https://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES_API = 'https://ignition.customsforge.com/search/get_content?group=updated'
CDLC_BY_DATE_API = 'http://ignition.customsforge.com/search/get_group_content?group=updated&sort=updated'
DOWNLOAD_API = 'https://customsforge.com/process.php?id={}'

YOUTUBE_SHORT_LINK = 'https://youtu.be/{}'

DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 100
DEFAULT_COOKIE_FILE = '.cookie_jar'
TEST_COOKIE_FILE = '.cookie_jar_test'

EONS_AGO = date.fromisoformat('2010-01-01')       # this should pre-date even the oldest CDLC
SOME_TIME_AGO = date.fromisoformat('2020-05-15')  # this should be in the past, but many older CDLCs should exist (1K+)


class CustomsForgeClient:
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
        self.__timeout = timeout if Verify.timeout(timeout) else DEFAULT_TIMEOUT
        self.__cookie_jar_file = cookie_jar_file

        self.__username = username
        self.__password = password
        self.__login_rejected = False
        self.__prevent_multiple_login_lock = Lock()

        self.__cookies = RequestsCookieJar()
        self.__with_cookie_jar('rb', lambda f: self.__cookies.update(pickle.load(f)))
        # no error, since cookie file probably doesn't exist; we'll try to write it later and log any error then

        self.__get_today = get_today

    def login(self, username: str = None, password: str = None) -> bool:
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
            r = self.__call('login', WithRetry.post, LOGIN_API, data=form, cookies=None, try_login=False)
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
        return self.__estimate_date_skip(since=SOME_TIME_AGO) > 0

    def dates(self, since: date = EONS_AGO) -> Iterator[str]:
        remaining_lazy_dates = self.__lazy_all(trying_to='find dates for CDLC updates',
                                               call=WithRetry.get,
                                               url=DATES_API,
                                               parse=Parse.dates,
                                               skip=self.__estimate_date_skip(since))

        for d in remaining_lazy_dates:
            if date.fromisoformat(d) >= since:
                yield d
                break

        yield from remaining_lazy_dates

    def cdlcs(self, since: date = EONS_AGO) -> Iterator[dict]:
        for d in self.dates(since):
            yield from self.__lazy_all(trying_to='find CDLCs',
                                       call=WithRetry.get,
                                       url=CDLC_BY_DATE_API,
                                       params={'filter': d},
                                       parse=Parse.cdlcs)

    def direct_link(self, cdlc_id: str) -> str:
        url = DOWNLOAD_API.format(cdlc_id)
        r = self.__call('get direct link', WithRetry.get, url)
        if not r or not r.is_redirect:
            return ''

        return r.headers.get('Location', '')

    def __has_credentials(self, username: str, password: str):
        if username and password:
            self.__username = username
            self.__password = password
            self.__login_rejected = False

        if self.__login_rejected:
            LOG.debug('Login rejected. Please provide new credentials to try again.')
            return False

        if not self.__username and not self.__password:
            LOG.info('No credentials have been provided.')
            self.__login_rejected = True
            return False

        return True

    def __estimate_date_skip(self, since: date) -> int:
        """
        :returns how many dates can be skipped to arrive closer to expected date; this is usually a generous estimate,
        but can become outdated; therefore, only estimate right before calling for dates
        """
        if not since or since <= EONS_AGO:
            return 0

        date_count = self.__date_count()
        if not date_count:
            return 0

        passed_since = self.__get_today() - since
        skip_estimate = date_count - passed_since.days - 3
        # we subtract one to include the date, one to account for time passing, one to avoid timezone shenanigans
        return skip_estimate if skip_estimate > 0 else 0

    def __date_count(self) -> Optional[int]:
        date_count = self.__lazy_all(trying_to='total count of dates',
                                     call=WithRetry.get,
                                     url=DATES_API,
                                     parse=Parse.date_count,
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
            return debug_ex(e, trying_to, log=LOG)

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            LOG.debug('Cannot %s: automatic login to customsforge failed.', trying_to)
            return None

        kwargs.pop('cookies', None)
        return self.__call(trying_to, call, url, try_login=False, **kwargs)

    def __lazy_all(self,
                   parse: Callable[[Any], Iterator[T]],
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
                it = parse(r.json())
                first = next(it, NON_EXISTENT)
                if first is NON_EXISTENT:
                    break

                yield first
                yield from it
            except Exception as e:
                return debug_ex(e, 'parse response of [{}] as JSON', call_params.get('trying_to'), log=LOG)

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
                    debug_ex(e, trying_to, log=LOG)
            else:
                with f:
                    return on_file(f)


class Verify:
    @staticmethod
    def batch_size(batch_size: int) -> bool:
        return batch_size and 0 < batch_size <= DEFAULT_BATCH_SIZE

    @staticmethod
    def timeout(timeout: int) -> bool:
        return timeout > 0


def read(data: dict, key: str) -> str:
    value = data.get(key)
    return html.unescape(value.strip()) if value else ''


def read_all(data: dict, key: str) -> List[str]:
    return [p.strip() for p in data.get(key).split(',') if p and not p.isspace()]


def read_bool(data: dict, key: str) -> bool:
    return parse_bool(read(data, key))


def read_link(data: dict, key: str) -> str:
    link = read(data, key)
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


class Parse:
    @staticmethod
    def dates(dates_api_json) -> Iterator[str]:
        date_groups = dates_api_json[0]
        if not date_groups:
            return

        for date_group in date_groups:
            yield date_group['grp']

    @staticmethod
    def date_count(dates_api_json) -> Iterator[str]:
        yield dates_api_json[1][0]['total']

    @staticmethod
    def cdlcs(cdlc_by_date_api_json) -> Iterator[dict]:
        if not cdlc_by_date_api_json:
            return

        for cdlc_json in cdlc_by_date_api_json:
            yield Parse.cdlc(cdlc_json)

    @staticmethod
    def cdlc(cdlc_json) -> dict:
        _id = cdlc_json.get('id')
        return {
            '_id': str(_id),
            'artist': read(cdlc_json, 'artist'),
            'title': read(cdlc_json, 'title'),
            'album': read(cdlc_json, 'album'),
            'author': read(cdlc_json, 'member'),
            'tuning': read(cdlc_json, 'tuning'),
            'parts': read_all(cdlc_json, 'parts'),
            'platforms': read_all(cdlc_json, 'platforms'),
            'has_dynamic_difficulty': read_bool(cdlc_json, 'dd'),
            'is_official': read_bool(cdlc_json, 'official'),
            'version_timestamp': cdlc_json.get('updated'),
            'music_video': read_link(cdlc_json, 'music_video'),
            'indirect_link': DOWNLOAD_API.format(_id),
        }
