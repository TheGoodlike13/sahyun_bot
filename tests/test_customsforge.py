from datetime import timedelta

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


def test_calculate_date_skip_continuous_release(cf):
    # 1) CDLCs are produced every day
    # 2) we ask for a fairly recent update
    since = TEST_DATE - timedelta(days=5)
    date_count = 100
    assert_that(cf.calculate_date_skip(since, date_count)).is_equal_to(92)


def test_calculate_date_skip_vacation(cf):
    # 1) CDLCs *were* produced every day, but there was a 100 day break, followed by new release
    # 2) we ask for update from before the break
    since = TEST_DATE - timedelta(days=100)
    date_count = 101
    assert_that(cf.calculate_date_skip(since, date_count)).is_equal_to(0)
