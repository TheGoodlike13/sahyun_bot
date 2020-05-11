import pytest
from assertpy import assert_that
from httmock import all_requests, HTTMock

from sahyun_bot.customsforge import CustomsForgeClient, MAIN_PAGE_URL


@pytest.fixture
def client():
    return CustomsForgeClient('key')


@all_requests
def login(url, request):
    for data in CORRECT_LOGIN_DATA:
        if data not in request.body:
            return {
                'status_code': 200,
                'content': 'Sign-in page'
            }

    return {
        'status_code': 302,
        'content': 'Redirect to main page',
        'headers': {
            'Set-Cookie': 'login_cookie',
            'Location': MAIN_PAGE_URL
        }
    }


@all_requests
def login_fail(url, request):
    raise ValueError('Any exception during request')


def test_login(client):
    with HTTMock(login):
        assert_that(client.login('user', 'pass')).is_true()

    with HTTMock(login):
        assert_that(client.login('user', 'wrong_pass')).is_false()

    with HTTMock(login_fail):
        assert_that(client.login('user', 'pass')).is_false()


CORRECT_LOGIN_DATA = {
    'ips_username=user',
    'ips_password=pass',
    'auth_key=key'
}
