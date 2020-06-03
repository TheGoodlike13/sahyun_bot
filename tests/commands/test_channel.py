from httmock import HTTMock

from tests.mock_twitch_extras import twitch_hosts


def test_hosts(commander, hook):
    with HTTMock(twitch_hosts), commander.executest(hook, '!hosts'):
        hook.assert_success('Hosts: thegoodlike13')
