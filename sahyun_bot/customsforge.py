from typing import Iterator, Optional, Callable

from requests import Response
from requests.sessions import Session

MAIN_PAGE = 'http://customsforge.com/'
LOGIN_PAGE = 'https://customsforge.com/index.php?app=core&module=global&section=login'

LOGIN_API = 'https://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES_API = 'https://ignition.customsforge.com/search/get_content?group=updated'

DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 300


class CustomsForgeClient:
    def __init__(self,
                 api_key: str,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 timeout: int = DEFAULT_TIMEOUT,
                 username: str = None,
                 password: str = None):
        self.__api_key = api_key
        self.__batch_size = batch_size
        self.__timeout = timeout

        self.__username = username
        self.__password = password

        self.__session = Session()

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
        skip = 0

        while True:
            params = {
                'skip': skip,
                'take': self.__batch_size
            }
            r = self.__call('find groups of songs', self.__session.get, DATES_API, params=params)
            if not r:
                break

            try:
                date_groups = r.json()[0]
                if len(date_groups) == 0:
                    break

                for date_group in date_groups:
                    yield date_group['grp']
            except BaseException as e:
                print('Cannot parse response as JSON: {}: {}'.format(type(e).__name__, e))
                break

            skip += self.__batch_size

    def __call(self,
               desc: str,
               call: Callable[..., Response],
               url: str,
               try_login: bool = True,
               **kwargs) -> Optional[Response]:
        try:
            r = call(url, timeout=self.__timeout, allow_redirects=False, **kwargs)
        except BaseException as e:
            print('Error while trying to {} @customsforge: {}: {}'.format(desc, type(e).__name__, e))
            return None

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            print('Error while trying to {} @customsforge: automatic login failed.'.format(desc))
            return None

        return self.__call(desc, call, url, try_login=False, **kwargs)
