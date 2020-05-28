import pytest
from assertpy import assert_that

from sahyun_bot.commander import TheCommander
from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.down import Downtime
from sahyun_bot.users_settings import User, UserRank


@pytest.fixture
def commander(users):
    downtime = {
        'fail': '3600',
        'time': '30',
        'testfollow': '30:1',
    }
    return TheCommander(us=users, dt=Downtime(config=downtime))


def test_not_command(commander, hook):
    with commander.executest('_test', '', hook):
        assert_that(hook.all_back()).is_empty()

    with commander.executest('_test', 'Time for some random IRC chatter!', hook):  # !time is a command
        assert_that(hook.all_back()).is_empty()


def test_commands_resolved_automatically(commander, hook):
    with commander.executest('_test', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')

    with commander.executest('_test', '!TIME', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')


def test_command_authorization(commander, hook):
    # banned user
    with commander.executest('sahyunbot', '!time', hook):
        assert_that(hook.all_to_sender()).is_empty()

    # admin
    with commander.executest('sahyun', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')

    # manual admin
    with commander.executest('thegoodlike13', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')

    # console or equivalent
    with commander.executest('_test', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')


def test_ask_to_follow_and_user_downtime(commander, hook, es_fresh):
    commander._add_command(TestFollow())

    with commander.executest('goodlikebot', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('Please follow the channel to use !testfollow')

    commander._users.set_manual('goodlikebot', UserRank.FLWR)  # simulate a follow

    with commander.executest('goodlikebot', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('Thanks for following!')

    # user downtime
    with commander.executest('goodlikebot', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('You can use !testfollow again in ', ' seconds')

    commander._users.set_manual('thegoodlike13', UserRank.FLWR)  # we need another follower to see downtime is user only
    with commander.executest('thegoodlike13', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('Thanks for following!')


def test_global_downtime(commander, hook, live_users):
    commander._users = live_users  # fewer admins, easier to test

    # first use is free
    with commander.executest('goodlikebot', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')

    # downtime
    with commander.executest('goodlikebot', '!time', hook):
        assert_that(hook.all_to_sender()).is_empty()

    # downtime is global
    with commander.executest('thegoodlike13', '!time', hook):
        assert_that(hook.all_to_sender()).is_empty()

    # but not for admins
    with commander.executest('sahyun', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')


def test_no_downtime_for_failure(commander, hook):
    commander._add_command(Fail())

    with commander.executest('goodlikebot', '!fail', hook):
        assert_that(hook.all_to_sender()).contains('I fail')
        assert_that(hook.all_to_debug()).contains('failure')

    # no downtime because command didn't succeed
    with commander.executest('goodlikebot', '!fail', hook):
        assert_that(hook.all_to_sender()).contains('I fail')


class TestFollow(Command):
    def min_rank(self) -> UserRank:
        return UserRank.FLWR

    def execute(self, user: User, args: str, respond: ResponseHook) -> bool:
        respond.to_sender('Thanks for following!')
        return True


class Fail(Command):
    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, args: str, respond: ResponseHook) -> bool:
        respond.to_sender('I fail')
        return False
