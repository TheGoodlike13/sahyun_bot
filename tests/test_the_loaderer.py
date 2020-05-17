from assertpy import assert_that
from httmock import HTTMock

from sahyun_bot.elastic import CustomDLC
from sahyun_bot.the_loaderer import load
from tests.mock_customsforge import customsforge


def test_loading_from_start(cf, es_fresh):
    with HTTMock(customsforge):
        load(cf).result()

    assert_that([hit.link for hit in CustomDLC.search().filter('term', from_auto_index=True)])\
        .is_length(6)\
        .contains_only('magical_link')


def test_loading_continued(cf, es):
    # pretend we loaded songs 2 days before TEST_DATE
    CustomDLC.get(49841).update(from_auto_index=True)

    with HTTMock(customsforge):
        load(cf).result()

    hits = list(CustomDLC.search().filter('term', from_auto_index=True).sort('snapshot_timestamp'))
    assert_that(hits).is_length(3)

    for hit in hits:
        assert_that(hit.link).is_equal_to('magical_link')
