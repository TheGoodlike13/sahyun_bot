import pytest
from assertpy import assert_that

from sahyun_bot.commander import TheCommander
from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.users_settings import User, UserRank


@pytest.fixture
def commander(users):
    return TheCommander(us=users)


def test_not_command(commander, hook):
    with commander.executest('_test', '', hook):
        assert_that(hook.all()).is_empty()

    with commander.executest('_test', 'Time for some random IRC chatter!', hook):  # !time is a command
        assert_that(hook.all()).is_empty()


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


def test_ask_to_follow(commander, hook, es_fresh):
    commander._add_command(TestFollow())

    with commander.executest('goodlikebot', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('Please follow the channel to use !testfollow')

    commander._users.set_manual('goodlikebot', UserRank.FLWR)  # simulate a follow

    with commander.executest('goodlikebot', '!testfollow', hook):
        assert_that(hook.all_to_sender()).contains('Thanks for following!')


class TestFollow(Command):
    def min_rank(self) -> UserRank:
        return UserRank.FLWR

    def execute(self, user: User, args: str, respond: ResponseHook):
        respond.to_sender('Thanks for following!')
