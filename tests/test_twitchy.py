from assertpy import assert_that
from httmock import HTTMock

from tests.mock_twitch_extras import twitch_hosts


def test_api_accessible(twitchy):
    assert_that(twitchy.is_following(streamer='sahyun', viewer='thegoodlike13')).is_true()
    assert_that(twitchy.is_following(streamer='sahyun', viewer='goodlikebot')).is_false()
    assert_that(twitchy.is_following(streamer='sahyun', viewer='_not_possible')).is_false()
    assert_that(twitchy.is_following(streamer='_not_possible', viewer='sahyun')).is_false()


def test_user_id(twitchy):
    assert_that(twitchy.get_id('sahyun')).is_equal_to('13144519')
    assert_that(twitchy.get_id('_not_possible')).is_none()


def test_hosts(twitchy):
    with HTTMock(twitch_hosts):
        assert_that(twitchy.hosts('thegoodlike13')).is_empty()
        assert_that(twitchy.hosts('sahyun')).contains_only('thegoodlike13')
