from assertpy import assert_that


def test_api_accessible(twitchy):
    assert_that(twitchy.is_following(streamer='sahyun', viewer='thegoodlike13')).is_true()


def test_user_id(twitchy):
    assert_that(twitchy.get_id('sahyun')).is_equal_to('13144519')
