from assertpy import assert_that

from sahyun_bot.commands.request_queue import Request, Next, Pick, Top, Played, Last, Playlist
from sahyun_bot.users_settings import UserRank


def test_no_match(rq, hook):
    with Request(rq=rq).executest(hook, args='could not possibly be found'):
        hook.assert_failure('No matches for <could not possibly be found>')


def test_multiple_matches(rq, hook):
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success(
            'Your request for <> is now in position 1',
            'To pick exact: ',
            '!1 Skillet - Those Nights (Rankourai)',
            '!2 Linkin Park - All For Nothing (AntonZap)',
            "!3 Trey Parker - Jackin' It In San Diego (dtn828)",
        )

    with Request(rq=rq).executest(hook, args='parke'):
        hook.assert_success(
            'Your request for <parke> is now in position 2',
            'To pick exact: ',
            '!1 Linkin Park - All For Nothing (AntonZap)',
            "!2 Trey Parker - Jackin' It In San Diego (dtn828)",
        )


def test_exact_match(rq, hook):
    with Request(rq=rq).executest(hook, args='ZUN'):
        hook.assert_success(
            'Your request for (L) ZUN - Paradise ~ Deep Mountain (coldrampage) is now in position 1',
            but_not='To pick exact: ',
        )


def test_next(rq, hook):
    with Next(rq=rq).executest(hook):
        hook.assert_failure('Request queue is empty')

    with Request(rq=rq).executest(hook, nick='sahyun', args='ZUN'):
        pass

    with Next(rq=rq).executest(hook):
        hook.assert_success('Next: (L) ZUN - Paradise ~ Deep Mountain (coldrampage) by ADMIN sahyun')

    assert_that(rq).is_empty()


def test_request_already_played(rq, hook):
    with Request(rq=rq).executest(hook, args=''), Next(rq=rq).executest(hook), \
         Request(rq=rq).executest(hook, args='ZUN'), Next(rq=rq).executest(hook):
        pass

    # followers cannot make requests in memory
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''):
        hook.assert_failure('Already played <>')

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='ZUN'):
        hook.assert_failure('Already played (L) ZUN - Paradise ~ Deep Mountain (coldrampage)')

    # still works for admins, though
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success()

    with Request(rq=rq).executest(hook, args='ZUN'):
        hook.assert_success()


def test_request_already_in_queue(rq, hook):
    with Request(rq=rq).executest(hook, args=''), Request(rq=rq).executest(hook, args='ZUN'):
        pass

    # followers cannot make requests for things already in queue
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''):
        hook.assert_failure('Request <> already in queue position 1')

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='ZUN'):
        hook.assert_failure('Request (L) ZUN - Paradise ~ Deep Mountain (coldrampage) already in queue position 2')

    # still works for admins, though
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success()

    with Request(rq=rq).executest(hook, args='ZUN'):
        hook.assert_success()


def test_replace_request(rq, hook):
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''), \
         Request(rq=rq).executest(hook, nick='another', args='parke'):
        pass

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='ZUN'):
        hook.assert_success('Your request for (L) ZUN - Paradise ~ Deep Mountain (coldrampage) is now in position 1')


def test_pick_specific(rq, hook):
    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='10'):
        hook.assert_failure('Try !pick 1-3')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='1'):
        hook.assert_silent_failure()

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='parke'):
        pass

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='3'):
        hook.assert_failure('3 is not available; max: 2')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='1'):
        hook.assert_success('Your request for (LRBV) Linkin Park - All For Nothing (AntonZap) is now in position 1')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='2'):
        hook.assert_success("(RBV) Trey Parker - Jackin' It In San Diego (dtn828) is now in position 1")


def test_admin_pick_next(rq, hook):
    with Pick(rq=rq).executest(hook, alias='1'):
        hook.assert_failure('Nothing to pick')

    with Request(rq=rq).executest(hook, args='parke'):
        pass

    with Next(rq=rq).executest(hook):
        hook.assert_success(
            'Pick for <parke> by ADMIN _test: ',
            '!1 Linkin Park - All For Nothing (AntonZap)',
            "!2 Trey Parker - Jackin' It In San Diego (dtn828)",
            but_not='Next: '
        )

    with Pick(rq=rq).executest(hook, alias='3'):
        hook.assert_failure('3 is not available; max: 2')

    with Pick(rq=rq).executest(hook, alias='1'):
        hook.assert_success('Next: (LRBV) Linkin Park - All For Nothing (AntonZap)')

    with Pick(rq=rq).executest(hook, alias='2'):
        hook.assert_success("Next: (RBV) Trey Parker - Jackin' It In San Diego (dtn828)")


def test_not_playable(rq, hook):
    with Request(rq=rq).executest(hook, args='The Who'):
        hook.assert_failure(
            'Matches for <The Who> not playable: ',
            'The Who - A Legal Matter (Haydo0467)',
        )

    with Request(rq=rq).executest(hook, args='Hitman'):
        hook.assert_failure(
            'Matches for <Hitman> not playable: ',
            'Metal Church - Hitman (vuducult)',
        )


def test_official(rq, hook):
    with Request(rq=rq).executest(hook, args='Skillet'):
        hook.assert_failure(
            'Your request for (OFFICIAL) (LBV) Skillet - Those Nights (Rankourai) is now in position 1',
            'WARNING! This song is official, so it may not be playable. Ask or try again!',
        )


def test_bump(rq, hook):
    with Request(rq=rq).executest(hook, args='ZUN'), Request(rq=rq).executest(hook, args='parke'), \
         Request(rq=rq).executest(hook, nick='another', rank=UserRank.FLWR, args=''):
        pass

    with Top(rq=rq).executest(hook, args='who'):
        hook.assert_failure('No requests by <who> in queue')

    with Top(rq=rq).executest(hook, args='another'):
        hook.assert_success('Request <> by FLWR another is now in position 1')


def test_played(rq, hook):
    with Played(rq=rq).executest(hook):
        hook.assert_success('Requests played: none')

    with Request(rq=rq).executest(hook, args=''), Next(rq=rq).executest(hook), \
         Request(rq=rq).executest(hook, args='ZUN'), Next(rq=rq).executest(hook):
        pass

    with Played(rq=rq).executest(hook):
        hook.assert_success('Requests played: <>, ZUN - Paradise ~ Deep Mountain (coldrampage)')


def test_last(rq, hook):
    with Last(rq=rq).executest(hook):
        hook.assert_failure('No requests have been played yet')

    with Request(rq=rq).executest(hook, args='ZUN'), Next(rq=rq).executest(hook):
        pass

    with Last(rq=rq).executest(hook):
        hook.assert_success('Last: (L) ZUN - Paradise ~ Deep Mountain (coldrampage) by ADMIN _test')


def test_playlist(rq, hook):
    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (0/0): empty')

    with Request(rq=rq).executest(hook, args=''):
        pass

    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (1/1): <>')

    with Request(rq=rq).executest(hook, args='ZUN'):
        pass

    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (2/2): <>, ZUN - Paradise ~ Deep Mountain (coldrampage)')

    with Playlist(rq=rq, max_print=1).executest(hook):
        hook.assert_success('Playlist (1/2): <>')


def test_ranks(commander, hook):
    with commander.executest(hook, '!request', 'goodlikebot'):
        hook.assert_failure('Please follow the channel to use !request')

    with commander.executest(hook, '!next', 'goodlikebot'):
        hook.assert_silent_failure()

    with commander.executest(hook, '!top', 'goodlikebot'):
        hook.assert_silent_failure()

    with commander.executest(hook, '!last', 'sahyunbot'):
        hook.assert_silent_failure()
