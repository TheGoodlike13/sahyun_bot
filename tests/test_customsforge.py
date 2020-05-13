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


def test_login_via_call(client):
    with HTTMock(request_fail):
        assert_that(client.login('user', 'pass')).is_false()

    with HTTMock(customsforge):
        assert_that(client.login('user', 'pass')).is_true()
        assert_that(client.login('user', 'wrong_pass')).is_false()


def test_login_via_config(client_with_login):
    with HTTMock(customsforge):
        assert_that(client_with_login.login()).is_true()


def test_login_via_cookie_jar(client_with_cookies):
    with HTTMock(customsforge):
        assert_logged_in(client_with_cookies)


def test_login_automatically(client_with_login):
    with HTTMock(customsforge):
        assert_logged_in(client_with_login)


def test_dates(client):
    with HTTMock(request_fail):
        assert_that(list(client.dates())).is_empty()

    with HTTMock(customsforge):
        assert_that(list(client.dates())).is_empty()

        client.login('user', 'pass')
        assert_that(list(client.dates())).is_length(2).contains('2020-05-11', '2020-05-12')


def test_cdlcs(client):
    with HTTMock(request_fail):
        assert_that(list(client.cdlcs())).is_empty()

    with HTTMock(customsforge):
        assert_that(list(client.cdlcs())).is_empty()

        client.login('user', 'pass')
        assert_that(list(client.cdlcs())).is_length(2).contains(CDLC(**CDLC_JSON_1), CDLC(**CDLC_JSON_2))


def test_cdlc_parsing():
    assert_cdlc_1(CDLC(**CDLC_JSON_1))
    assert_cdlc_2(CDLC(**CDLC_JSON_2))


def assert_logged_in(client):
    # for now we just perform a random call which returns expected values only when logged in
    assert_that(list(client.dates())).is_length(2).contains('2020-05-11', '2020-05-12')


def assert_cdlc_1(cdlc_json):
    assert_that(cdlc_json.id).is_equal_to('3492')
    assert_that(cdlc_json.artist).is_equal_to('Porno Graffiti')
    assert_that(cdlc_json.title).is_equal_to('Hitori No Yoru(Great Teacher Onizuka)')
    assert_that(cdlc_json.album).is_equal_to('Romantist Egoist')
    assert_that(cdlc_json.author).is_equal_to('BMB')
    assert_that(cdlc_json.tuning).is_equal_to('estandard')
    assert_that(cdlc_json.parts).is_length(3).contains('lead', 'rhythm', 'bass')
    assert_that(cdlc_json.platforms).is_length(2).contains('pc', 'mac')
    assert_that(cdlc_json.hasDynamicDifficulty).is_equal_to(False)
    assert_that(cdlc_json.isOfficial).is_equal_to(False)
    assert_that(cdlc_json.lastUpdated).is_equal_to(1398197782)
    assert_that(cdlc_json.musicVideo).is_equal_to('http://youtu.be/kDh3D2ewiNs')

    assert_that(cdlc_json.link()).is_equal_to('https://customsforge.com/process.php?id=3492')


def assert_cdlc_2(cdlc_json):
    assert_that(cdlc_json.id).is_equal_to('8623')
    assert_that(cdlc_json.artist).is_equal_to('Blur')
    assert_that(cdlc_json.title).is_equal_to('Song 2')
    assert_that(cdlc_json.album).is_equal_to('Blur')
    assert_that(cdlc_json.author).is_equal_to('CustomsForge')
    assert_that(cdlc_json.tuning).is_equal_to('estandard')
    assert_that(cdlc_json.parts).is_length(3).contains('lead', 'bass', 'vocals')
    assert_that(cdlc_json.platforms).is_length(4).contains('pc', 'mac', 'xbox360', 'ps3')
    assert_that(cdlc_json.hasDynamicDifficulty).is_equal_to(True)
    assert_that(cdlc_json.isOfficial).is_equal_to(True)
    assert_that(cdlc_json.lastUpdated).is_equal_to(1318910400)
    assert_that(cdlc_json.musicVideo).is_equal_to('https://www.youtube.com/watch?v=SSbBvKaM6sk')

    assert_that(cdlc_json.link()).is_equal_to('https://customsforge.com/process.php?id=8623')


@all_requests
def request_fail(url, request):
    raise ValueError('Any exception during request')


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
    if 'skip=0' in url.query:
        return group('2020-05-11')

    if 'skip=1' in url.query:
        return group('2020-05-12')

    return group()


def group(date: str = None):
    return values([
        [{'grp': date}] if date else [],
        [{'total': 2}]
    ])


def cdlcs_mock(url, request):
    if 'skip=0' in url.query:
        if '2020-05-11' in url.query:
            return values([CDLC_JSON_1])

        if '2020-05-12' in url.query:
            return values([CDLC_JSON_2])

    return values([])


def cdlc(cdlc_json=None):
    values([cdlc_json] if cdlc_json else [])


def values(v):
    return {
        'status_code': 200,
        'content': v,
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

CDLC_JSON_1 = {
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

CDLC_JSON_2 = {
    "artist": "Blur",
    "0": "Blur",
    "title": "Song 2",
    "1": "Song 2",
    "album": "Blur",
    "2": "Blur",
    "tuning": "estandard",
    "3": "estandard",
    "parts": "lead,bass,vocals",
    "4": "lead,bass,vocals",
    "dd": "yes",
    "5": "yes",
    "platforms": ",pc,mac,xbox360,ps3,",
    "6": ",pc,mac,xbox360,ps3,",
    "rating": 49424,
    "7": 49424,
    "updated": 1318910400,
    "8": 1318910400,
    "member": "CustomsForge",
    "9": "CustomsForge",
    "furl": "song-2",
    "10": "song-2",
    "id": 8623,
    "11": 8623,
    "added": 1318910400,
    "12": 1318910400,
    "version": "1.0",
    "13": "1.0",
    "downloads": 3084,
    "14": 3084,
    "official": "Yes",
    "15": "Yes",
    "direct": "http://www.theriffrepeater.com/rocksmith-2014-setlist/rocksmith-setlist/",
    "16": "http://www.theriffrepeater.com/rocksmith-2014-setlist/rocksmith-setlist/",
    "music_video": "https://www.youtube.com/watch?v=SSbBvKaM6sk",
    "17": "https://www.youtube.com/watch?v=SSbBvKaM6sk",
    "instrument_info": None,
    "18": None,
    "album_art": "http://upload.wikimedia.org/wikipedia/en/b/b1/Blur_Blur.jpg",
    "19": "http://upload.wikimedia.org/wikipedia/en/b/b1/Blur_Blur.jpg",
    "like_rel_id": None,
    "20": None,
    "follow": None,
    "21": None,
    "record_id": None,
    "22": None,
    "saved": None,
    "23": None
}
