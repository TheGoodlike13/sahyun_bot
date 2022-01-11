from assertpy import assert_that
from elasticsearch import NotFoundError

from sahyun_bot.elastic import CustomDLC


def test_properties(es_cdlc):
    cdlc = CustomDLC.get(65175)
    assert_that(cdlc.full_title).is_equal_to("Yazoo - Only You")
    assert_that(cdlc.link).is_equal_to('https://www.dropbox.com/sh/i3uj2fwxle0dag6/AAAgK-D506DtEXoH1NiJoKVBa?dl=0')


def test_last_auto_index_time(es_cdlc):
    assert_that(CustomDLC.latest_auto_time()).is_none()

    # this cdlc IS NOT the earliest in the index, so it will be considered non-continuous
    CustomDLC(_id=65173).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_none()
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1641340800)

    # this cdlc IS the earliest in the index, so it AND ONLY IT will be considered continuous
    CustomDLC(_id=65171).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1641340800)
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1641427200)

    # after this, all cdlcs marked as indexed are continuous, since no unmarked cdlcs are in between
    CustomDLC(_id=65172).update(from_auto_index=True)
    assert_that(CustomDLC.latest_auto_time()).is_equal_to(1641513600)
    assert_that(CustomDLC.earliest_not_auto()).is_equal_to(1641600000)


def test_request(es_cdlc):
    assert_that(list(CustomDLC.search('definitely not here'))).is_empty()

    cdlcs = list(CustomDLC.search('dad'))
    assert_that(cdlcs).is_length(1)
    assert_that(cdlcs[0].full_title).is_equal_to('Hockey Dad - I Wanna Be Everybody')


def test_partial_update_for_non_existent_document(es_cdlc):
    try:
        CustomDLC(_id=100000).update(id=100000)
        assert False  # exception should be thrown!
    except NotFoundError:
        assert_that(CustomDLC.get(100000, ignore=[404])).is_none()


def test_playable(es_cdlc):
    assert_that(CustomDLC.get(65172).is_playable).is_true()   # official is still playable
    assert_that(CustomDLC.get(65171).is_playable).is_false()  # no lead or rhythm
    assert_that(CustomDLC.get(65174).is_playable).is_false()  # no pc


def test_filtered_pools(es_cdlc):
    assert_that(list(CustomDLC.playable())).is_length(3)     # 3 mock CDLCs out of 6 are playable
    assert_that(list(CustomDLC.random_pool())).is_length(2)  # 1 of them is official


def test_random(es_cdlc):
    assert_that(CustomDLC.random('definitely not here')).is_none()

    assert_that(CustomDLC.random().id).is_in(65175, 65176)
