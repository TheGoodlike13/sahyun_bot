from sahyun_bot.customsforge import LOGIN_PAGE, LOGIN_REDIRECT
from tests.mock_settings import *


@all_requests
def customsforge(url, request):
    if 'index.php' in url.path:
        return login_mock(url, request)

    if not request.headers.get('Cookie', '') == MOCK_COOKIE:
        return to_login_page()

    if 'ignition4' in url.hostname:
        return cdlcs_mock(url, request)

    return {
        'status_code': 404,
        'reason': 'Not Found',
        'content': 'Unexpected URL',
    }


def login_mock(url, request):
    if request.method == 'GET':
        return ok(f'Initial login page <input name="csrfKey" value="{MOCK_CSRF}">')

    if all(param in request.body.split('&') for param in VALID_LOGIN_FORM):
        return successful_login_redirect()

    return ok('Sign-in error page')


def cdlcs_mock(url, request):
    if 'draw' in url.query:
        return ok({
            'draw': 1,
            'recordsTotal': 6,
            'recordsFiltered': 6,
            'data': MOCK_CDLC if 'start=0' in url.query else []
        })

    return ok('Default ignition page. Used for pinging.')


def successful_login_redirect():
    return {
        'status_code': 301,
        'reason': 'Moved Temporarily',
        'content': 'Redirect to main page - login successful!',
        'headers': {
            'Set-Cookie': MOCK_SET_COOKIE,
            'Location': LOGIN_REDIRECT,
        },
    }


def to_login_page():
    return {
        'status_code': 301,
        'reason': 'Moved Temporarily',
        'content': 'Redirect to login page - login is required!',
        'headers': {
            'Location': LOGIN_PAGE,
        },
    }


def ok(content=None):
    return {
        'status_code': 200,
        'reason': 'OK',
        'content': content,
    }
