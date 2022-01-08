from datetime import date
from typing import Dict

from httmock import all_requests

from sahyun_bot.customsforge import LOGIN_FORM_CSRF, LOGIN_FORM_EMAIL, LOGIN_FORM_PASSWORD

MOCK_CSRF = 'acdc'
MOCK_EMAIL = 'email'
MOCK_PASS = 'pass'

MOCK_COOKIE_KEY = '-login_cookie'
MOCK_COOKIE_VALUE = 'login_value'
MOCK_COOKIE_DOMAIN = '.customsforge.com'
MOCK_COOKIE_PATH = '/'
MOCK_COOKIE = MOCK_COOKIE_KEY + '=' + MOCK_COOKIE_VALUE
MOCK_SET_COOKIE = f'{MOCK_COOKIE}; path={MOCK_COOKIE_PATH}; domain={MOCK_COOKIE_DOMAIN}; httponly'

VALID_LOGIN_FORM = frozenset([
    f'{LOGIN_FORM_CSRF}={MOCK_CSRF}',
    f'{LOGIN_FORM_EMAIL}={MOCK_EMAIL}',
    f'{LOGIN_FORM_PASSWORD}={MOCK_PASS}',
])

TEST_DATE = date.fromisoformat('2020-05-15')
MOCK_CDLC: Dict[str, dict] = {}


@all_requests
def server_down(url, request):
    raise Exception('Failure as expected')
