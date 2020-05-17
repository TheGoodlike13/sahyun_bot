from assertpy import assert_that
from httmock import HTTMock

from sahyun_bot.customsforge import To
from tests.mock_customsforge import server_down, customsforge
from tests.mock_settings import *


def test_server_down(cf, cf_off):
    with HTTMock(server_down):
        for c in [cf, cf_off]:
            assert_that(c.login(MOCK_USER, MOCK_PASS)).is_false()
            assert_that(list(c.dates())).is_empty()
            assert_that(list(c.cdlcs())).is_empty()
            assert_that(c.direct_link('any')).is_empty()


def test_offline(cf_off):
    with HTTMock(customsforge):
        assert_that(list(cf_off.dates())).is_empty()
        assert_that(list(cf_off.cdlcs())).is_empty()
        assert_that(cf_off.direct_link('any')).is_empty()


def test_manual_login(cf, cf_off):
    with HTTMock(customsforge):
        for c in [cf, cf_off]:
            assert_that(c.login(MOCK_USER, MOCK_PASS)).is_true()
            assert_that(c.login(MOCK_USER, MOCK_PASS + ' but wrong')).is_false()


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


def test_dates(cf):
    with HTTMock(customsforge):
        assert_that(list(cf.dates())).is_length(6)
        assert_that(list(cf.dates(since=TEST_DATE))).contains(str(TEST_DATE)).is_length(1)


def test_cdlcs(cf):
    with HTTMock(customsforge):
        assert_that(list(cf.cdlcs())).is_length(6)
        assert_that([cdlc.get('id') for cdlc in cf.cdlcs(since=TEST_DATE)]).contains(49886).is_length(1)


def test_direct_link(cf):
    with HTTMock(customsforge):
        assert_that(cf.direct_link(49706)).is_equal_to('magical_link')
        assert_that(cf.direct_link('12990')).is_equal_to('magical_link')

        assert_that(cf.direct_link('any other id')).is_empty()


def test_to_cdlc():
    info_link = 'http://customsforge.com/page/customsforge_rs_2014_cdlc.html/_/pc-enabled-rs-2014-cdlc/' \
                'paradise-deep-mountain-r49886'
    assert_that(To.cdlc(MOCK_CDLC[str(TEST_DATE)])).contains_entry(
        _id='49886',

        id=49886,
        artist='ZUN',
        title='Paradise ~ Deep Mountain',
        album='Perfect Cherry Blossom OST',
        tuning='estandard',
        instrument_info=[],
        parts=['lead'],
        platforms=['pc'],
        has_dynamic_difficulty=True,
        is_official=False,

        author='coldrampage',
        version='1.0',

        download='https://customsforge.com/process.php?id=49886',
        info=info_link,
        video='https://youtu.be/iuc7L50iUhw',
        art='https://i.imgur.com/YOA0laU.png',

        snapshot_timestamp=1589556530,
    )
