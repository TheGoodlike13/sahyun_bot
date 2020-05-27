from datetime import date
from typing import Dict

from httmock import all_requests

MOCK_USER = 'user'
MOCK_PASS = 'pass'
MOCK_API_KEY = 'key'

MOCK_COOKIE_KEY = '-login_cookie'
MOCK_COOKIE_VALUE = 'login_value'
MOCK_COOKIE_DOMAIN = '.customsforge.com'
MOCK_COOKIE_PATH = '/'
MOCK_COOKIE = MOCK_COOKIE_KEY + '=' + MOCK_COOKIE_VALUE
MOCK_SET_COOKIE = f'{MOCK_COOKIE}; path={MOCK_COOKIE_PATH}; domain={MOCK_COOKIE_DOMAIN}; httponly'

VALID_LOGIN_FORM = frozenset([
    f'ips_username={MOCK_USER}',
    f'ips_password={MOCK_PASS}',
    f'auth_key={MOCK_API_KEY}',
])

TEST_DATE = date.fromisoformat('2020-05-15')
MOCK_CDLC: Dict[str, dict] = {}


@all_requests
def server_down(url, request):
    raise Exception('Failure as expected')
