from assertpy import assert_that
from httmock import HTTMock

from sahyun_bot.elastic import CustomDLC
from sahyun_bot.the_loaderer import load, load_links
from tests.mock_customsforge import customsforge


def test_loading_from_start(cf, es_fresh):
    with HTTMock(customsforge):
        load(cf)

    assert_that([hit.link for hit in CustomDLC.search().filter('term', from_auto_index=True)])\
        .is_length(6)\
        .contains_only('magical_link')


def test_loading_continued(cf, es_fresh):
    # pretend we loaded songs 2 days before TEST_DATE
    CustomDLC.get(49841).update(from_auto_index=True)

    with HTTMock(customsforge):
        load(cf)

    hits = list(CustomDLC.search().filter('term', from_auto_index=True))
    assert_that(hits).is_length(3)

    for hit in hits:
        assert_that(hit.link).is_equal_to('magical_link')


def test_load_links(cf, es_fresh):
    # TODO: this simulates the scenario where link was empty due to error - does not work because ES was miss-configured
    # CustomDLC.get(49841).update(direct_download='')
    # print(CustomDLC.get(49841).to_dict())

    with HTTMock(customsforge):
        load_links(cf)

    assert_that([hit.link for hit in CustomDLC.search()])\
        .is_length(6)\
        .contains_only('magical_link')
