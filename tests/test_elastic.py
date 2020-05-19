from assertpy import assert_that

from sahyun_bot.elastic import CustomDLC


def test_properties(es):
    cdlc = CustomDLC.get('49874')
    assert_that(cdlc.full_title).is_equal_to("Trey Parker - Jackin' It In San Diego")
    assert_that(cdlc.link).is_equal_to('https://customsforge.com/process.php?id=49874')

    cdlc.update(direct_download='direct_link')

    same_cdlc = list(CustomDLC.search().query('match', id='49874'))
    assert_that(same_cdlc).is_length(1)
    assert_that(same_cdlc[0].link).is_equal_to('direct_link')


def test_last_auto_index_time(es):
    assert_that(CustomDLC.latest_auto_time()).is_none()

    CustomDLC.get('49706').update(from_auto_index=True)

    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1589092730)


def test_request(es):
    assert_that(CustomDLC.request('definitely not here')).is_empty()

    cdlcs = CustomDLC.request('paradise')
    assert_that(cdlcs).is_length(1)
    assert_that(cdlcs[0].full_title).is_equal_to('ZUN - Paradise ~ Deep Mountain')
