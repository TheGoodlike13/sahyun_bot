import pytest
from assertpy import assert_that
from httmock import all_requests, HTTMock

from sahyun_bot.customsforge import CustomsForgeClient, MAIN_PAGE


@pytest.fixture
def client():
    return CustomsForgeClient('key')


def test_login(client):
    with HTTMock(customsforge):
        assert_that(client.login('user', 'pass')).is_true()
        assert_that(client.login('user', 'wrong_pass')).is_false()

    with HTTMock(request_fail):
        assert_that(client.login('user', 'pass')).is_false()


def test_dates(client):
    pass


@all_requests
def request_fail(url, request):
    raise ValueError('Any exception during request')


@all_requests
def customsforge(url, request):
    if 'index.php' in url.path:
        return login_mock(url, request)

    if 'get_content' in url.path:
        return dates_mock(url, request)

    return {
        'status_code': 404,
        'content': 'Unexpected URL'
    }


def login_mock(url, request):
    if all(param in request.body for param in VALID_LOGIN_FORM):
        return {
            'status_code': 302,
            'content': 'Redirect to main page',
            'headers': {
                'Set-Cookie': 'login_cookie',
                'Location': MAIN_PAGE
            }
        }

    return {
        'status_code': 200,
        'content': 'Sign-in error page'
    }


def dates_mock(url, request):
    pass


VALID_LOGIN_FORM = {
    'ips_username=user',
    'ips_password=pass',
    'auth_key=key'
}
