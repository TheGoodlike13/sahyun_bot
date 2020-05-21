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

    # this cdlc IS NOT the earliest in the index, so it will be considered non-continuous
    CustomDLC(_id='49792').update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_none()

    # this cdlc IS the earliest in the index, so it AND ONLY IT will be considered continuous
    CustomDLC(_id='49706').update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1589092730)

    # after this, all cdlcs marked as indexed are continuous, since no unmarked cdlcs are in between
    CustomDLC(_id='12990').update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1589249216)


def test_request(es):
    assert_that(list(CustomDLC.request('definitely not here'))).is_empty()

    cdlcs = list(CustomDLC.request('paradise'))
    assert_that(cdlcs).is_length(1)
    assert_that(cdlcs[0].full_title).is_equal_to('ZUN - Paradise ~ Deep Mountain')
