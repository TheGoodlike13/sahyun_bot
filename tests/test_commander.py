from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.users_settings import User, UserRank


def test_not_command(commander, hook):
    with commander.executest(hook, ''):
        hook.assert_silent_failure()

    with commander.executest(hook, 'Time for some random IRC chatter!'):  # !time is a command
        hook.assert_silent_failure()


def test_commands_resolved_automatically(commander, hook):
    with commander.executest(hook, '!time'):
        hook.assert_success('The time is now ', ' UTC')

    with commander.executest(hook, '!TIME'):
        hook.assert_success('The time is now ', ' UTC')


def test_command_authorization(commander, hook):
    # banned user
    with commander.executest(hook, '!time', 'sahyunbot'):
        hook.assert_silent_failure()

    # admin
    with commander.executest(hook, '!time', 'sahyun'):
        hook.assert_success()

    # manual admin
    with commander.executest(hook, '!time', 'thegoodlike13'):
        hook.assert_success()

    # console or equivalent
    with commander.executest(hook, '!time', '_console'):
        hook.assert_success()


def test_ask_to_follow_and_user_downtime(commander, hook):
    commander._add_command(TestFollow())

    with commander.executest(hook, '!testfollow', 'goodlikebot'):
        hook.assert_failure('Please follow the channel to use !testfollow')

    with commander._users._manual('goodlikebot', UserRank.FLWR):  # simulate a follow
        with commander.executest(hook, '!testfollow', 'goodlikebot'):
            hook.assert_success('Thanks for following!')

        with commander.executest(hook, '!testfollow', 'goodlikebot'):  # user downtime
            hook.assert_failure('You can use !testfollow again in ', ' seconds')

    commander._users.set_manual('thegoodlike13', UserRank.FLWR)  # we need another follower to see downtime is user only
    with commander.executest(hook, '!testfollow', 'thegoodlike13'):
        hook.assert_success('Thanks for following!')


def test_global_downtime(commander, hook, live_users):
    commander._users = live_users  # fewer admins, easier to test

    # first use is free
    with commander.executest(hook, '!time', 'goodlikebot'):
        hook.assert_success()

    # downtime
    with commander.executest(hook, '!time', 'goodlikebot'):
        hook.assert_silent_failure()

    # downtime is global
    with commander.executest(hook, '!time', 'thegoodlike13'):
        hook.assert_silent_failure()

    # but not for admins
    with commander.executest(hook, '!time', 'sahyun'):
        hook.assert_success()


def test_no_downtime_for_failure(commander, hook):
    commander._add_command(Fail())

    with commander.executest(hook, '!fail', 'goodlikebot'):
        hook.assert_failure('I fail')

    # no downtime because command didn't succeed
    with commander.executest(hook, '!fail', 'goodlikebot'):
        hook.assert_failure('I fail')


class TestFollow(Command):
    def min_rank(self) -> UserRank:
        return UserRank.FLWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        respond.to_sender('Thanks for following!')


class Fail(Command):
    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        return respond.to_sender('I fail')
