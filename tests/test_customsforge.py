import os
import pickle

import pytest
from assertpy import assert_that
from httmock import all_requests, HTTMock
from requests.cookies import RequestsCookieJar

from sahyun_bot.customsforge import CustomsForgeClient, MAIN_PAGE, LOGIN_PAGE, TEST_COOKIE_FILE, CDLC


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


def test_song_parsing():
    cdlc = CDLC(**SONG_JSON)
    assert_that(cdlc.id).is_equal_to('3492')
    assert_that(cdlc.artist).is_equal_to('Porno Graffiti')
    assert_that(cdlc.title).is_equal_to('Hitori No Yoru(Great Teacher Onizuka)')
    assert_that(cdlc.album).is_equal_to('Romantist Egoist')
    assert_that(cdlc.author).is_equal_to('BMB')
    assert_that(cdlc.tuning).is_equal_to('estandard')
    assert_that(cdlc.parts).is_length(3).contains('lead', 'rhythm', 'bass')
    assert_that(cdlc.platforms).is_length(2).contains('pc', 'mac')
    assert_that(cdlc.hasDynamicDifficulty).is_equal_to(False)
    assert_that(cdlc.isOfficial).is_equal_to(False)
    assert_that(cdlc.lastUpdated).is_equal_to(1398197782)
    assert_that(cdlc.musicVideo).is_equal_to('http://youtu.be/kDh3D2ewiNs')

    assert_that(cdlc.link()).is_equal_to('https://customsforge.com/process.php?id=3492')


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

SONG_JSON = {
    "artist": "Porno Graffiti",
    "0": "Porno Graffiti",
    "title": "Hitori No Yoru(Great Teacher Onizuka)",
    "1": "Hitori No Yoru(Great Teacher Onizuka)",
    "album": "Romantist Egoist",
    "2": "Romantist Egoist",
    "tuning": "estandard",
    "3": "estandard",
    "parts": ",lead,rhythm,bass,",
    "4": ",lead,rhythm,bass,",
    "dd": "no",
    "5": "no",
    "platforms": ",pc,mac,",
    "6": ",pc,mac,",
    "rating": 5057,
    "7": 5057,
    "updated": 1398197782,
    "8": 1398197782,
    "member": "BMB",
    "9": "BMB",
    "furl": "hitori-no-yorugreat-teacher-onizuka",
    "10": "hitori-no-yorugreat-teacher-onizuka",
    "id": 3492,
    "11": 3492,
    "added": 1398197770,
    "12": 1398197770,
    "version": "1.0",
    "13": "1.0",
    "downloads": 837,
    "14": 837,
    "official": "No",
    "15": "No",
    "direct": "",
    "16": "",
    "music_video": "http://youtu.be/kDh3D2ewiNs",
    "17": "http://youtu.be/kDh3D2ewiNs",
    "instrument_info": "",
    "18": "",
    "album_art": "http://www.jpopasia.com/img/album-covers/2/16933-hitorinoyoru-ywbi.jpg",
    "19": "http://www.jpopasia.com/img/album-covers/2/16933-hitorinoyoru-ywbi.jpg",
    "like_rel_id": None,
    "20": None,
    "follow": None,
    "21": None,
    "record_id": None,
    "22": None,
    "saved": None,
    "23": None
}
