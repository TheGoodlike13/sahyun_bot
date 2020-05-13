import pickle
from typing import Iterator, Optional, Callable, IO, Any

from requests import Response
from requests.sessions import Session

from sahyun_bot.utils import T, print_error, identity, parse_bool, non_existent

MAIN_PAGE = 'http://customsforge.com/'
LOGIN_PAGE = 'https://customsforge.com/index.php?app=core&module=global&section=login'

LOGIN_API = 'https://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES_API = 'https://ignition.customsforge.com/search/get_content?group=updated'
CDLC_BY_DATE_API = 'http://ignition.customsforge.com/search/get_group_content?group=updated&sort=updated'
DOWNLOAD_API = 'https://customsforge.com/process.php?id={}'

DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 300
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
        self.__batch_size = batch_size
        self.__timeout = timeout
        self.__cookie_jar_file = cookie_jar_file

        self.__username = username
        self.__password = password

        self.__session = Session()
        self.__with_cookie_file('rb', lambda f: self.__session.cookies.update(pickle.load(f)))
        # no error, since cookie file probably doesn't exist; we'll try to write it later and log any error then

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.__session.close()

    def login(self, username: str = None, password: str = None) -> bool:
        if username and password:
            self.__username = username
            self.__password = password

        if not self.__username and not self.__password:
            print('Username and password were not provided.')
            return False

        self.__session.cookies.clear()
        self.__with_cookie_file('wb', trying_to='clear cookie jar')

        form = {
            'ips_username': self.__username,
            'ips_password': self.__password,
            'auth_key': self.__api_key,
            'rememberMe': '1',
            'referer': MAIN_PAGE
        }
        r = self.__call('login', self.__session.post, LOGIN_API, data=form, try_login=False)
        if r is None:
            return False

        if not r.is_redirect or not r.headers.get('Location', '') == MAIN_PAGE:
            print('Login failed. Please check your credentials.')
            return False

        return True

    def dates(self) -> Iterator[str]:
        yield from self.__all(trying_to='find groups of songs',
                              call=self.__session.get,
                              url=DATES_API,
                              parse=Parse.dates)

    def cdlcs(self) -> Iterator[CDLC]:
        for date in self.dates():
            yield from self.__all(trying_to='find CDLCs',
                                  call=self.__session.get,
                                  url=CDLC_BY_DATE_API,
                                  params={'filter': date},
                                  parse=Parse.cdlcs)

    def __call(self,
               trying_to: str,
               call: Callable[..., Response],
               url: str,
               try_login: bool = True,
               **kwargs) -> Optional[Response]:
        try:
            r = call(url, timeout=self.__timeout, allow_redirects=False, **kwargs)
        except Exception as e:
            print_error(e, trying_to=trying_to)
            return None

        self.__with_cookie_file('wb', lambda f: pickle.dump(self.__session.cookies, f), trying_to='update cookie jar')

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            print('Cannot {}: automatic login to customsforge failed.'.format(trying_to))
            return None

        return self.__call(trying_to, call, url, try_login=False, **kwargs)

    def __all(self, parse: Callable[[Any], Iterator[T]], **call_params) -> Iterator[T]:
        skip = 0

        while True:
            params = call_params.setdefault('params', {})
            params['skip'] = skip
            params['take'] = self.__batch_size

            r = self.__call(**call_params)
            if not r:
                break

            try:
                it = parse(r.json())
                first = next(it, non_existent)
                if first is non_existent:
                    break

                yield first
                yield from it
            except Exception as e:
                print_error(e, trying_to='parse response of [{}] as JSON'.format(call_params.get('trying_to')))
                break

            skip += self.__batch_size

    def __with_cookie_file(self,
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
