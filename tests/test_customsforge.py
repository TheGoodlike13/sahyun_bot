import os
import pickle

import pytest
from assertpy import assert_that
from httmock import all_requests, HTTMock
from requests.cookies import RequestsCookieJar

from sahyun_bot.customsforge import CustomsForgeClient, MAIN_PAGE, LOGIN_PAGE, TEST_COOKIE_FILE


@pytest.fixture
def client():
    return CustomsForgeClient(api_key='key', batch_size=1, cookie_jar_file=None)


@pytest.fixture
def client_with_login():
    return CustomsForgeClient(api_key='key', batch_size=1, username='user', password='pass', cookie_jar_file=None)


@pytest.fixture
def client_with_cookies():
    cookies = RequestsCookieJar()
    cookies.set('-login_cookie', 'login_value', domain='.customsforge.com', path='/')

    with open(TEST_COOKIE_FILE, 'wb') as jar:
        pickle.dump(cookies, jar)

    yield CustomsForgeClient(api_key='key', batch_size=1, cookie_jar_file=TEST_COOKIE_FILE)

    if os.path.exists(TEST_COOKIE_FILE):
        os.remove(TEST_COOKIE_FILE)


def test_login(client):
    with HTTMock(request_fail):
        assert_that(client.login('user', 'pass')).is_false()

    with HTTMock(customsforge):
        assert_that(client.login('user', 'pass')).is_true()
        assert_that(client.login('user', 'wrong_pass')).is_false()


def test_login_with_client_credentials(client_with_login):
    with HTTMock(customsforge):
        assert_that(client_with_login.login()).is_true()


def test_dates(client):
    with HTTMock(request_fail):
        assert_that(list(client.dates())).is_empty()

    with HTTMock(customsforge):
        assert_that(list(client.dates())).is_empty()

        client.login('user', 'pass')
        assert_that(list(client.dates())).is_length(2).contains('2020-05-11', '2020-05-12')


def test_dates_auto_login(client_with_login):
    with HTTMock(customsforge):
        assert_that(list(client_with_login.dates())).is_length(2).contains('2020-05-11', '2020-05-12')


def test_cookie_jar(client_with_cookies):
    with HTTMock(customsforge):
        assert_that(list(client_with_cookies.dates())).is_length(2).contains('2020-05-11', '2020-05-12')


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
        return to_main_page()

    return {
        'status_code': 200,
        'content': 'Sign-in error page'
    }


def dates_mock(url, request):
    if not request.headers.get('Cookie', '') == '-login_cookie=login_value':
        return to_login_page()

    if 'skip=2' in url.query:
        return group()

    return group('2020-05-11' if 'skip=0' in url.query else '2020-05-12')


def group(date: str = None):
    return {
        'status_code': 200,
        'content': [
            [{'grp': date}] if date else [],
            [{'total': 2}]
        ],
        # we have to return this, because httmock overrides session cookies with response cookies
        'headers': {
            'Set-Cookie': '-login_cookie=login_value; path=/; domain=.customsforge.com; httponly',
        }
    }


def to_main_page():
    return {
        'status_code': 302,
        'content': 'Redirect to main page - login successful!',
        'headers': {
            'Set-Cookie': '-login_cookie=login_value; path=/; domain=.customsforge.com; httponly',
            'Location': MAIN_PAGE
        }
    }


def to_login_page():
    return {
        'status_code': 302,
        'content': 'Redirect to login page - login is required!',
        'headers': {
            'Location': LOGIN_PAGE
        }
    }


VALID_LOGIN_FORM = {
    'ips_username=user',
    'ips_password=pass',
    'auth_key=key'
}
