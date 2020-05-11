import requests


class CustomsForgeClient:
    def __init__(self, api_key: str):
        self.__api_key = api_key
        self.__cookies = None

    def login(self, username: str, password: str):
        data = {
            'ips_username': username,
            'ips_password': password,
            'auth_key': self.__api_key,
            'rememberMe': '1',
            'referer': MAIN_PAGE_URL
        }
        try:
            r = requests.post(LOGIN_URL, data, allow_redirects=False)
        except BaseException as e:
            print('Could not login to customsforge: ' + type(e).__name__ + ': ' + str(e))
            return False

        if not r.headers.get('Location', '') == MAIN_PAGE_URL:
            print('Login failed. Please check your credentials.')
            return False

        self.__cookies = r.cookies
        return True


LOGIN_URL = 'http://customsforge.com/index.php?app=core&module=global&section=login&do=process'
MAIN_PAGE_URL = 'http://customsforge.com/'
