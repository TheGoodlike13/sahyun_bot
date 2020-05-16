import os
import pickle
from datetime import date

import pytest
from assertpy import assert_that
from httmock import all_requests, HTTMock
from requests.cookies import RequestsCookieJar

from sahyun_bot.customsforge import CustomsForgeClient, MAIN_PAGE, LOGIN_PAGE, TEST_COOKIE_FILE, Parse
from tests.test_values import *

test_date = date.fromisoformat('2020-05-15')


@pytest.fixture
def cf():
    return CustomsForgeClient(api_key='key',
                              batch_size=1,
                              cookie_jar_file=None,
                              get_today=lambda: test_date)


@pytest.fixture
def cf_with_credentials():
    return CustomsForgeClient(api_key='key',
                              batch_size=1,
                              username='user',
                              password='pass',
                              cookie_jar_file=None,
                              get_today=lambda: test_date)


@pytest.fixture
def cf_with_cookies():
    cookies = RequestsCookieJar()
    cookies.set('-login_cookie', 'login_value', domain='.customsforge.com', path='/')

    with open(TEST_COOKIE_FILE, 'wb') as jar:
        pickle.dump(cookies, jar)

    yield CustomsForgeClient(api_key='key',
                             batch_size=1,
                             cookie_jar_file=TEST_COOKIE_FILE,
                             get_today=lambda: test_date)

    if os.path.exists(TEST_COOKIE_FILE):
        os.remove(TEST_COOKIE_FILE)


def test_login_via_call(cf):
    with HTTMock(request_fail):
        assert_that(cf.login('user', 'pass')).is_false()

    with HTTMock(customsforge):
        assert_that(cf.login('user', 'pass')).is_true()
        assert_that(cf.login('user', 'wrong_pass')).is_false()


def test_login_via_config(cf_with_credentials):
    with HTTMock(customsforge):
        assert_that(cf_with_credentials.login()).is_true()


def test_login_via_cookie_jar(cf_with_cookies):
    with HTTMock(customsforge):
        assert_logged_in(cf_with_cookies)


def test_login_automatically(cf_with_credentials):
    with HTTMock(customsforge):
        assert_logged_in(cf_with_credentials)


def test_dates(cf):
    with HTTMock(request_fail):
        assert_that(list(cf.dates())).is_empty()

    with HTTMock(customsforge):
        assert_that(list(cf.dates())).is_empty()

        cf.login('user', 'pass')
        assert_that(list(cf.dates())).is_length(4).contains('2020-05-12', '2020-05-13', '2020-05-14', '2020-05-15')
        assert_that(list(cf.dates(since=test_date))).is_length(1).contains('2020-05-15')


def test_cdlcs(cf):
    with HTTMock(request_fail):
        assert_that(list(cf.cdlcs())).is_empty()

    with HTTMock(customsforge):
        assert_that(list(cf.cdlcs())).is_empty()

        cf.login('user', 'pass')
        assert_that(list(cf.cdlcs())).is_length(2).contains(Parse.cdlc(CDLC_JSON_1), Parse.cdlc(CDLC_JSON_2))
        assert_that(list(cf.cdlcs(since=test_date))).is_length(1).contains(Parse.cdlc(CDLC_JSON_2))


def test_direct_link(cf):
    with HTTMock(request_fail):
        assert_that(cf.direct_link('49410')).is_empty()

    with HTTMock(customsforge):
        assert_that(cf.direct_link('49410')).is_empty()

        cf.login('user', 'pass')
        assert_that(cf.direct_link('49410')).is_equal_to('magical_link')
        assert_that(cf.direct_link('100000')).is_empty()


def test_cdlc_parsing():
    assert_cdlc_1(Parse.cdlc(CDLC_JSON_1))
    assert_cdlc_2(Parse.cdlc(CDLC_JSON_2))
    assert_cdlc_3(Parse.cdlc(CDLC_JSON_3))


def assert_logged_in(cf):
    assert_that(cf.ping()).is_true()


