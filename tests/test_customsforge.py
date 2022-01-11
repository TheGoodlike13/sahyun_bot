import os
import pickle
from datetime import timedelta

import pytest
from assertpy import assert_that
from httmock import HTTMock
from requests.cookies import RequestsCookieJar

from sahyun_bot.customsforge import To, CustomsforgeClient
from sahyun_bot.customsforge_settings import TEST_COOKIE_FILE
from tests.mock_customsforge import customsforge
from tests.mock_settings import *


@pytest.fixture
def cf_off():
    return CustomsforgeClient(batch_size=1,
                              cookie_jar_file=None,
                              get_today=lambda: TEST_DATE)


@pytest.fixture
def cf_cookies():
    cookies = RequestsCookieJar()
    cookies.set(MOCK_COOKIE_KEY, MOCK_COOKIE_VALUE, domain=MOCK_COOKIE_DOMAIN, path=MOCK_COOKIE_PATH)

    with open(TEST_COOKIE_FILE, 'wb') as jar:
        pickle.dump(cookies, jar)

    yield CustomsforgeClient(batch_size=1,
                             cookie_jar_file=TEST_COOKIE_FILE,
                             get_today=lambda: TEST_DATE)

    if os.path.exists(TEST_COOKIE_FILE):
        os.remove(TEST_COOKIE_FILE)


def test_server_down(cf, cf_off):
    with HTTMock(server_down):
        for c in [cf, cf_off]:
            assert_that(c.login(MOCK_EMAIL, MOCK_PASS)).is_false()
            assert_that(list(c.cdlcs())).is_empty()


def test_offline(cf_off):
    with HTTMock(customsforge):
        assert_that(list(cf_off.cdlcs())).is_empty()


def test_manual_login(cf, cf_off):
    with HTTMock(customsforge):
        for c in [cf, cf_off]:
            assert_that(c.login(MOCK_EMAIL, MOCK_PASS)).is_true()
            assert_that(c.login(MOCK_EMAIL, MOCK_PASS + ' but wrong')).is_false()


def test_re_log(cf, cf_off):
    with HTTMock(customsforge):
        assert_that(cf.login()).is_true()
        assert_that(cf_off.login()).is_false()


def test_auto_login(cf, cf_off):
    with HTTMock(customsforge):
        assert_that(cf.ping()).is_true()
        assert_that(cf_off.ping()).is_false()


def test_cookies(cf_cookies):
    with HTTMock(customsforge):
        assert_that(cf_cookies.ping()).is_true()


def test_cdlcs(cf):
    with HTTMock(customsforge):
        assert_that(list(cf.cdlcs())).is_length(6)

        before_test_date = TEST_DATE - timedelta(days=1)

        full_two_days = [cdlc['id'] for cdlc in cf.cdlcs(since=before_test_date)]
        assert_that(full_two_days).contains(65176, 65175).is_length(2)


def test_to_cdlc():
    assert_that(To.cdlc(MOCK_CDLC[0])).contains_entry(
        id=65176,
        artist='Hockey Dad',
        title='I Wanna Be Everybody',
        album='Blend Inn',
        tuning='E Standard',
        instrument_info=['ii_tremolo'],
        parts=['lead', 'bass', 'vocals'],
        platforms=['pc', 'mac'],
        has_dynamic_difficulty=False,
        is_official=False,

        author='AlQapone',
        version='1',

        direct_download='https://drive.google.com/file/d/1wUb2ukepPD9F0V8JeND0kT1kB6kmPJN-/view?usp=sharing',
        download='https://customsforge.com/process.php?id=65176',
        info='https://ignition4.customsforge.com/cdlc/65176',
        video='https://www.youtube.com/embed/WHNDUbHo2z0',
        art='https://f4.bcbits.com/img/0011797846_10.jpg',

        snapshot_timestamp=1641772800,
    )
