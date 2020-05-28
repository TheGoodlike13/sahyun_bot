from httmock import HTTMock

from sahyun_bot.commands.admin import Index
from tests.mock_customsforge import customsforge


def test_require_admin(commander, hook):
    for command in ['!lock', '!index']:
        with commander.executest('goodlikebot', command, hook):
            hook.assert_silent_failure()


def test_lock_unlock(commander, hook):
    with commander.executest('sahyun', '!lock', hook):
        hook.assert_success('Bot is now in ADMIN only mode')

    # even basic commands are unauthorized
    with commander.executest('goodlikebot', '!time', hook):
        hook.assert_silent_failure()

    with commander.executest('sahyun', '!lock', hook):
        hook.assert_success('Bot no longer in ADMIN only mode')

    # functionality restored
    with commander.executest('goodlikebot', '!time', hook):
        hook.assert_success()


def test_index(tl, hook):
    with HTTMock(customsforge), Index(tl=tl).executest(hook):
        hook.assert_success('CDLCs indexed')

    tl.set_use_elastic(False)

    with HTTMock(customsforge), Index(tl=tl).executest(hook):
        hook.assert_failure('CDLCs could not be indexed')
