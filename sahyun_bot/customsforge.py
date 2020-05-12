from typing import Iterator, Optional

import requests
from requests import Response
from requests.cookies import RequestsCookieJar


class CustomsForgeClient:
    def __init__(self, api_key: str, batch_size: int):
        self.__api_key = api_key
        self.__batch_size = batch_size

        self.__cookies = RequestsCookieJar()

    def login(self, username: str, password: str) -> bool:
        self.__cookies = RequestsCookieJar()

        data = {
            'ips_username': username,
            'ips_password': password,
            'auth_key': self.__api_key,
            'rememberMe': '1',
            'referer': MAIN_PAGE
        }
        r = self.__call('login', requests.post, LOGIN, data, is_login=True)
        if r is None:
            return False

        if not r.headers.get('Location', '') == MAIN_PAGE:
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
            r = self.__call('find groups of songs', requests.get, DATES, data)
            if not r:
                break

            if r.is_redirect:
                print('Not logged in - maybe we should automate that?')
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

    def __call(self, description: str, call, url: str, data: dict, is_login=False) -> Optional[Response]:
        try:
            r = call(url, data, timeout=300, allow_redirects=False, cookies=None if is_login else self.__cookies)
            self.__cookies.update(r.cookies)
            return r
        except BaseException as e:
            print('Error while trying to {} @customsforge: {}: {}'.format(description, type(e).__name__, e))
            return None


MAIN_PAGE = 'http://customsforge.com/'
LOGIN = 'http://customsforge.com/index.php?app=core&module=global&section=login&do=process'
DATES = 'http://ignition.customsforge.com/search/get_content?group=updated'
