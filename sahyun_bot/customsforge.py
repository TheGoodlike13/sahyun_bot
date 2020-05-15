import html
import pickle
from datetime import date
from threading import Lock
from typing import Iterator, Optional, Callable, IO, Any

from requests import Response
from requests.cookies import RequestsCookieJar

from sahyun_bot.utils import T, NON_EXISTENT, identity, parse_bool, print_error, WithRetry

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

EONS_AGO = date.fromisoformat('2010-01-01')


def read(data: dict, key: str):
    return html.unescape(data.get(key).strip())


def read_all(data: dict, key: str):
    return [p.strip() for p in data.get(key).split(',') if p and not p.isspace()]


def read_bool(data: dict, key: str):
    return parse_bool(read(data, key))


class CDLC:
    def __init__(self, **data):
        self.id = str(data.get('id'))
        self.artist = read(data, 'artist')
        self.title = read(data, 'title')
        self.album = read(data, 'album')
        self.author = read(data, 'member')
        self.tuning = read(data, 'tuning')
        self.parts = read_all(data, 'parts')
        self.platforms = read_all(data, 'platforms')
        self.hasDynamicDifficulty = read_bool(data, 'dd')
        self.isOfficial = read_bool(data, 'official')
        self.lastUpdated = data.get('updated')
        self.musicVideo = read(data, 'music_video')

    def link(self) -> Optional[str]:
        return DOWNLOAD_API.format(self.id) if self.id else None

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, __class__):
            return NotImplemented

        return vars(self) == vars(o)

    def __hash__(self) -> int:
        return hash(vars(self))


class CustomsForgeClient:
    def __init__(self,
                 api_key: str,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 timeout: int = DEFAULT_TIMEOUT,
                 cookie_jar_file: Optional[str] = DEFAULT_COOKIE_FILE,
                 username: str = None,
                 password: str = None):
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

    def login(self, username: str = None, password: str = None) -> bool:
        with self.__prevent_multiple_login_lock:
            if username and password:
                self.__username = username
                self.__password = password
                self.__login_rejected = False

            if self.__login_rejected:
                print('Login rejected. Please provide new credentials to try again.')
                return False

            if not self.__username and not self.__password:
                print('No credentials have been provided.')
                self.__login_rejected = True
                return False

            form = {
                'ips_username': self.__username,
                'ips_password': self.__password,
                'auth_key': self.__api_key,
                'rememberMe': '1',
                'referer': MAIN_PAGE
            }
            r = self.__call('login', WithRetry.post, LOGIN_API, data=form, cookies=None, try_login=False)
            if r is None:  # this indicates an error - repeated attempts may still succeed
                return False

            if not r.is_redirect or not r.headers.get('Location', '') == MAIN_PAGE:
                print('Login failed. Please check your credentials.')
                self.__login_rejected = True
                return False

            self.__with_cookie_jar('wb', lambda f: pickle.dump(r.cookies, f), trying_to='update cookie jar')
            self.__cookies = r.cookies
            return True

    def ping(self) -> bool:
        """
        :returns true if a simple call to customsforge succeeded (including login), false otherwise
        """
        return next(self.dates(custom_batch=1), NON_EXISTENT) is not NON_EXISTENT

    def dates(self, since: date = EONS_AGO, custom_batch: int = None) -> Iterator[date]:
        remaining_lazy_dates = self.__lazy_all(trying_to='find dates for CDLC updates',
                                               call=WithRetry.get,
                                               url=DATES_API,
                                               parse=Parse.dates,
                                               skip=self.__estimate_date_skip(since),
                                               batch=custom_batch)

        for d in remaining_lazy_dates:
            if date.fromisoformat(d) >= since:
                yield d
                break

        yield from remaining_lazy_dates

    def cdlcs(self, since: date = EONS_AGO) -> Iterator[CDLC]:
        for d in self.dates(since):
            yield from self.__lazy_all(trying_to='find CDLCs',
                                       call=WithRetry.get,
                                       url=CDLC_BY_DATE_API,
                                       params={'filter': d},
                                       parse=Parse.cdlcs)

    def __estimate_date_skip(self, since: date) -> int:
        """
        :returns how many dates can be skipped to arrive closer to expected date; this is usually a generous estimate,
        but can become outdated; therefore, only estimate right before calling for dates
        """
        if since <= EONS_AGO:
            return 0

        delta = date.today() - since
        skip_estimate = self.__date_count() - delta.days - 1
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
            print_error(e, trying_to=trying_to)
            return None

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            print('Cannot {}: automatic login to customsforge failed.'.format(trying_to))
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
                print_error(e, trying_to='parse response of [{}] as JSON'.format(call_params.get('trying_to')))
                break

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
                    print_error(e, trying_to)
            else:
                with f:
                    return on_file(f)


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
    def cdlcs(cdlc_by_date_api_json) -> Iterator[CDLC]:
        if not cdlc_by_date_api_json:
            return

        for cdlc in cdlc_by_date_api_json:
            yield CDLC(**cdlc)


class Verify:
    @staticmethod
    def batch_size(batch_size: int) -> bool:
        return batch_size and 0 < batch_size <= DEFAULT_BATCH_SIZE

    @staticmethod
    def timeout(timeout: int) -> bool:
        return timeout > 0
