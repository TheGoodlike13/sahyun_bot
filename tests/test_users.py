import pytest
from assertpy import assert_that

from sahyun_bot.users import Users
from sahyun_bot.users_settings import UserRank, User


@pytest.fixture
def users(twitchy, es):
    return Users(streamer='sahyun', tw=twitchy, use_elastic=True)


@pytest.fixture
def live_users(twitchy, es):
    return Users(streamer='sahyun', tw=twitchy)


@pytest.fixture
def fallback_users():
    return Users(streamer='sahyun')


def test_fallback(fallback_users):
    assert_user(fallback_users.get('sahyun'), rank=UserRank.ADMIN)
    assert_user(fallback_users.get('thegoodlike13'), rank=UserRank.UNKNW)


def test_no_elastic(live_users):
    assert_user(live_users.get('sahyun'), rank=UserRank.ADMIN, user_id='13144519')
    assert_user(live_users.get('thegoodlike13'), rank=UserRank.FLWR, user_id='37103864')
    assert_user(live_users.get('goodlikebot'), rank=UserRank.VWR, user_id='91770105')


def test_full_functionality(users):
    assert_user(users.get('sahyun'), rank=UserRank.ADMIN, user_id='13144519')
    assert_user(users.get('thegoodlike13'), rank=UserRank.ADMIN, user_id='37103864')
    assert_user(users.get('goodlikebot'), rank=UserRank.VWR, user_id='91770105')


def test_set_manual_rank(users):
    users.set_manual('sahyunbot', UserRank.BAN)
    assert_user(users.get('sahyunbot'), rank=UserRank.BAN, user_id='92152420')


def assert_user(user: User, rank: UserRank = None, user_id: str = None):
    assert_that(user).is_not_none()
    assert_that(user.rank).is_equal_to(rank)
    assert_that(user.user_id).is_equal_to(user_id)
