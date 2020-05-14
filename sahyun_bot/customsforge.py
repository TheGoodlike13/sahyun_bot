import pickle
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

DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 100
DEFAULT_COOKIE_FILE = '.cookie_jar'
TEST_COOKIE_FILE = '.cookie_jar_test'


class CDLC:
    def __init__(self, **data):
        self.id = str(data.get('id'))
        self.artist = data.get('artist').strip()
        self.title = data.get('title').strip()
        self.album = data.get('album').strip()
        self.author = data.get('member').strip()
        self.tuning = data.get('tuning').strip()
        self.parts = [p.strip() for p in data.get('parts').split(',') if p and not p.isspace()]
        self.platforms = [p.strip() for p in data.get('platforms').split(',') if p and not p.isspace()]
        self.hasDynamicDifficulty = parse_bool(data.get('dd').strip())
        self.isOfficial = parse_bool(data.get('official').strip())
        self.lastUpdated = data.get('updated')
        self.musicVideo = data.get('music_video').strip()

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

    def dates(self, custom_batch: int = None) -> Iterator[str]:
        yield from self.__all(trying_to='find groups of songs',
                              call=WithRetry.get,
                              url=DATES_API,
                              custom_batch=custom_batch,
                              parse=Parse.dates)

    def cdlcs(self) -> Iterator[CDLC]:
        for date in self.dates():
            yield from self.__all(trying_to='find CDLCs',
                                  call=WithRetry.get,
                                  url=CDLC_BY_DATE_API,
                                  params={'filter': date},
                                  parse=Parse.cdlcs)

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

    def __all(self,
              parse: Callable[[Any], Iterator[T]],
              custom_batch: int = None,
              **call_params) -> Iterator[T]:
        skip = 0
        batch = custom_batch if Verify.batch_size(custom_batch) else self.__batch_size

        while True:
            params = call_params.setdefault('params', {})
            params['skip'] = skip
            params['take'] = batch

            r = self.__call(**call_params)
            if not r:
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
        return 0 < timeout
