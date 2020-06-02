from assertpy import assert_that
from elasticsearch import NotFoundError

from sahyun_bot.elastic import CustomDLC


def test_properties(es_cdlc):
    cdlc = CustomDLC.get(49874)
    assert_that(cdlc.full_title).is_equal_to("Trey Parker - Jackin' It In San Diego")
    assert_that(cdlc.link).is_equal_to('https://customsforge.com/process.php?id=49874')

    cdlc.update(direct_download='direct_link')

    same_cdlc = list(CustomDLC.search().query('match', id='49874'))
    assert_that(same_cdlc).is_length(1)
    assert_that(same_cdlc[0].link).is_equal_to('direct_link')


def test_last_auto_index_time(es_cdlc):
    assert_that(CustomDLC.latest_auto_time()).is_none()

    # this cdlc IS NOT the earliest in the index, so it will be considered non-continuous
    CustomDLC(_id=49792).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_none()
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1589092730)

    # this cdlc IS the earliest in the index, so it AND ONLY IT will be considered continuous
    CustomDLC(_id=49706).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1589092730)
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1589162625)

    # after this, all cdlcs marked as indexed are continuous, since no unmarked cdlcs are in between
    CustomDLC(_id=12990).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1589249216)
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1589377216)


def test_request(es_cdlc):
    assert_that(list(CustomDLC.search('definitely not here'))).is_empty()

    cdlcs = list(CustomDLC.search('paradise'))
    assert_that(cdlcs).is_length(1)
    assert_that(cdlcs[0].full_title).is_equal_to('ZUN - Paradise ~ Deep Mountain')


def test_partial_update_for_non_existent_document(es_cdlc):
    try:
        CustomDLC(_id=100000).update(id=100000)
        assert False  # exception should be thrown!
    except NotFoundError:
        assert_that(CustomDLC.get(100000, ignore=[404])).is_none()


def test_playable(es_cdlc):
    assert_that(CustomDLC.get(49706).is_playable).is_true()   # official is still playable
    assert_that(CustomDLC.get(49792).is_playable).is_false()  # no pc
    assert_that(CustomDLC.get(49841).is_playable).is_false()  # no lead or rhythm


def test_filtered_pools(es_cdlc):
    assert_that(list(CustomDLC.playable())).is_length(4)     # 2 mock CDLCs out of 6 are not playable
    assert_that(list(CustomDLC.random_pool())).is_length(3)  # 1 more CDLC is official


def test_random(es_cdlc):
    assert_that(CustomDLC.random('definitely not here')).is_none()

    assert_that(CustomDLC.random().id).is_in(12990, 49874, 49886)
