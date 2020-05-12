from typing import Iterator, Optional

import requests
from requests import Response
from requests.cookies import RequestsCookieJar


class CustomsForgeClient:
    def __init__(self, api_key: str, batch_size: int, username=None, password=None):
        self.__api_key = api_key
        self.__batch_size = batch_size

        self.__username = username
        self.__password = password

        self.__cookies = RequestsCookieJar()

    def login(self, username=None, password=None) -> bool:
        if username and password:
            self.__username = username
            self.__password = password

        if not self.__username and not self.__password:
            print('Username and password were not provided.')
            return False

        self.__cookies = RequestsCookieJar()

        data = {
            'ips_username': self.__username,
            'ips_password': self.__password,
            'auth_key': self.__api_key,
            'rememberMe': '1',
            'referer': MAIN_PAGE
        }
        r = self.__call('login', requests.post, LOGIN_API, data, try_login=False)
        if r is None:
            return False

        if not r.is_redirect or not r.headers.get('Location', '') == MAIN_PAGE:
            print('Login failed. Please check your credentials.')
            return False

        return True

    def dates(self) -> Iterator[str]:
        skip = 0

        while True:
            data = {
                'skip': skip,
                'take': self.__batch_size
            }
            r = self.__call('find groups of songs', requests.get, DATES_API, data)
            if not r:
                break

            try:
                date_groups = r.json()[0]
                if len(date_groups) == 0:
                    break

                for date_group in date_groups:
                    yield date_group['grp']
            except BaseException as e:
                print('Cannot parse response as JSON: ' + type(e).__name__ + ': ' + str(e))
                break

            skip += self.__batch_size

    def __call(self, desc: str, call, url: str, data: dict, try_login=True) -> Optional[Response]:
        try:
            r = call(url, data, timeout=300, allow_redirects=False, cookies=self.__cookies)
        except BaseException as e:
            print('Error while trying to {} @customsforge: {}: {}'.format(desc, type(e).__name__, e))
            return None

        self.__cookies.update(r.cookies)

        if not try_login or not r.is_redirect or not r.headers.get('Location', '') == LOGIN_PAGE:
            return r

        if not self.login():
            print('Error while trying to {} @customsforge: automatic login failed.'.format(desc))
            return None

        return self.__call(desc, call, url, data, try_login=False)


MAIN_PAGE = 'http://customsforge.com/'
LOGIN_PAGE = 'https://customsforge.com/index.php?app=core&module=global&section=login'

LOGIN_API = 'https://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES_API = 'https://ignition.customsforge.com/search/get_content?group=updated'
