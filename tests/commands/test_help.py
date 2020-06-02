from sahyun_bot.users_settings import UserRank


def test_commands(commander, hook):
    with commander.executest(hook, '!commands', 'sahyunbot'):
        hook.assert_silent_failure()

    with commander.executest(hook, '!commands', 'goodlikebot'):
        hook.assert_success(
            'Commands:',
            '!commands,',
            '!last',
            '!playlist',
            '!joke',
            '!time',
            but_not=[
                '!pick',
                '!random',
                '!request',
                '!index',
                '!lock',
                '!rank',
                '!next',
                '!top',
            ],
        )
        
    with commander._users._manual('goodlikebot', UserRank.FLWR), commander.executest(hook, '!commands', 'goodlikebot'):
        hook.assert_success(
            'Commands:',
            '!commands,',
            '!last',
            '!playlist',
            '!joke',
            '!time',
            '!pick',
            '!random',
            '!request',
            but_not=[
                '!index',
                '!lock',
                '!rank',
                '!next',
                '!top',
            ],
        )
    
    with commander.executest(hook, '!commands', 'sahyun'):
        hook.assert_success(
            'Commands:',
            '!commands,',
            '!last',
            '!playlist',
            '!joke',
            '!time',
            '!pick',
            '!random',
            '!request',
            '!index',
            '!lock',
            '!rank',
            '!next',
            '!top',
        )
