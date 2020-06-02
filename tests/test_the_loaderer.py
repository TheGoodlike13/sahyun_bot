from assertpy import assert_that
from httmock import HTTMock

from sahyun_bot.elastic import CustomDLC
from tests.mock_customsforge import customsforge


def test_loading_from_start(tl):
    with HTTMock(customsforge):
        tl.load()

    assert_that([hit.link for hit in CustomDLC.search().filter('term', from_auto_index=True)]) \
        .is_length(6) \
        .contains_only('magical_link')


def test_loading_continued(tl):
    # pretend we loaded cdlcs 2 days before TEST_DATE
    for cdlc_id in ['49706', '12990', '49792', '49841']:
        CustomDLC(_id=cdlc_id).update(from_auto_index=True)

    with HTTMock(customsforge):
        tl.load()

    hits = list(CustomDLC.search().filter('term', from_auto_index=True).filter('term', direct_download='magical_link'))
    # the only updated cdlcs are from the last two days (one each), and the latest cdlc before
    assert_that(hits).is_length(3)


def test_load_links(tl):
    # this simulates the scenario where link was empty due to error
    CustomDLC(_id=49841).update(direct_download='')

    with HTTMock(customsforge):
        tl.load_links()

    assert_that([hit.link for hit in CustomDLC.search()]) \
        .is_length(6) \
        .contains_only('magical_link')
