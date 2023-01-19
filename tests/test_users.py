import pytest
from assertpy import assert_that

from sahyun_bot.users import Users
from sahyun_bot.users_settings import UserRank, User


@pytest.fixture
def fallback_users():
    return Users(streamer='sahyun')


def test_fallback(fallback_users):
    assert_user(fallback_users.user('sahyun'), rank=UserRank.ADMIN)
    assert_user(fallback_users.user('thegoodlike13'), rank=UserRank.UNKNW)
    assert_user(fallback_users.user('goodlikebot'), rank=UserRank.UNKNW)
    assert_user(fallback_users.user('sahyunbot'), rank=UserRank.UNKNW)


def test_no_elastic(live_users):
    assert_user(live_users.user('sahyun'), rank=UserRank.ADMIN, user_id=13144519)
    # assert_user(live_users.user('thegoodlike13'), rank=UserRank.FLWR, user_id=37103864)  deleted account
    assert_user(live_users.user('goodlikebot'), rank=UserRank.VWR, user_id=91770105)
    assert_user(live_users.user('sahyunbot'), rank=UserRank.FLWR, user_id=92152420)


def test_full_functionality(users):
    assert_user(users.user('sahyun'), rank=UserRank.ADMIN, user_id=13144519)
    assert_user(users.user('thegoodlike13'), rank=UserRank.ADMIN, user_id=37103864)
    assert_user(users.user('goodlikebot'), rank=UserRank.VWR, user_id=91770105)
    assert_user(users.user('sahyunbot'), rank=UserRank.BAN, user_id=92152420)


def test_remove_manual_rank(users):
    users.remove_manual('sahyunbot')
    assert_that(users.user('sahyunbot').rank).is_not_equal_to(UserRank.BAN)


def test_set_manual_rank(users):
    with users._manual('goodlikebot', UserRank.BAN):
        assert_user(users.user('goodlikebot'), rank=UserRank.BAN, user_id=91770105)


def assert_user(user: User, rank: UserRank = None, user_id: int = None):
    assert_that(user).is_not_none()
    assert_that(user.rank).is_equal_to(rank)
    assert_that(user.user_id).is_equal_to(user_id)
