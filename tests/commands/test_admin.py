def test_require_admin(commander, hook):
    for command in ['!lock']:
        with commander.executest('goodlikebot', command, hook):
            hook.assert_silent_failure()

        with commander.executest('sahyun', command, hook):
            hook.assert_success()


def test_lock_unlock(commander, hook):
    with commander.executest('sahyun', '!lock', hook):
        hook.assert_success('Bot is now in ADMIN only mode.')

    # even basic commands are unauthorized
    with commander.executest('goodlikebot', '!time', hook):
        hook.assert_silent_failure()

    with commander.executest('sahyun', '!lock', hook):
        hook.assert_success('Bot no longer in ADMIN only mode.')

    # functionality restored
    with commander.executest('goodlikebot', '!time', hook):
        hook.assert_success()
