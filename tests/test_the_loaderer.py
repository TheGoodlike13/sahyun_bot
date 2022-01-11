from assertpy import assert_that
from httmock import HTTMock

from sahyun_bot.elastic import CustomDLC
from tests.mock_customsforge import customsforge


def test_loading_from_start(tl):
    with HTTMock(customsforge):
        tl.load()

    assert_that(list(CustomDLC.search().filter('term', from_auto_index=True))).is_length(6)


def test_loading_continued(tl):
    # pretend we loaded cdlcs 2 days before TEST_DATE
    for cdlc_id in ['65171', '65172', '65173', '65174']:
        CustomDLC(_id=cdlc_id).update(from_auto_index=True, direct_download='fake')

    with HTTMock(customsforge):
        tl.load()

    hits = list(CustomDLC.search().filter('term', from_auto_index=True).exclude('term', direct_download='fake'))
    # the only updated cdlcs are from the last two days (one each), and the latest cdlc before
    assert_that(hits).is_length(3)
