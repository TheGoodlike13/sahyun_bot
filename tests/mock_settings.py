from datetime import date

MOCK_USER = 'user'
MOCK_PASS = 'pass'
MOCK_API_KEY = 'key'

MOCK_COOKIE_KEY = '-login_cookie'
MOCK_COOKIE_VALUE = 'login_value'
MOCK_COOKIE_DOMAIN = '.customsforge.com'
MOCK_COOKIE_PATH = '/'
MOCK_COOKIE = MOCK_COOKIE_KEY + '=' + MOCK_COOKIE_VALUE
MOCK_SET_COOKIE = '{}; path={}; domain={}; httponly'.format(MOCK_COOKIE, MOCK_COOKIE_PATH, MOCK_COOKIE_DOMAIN)

VALID_LOGIN_FORM = frozenset([
    'ips_username={}'.format(MOCK_USER),
    'ips_password={}'.format(MOCK_PASS),
    'auth_key={}'.format(MOCK_API_KEY),
])

TEST_DATE = date.fromisoformat('2020-05-15')
MOCK_CDLC = {}