def assert_cdlc_1(cdlc):
    assert_that(cdlc).contains_entry(
        _id='3492',
        artist='Porno Graffiti',
        title='Hitori No Yoru(Great Teacher Onizuka)',
        album='Romantist Egoist',
        author='BMB',
        tuning='estandard',
        parts=['lead', 'rhythm', 'bass'],
        platforms=['pc', 'mac'],
        has_dynamic_difficulty=False,
        is_official=False,
        version_timestamp=1398197782,
        music_video='https://youtu.be/kDh3D2ewiNs',
    )


def assert_cdlc_2(cdlc):
    assert_that(cdlc).contains_entry(
        _id='8623',
        artist='Blur',
        title='Song 2',
        album='Blur',
        author='CustomsForge',
        tuning='estandard',
        parts=['lead', 'bass', 'vocals'],
        platforms=['pc', 'mac', 'xbox360', 'ps3'],
        has_dynamic_difficulty=True,
        is_official=True,
        version_timestamp=1318910400,
        music_video='https://youtu.be/SSbBvKaM6sk',
    )


def assert_cdlc_3(cdlc):
    assert_that(cdlc).contains_entry(
        _id='49410',
        artist='Yellowcard',
        title='Hang You Up',
        album='When You\'re Through Thinking Say Yes',
        author='llfnv321',
        tuning='estandard',
        parts=['lead', 'rhythm', 'vocals'],
        platforms=['pc'],
        has_dynamic_difficulty=True,
        is_official=False,
        version_timestamp=1588013991,
        music_video='',
    )


@all_requests
def request_fail(url, request):
    raise ValueError('Failed as expected')


@all_requests
def customsforge(url, request):
    if 'index.php' in url.path:
        return login_mock(url, request)

    if not request.headers.get('Cookie', '') == '-login_cookie=login_value':
        return to_login_page()

    if 'get_content' in url.path:
        return dates_mock(url, request)

    if 'get_group_content' in url.path:
        return cdlcs_mock(url, request)

    if 'process.php' in url.path:
        return direct_link_mock(url, request)

    return {
        'status_code': 404,
        'content': 'Unexpected URL',
    }


def login_mock(url, request):
    if all(param in request.body for param in VALID_LOGIN_FORM):
        return to_main_page()

    return {
        'status_code': 200,
        'content': 'Sign-in error page',
    }


def dates_mock(url, request):
    if 'skip=0' in url.query:
        return group('2020-05-12')

    if 'skip=1' in url.query:
        return group('2020-05-13')

    if 'skip=2' in url.query:
        return group('2020-05-14')

    if 'skip=3' in url.query:
        return group('2020-05-15')

    return values()


def group(date_str: str):
    return values([
        [{'grp': date_str}],
        [{'total': 4}]
    ])


def cdlcs_mock(url, request):
    if 'skip=0' in url.query:
        if '2020-05-14' in url.query:
            return values([CDLC_JSON_1])

        if '2020-05-15' in url.query:
            return values([CDLC_JSON_2])

    return values('[]')


def direct_link_mock(url, request):
    return to_direct_link('magical_link') if 'id=49410' in url.query else to_direct_link()


def values(v=None):
    return {
        'status_code': 200,
        'content': v,
    }


def to_main_page():
    return {
        'status_code': 302,
        'content': 'Redirect to main page - login successful!',
        'headers': {
            'Set-Cookie': '-login_cookie=login_value; path=/; domain=.customsforge.com; httponly',
            'Location': MAIN_PAGE,
        },
    }


def to_login_page():
    return {
        'status_code': 302,
        'content': 'Redirect to login page - login is required!',
        'headers': {
            'Location': LOGIN_PAGE,
        },
    }


def to_direct_link(link: str = ''):
    return {
        'status_code': 302,
        'content': 'Redirect to direct link - if one exists, that is!',
        'headers': {
            'Location': link,
        },
    }


VALID_LOGIN_FORM = {
    'ips_username=user',
    'ips_password=pass',
    'auth_key=key',
}
