from assertpy import assert_that

from sahyun_bot.commands.request_queue import Request, Next, Pick, Top, Played, Last, Playlist
from sahyun_bot.link_job_properties import LinkJob
from sahyun_bot.users_settings import UserRank


def test_no_match(rq, hook):
    with Request(rq=rq).executest(hook, args='could not possibly be found'):
        hook.assert_failure('No matches for <could not possibly be found>')


def test_multiple_matches(rq, hook):
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success(
            'Your request for <> is now in position 1',
            'To pick exact: ',
            '!1 Hockey Dad - I Wanna Be Everybody (AlQapone)',
            '!2 Yazoo - Only You (JamesPrestonUK)',
            '!3 Yazoo - Bad Connection (smellthemagic)',
        )

    with Request(rq=rq).executest(hook, args='yazoo'):
        hook.assert_success(
            'Your request for <yazoo> is now in position 2',
            'To pick exact: ',
            '!1 Yazoo - Only You (JamesPrestonUK)',
            '!2 Yazoo - Bad Connection (smellthemagic)',
        )


def test_exact_match(rq, hook):
    with Request(rq=rq).executest(hook, args='Hockey'):
        hook.assert_success(
            'Your request for (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone) is now in position 1',
            but_not='To pick exact: ',
        )


def test_next(rq, hook):
    with Next(rq=rq).executest(hook):
        hook.assert_failure('Request queue is empty')

    with Request(rq=rq).executest(hook, nick='sahyun', args='Hockey'):
        pass

    job = MockJob()
    with job, Next(rq=rq, lj=job).executest(hook):
        hook.assert_success('Next: (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone) by ADMIN sahyun')
        hockey_link = 'https://drive.google.com/file/d/1wUb2ukepPD9F0V8JeND0kT1kB6kmPJN-/view?usp=sharing'
        assert_that(job.last_link).is_equal_to(hockey_link)

    assert_that(rq).is_empty()


def test_request_already_played(rq, hook):
    with Request(rq=rq).executest(hook, args=''), Next(rq=rq).executest(hook), \
         Request(rq=rq).executest(hook, args='Hockey'), Next(rq=rq).executest(hook):
        pass

    # followers cannot make requests in memory
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''):
        hook.assert_failure('Already played <>')

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='Hockey'):
        hook.assert_failure('Already played (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone)')

    # still works for admins, though
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success()

    with Request(rq=rq).executest(hook, args='Hockey'):
        hook.assert_success()


def test_request_already_in_queue(rq, hook):
    with Request(rq=rq).executest(hook, args=''), Request(rq=rq).executest(hook, args='Hockey'):
        pass

    # followers cannot make requests for things already in queue
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''):
        hook.assert_failure('Request <> already in queue position 1')

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='Hockey'):
        hook.assert_failure('Request (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone) already in queue position 2')

    # still works for admins, though
    with Request(rq=rq).executest(hook, args=''):
        hook.assert_success()

    with Request(rq=rq).executest(hook, args='Hockey'):
        hook.assert_success()


def test_replace_request(rq, hook):
    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args=''), \
         Request(rq=rq).executest(hook, nick='another', args='Yazoo'):
        pass

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='Hockey'):
        hook.assert_success('Your request for (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone) is now in position 1')


def test_pick_specific(rq, hook):
    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='10'):
        hook.assert_failure('Try !pick 1-3')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='1'):
        hook.assert_silent_failure()

    with Request(rq=rq).executest(hook, rank=UserRank.FLWR, args='Yazoo'):
        pass

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='3'):
        hook.assert_failure('3 is not available; max: 2')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='1'):
        hook.assert_success('Your request for (LRB) Yazoo - Only You (JamesPrestonUK) is now in position 1')

    with Pick(rq=rq).executest(hook, rank=UserRank.FLWR, alias='2'):
        hook.assert_failure(  # to avoid triggering the command limit, this is considered a failure
            'Your request for (OFFICIAL) (LRB) Yazoo - Bad Connection (smellthemagic) is now in position 1',
            'WARNING! This song is official, so it may not be playable. Ask or try again!',
        )


def test_admin_pick_next(rq, hook):
    with Pick(rq=rq).executest(hook, alias='1'):
        hook.assert_failure('Nothing to pick')

    with Request(rq=rq).executest(hook, args='Yazoo'):
        pass

    job = MockJob()
    with job, Next(rq=rq, lj=job).executest(hook):
        hook.assert_success(
            'Pick for <Yazoo> by ADMIN _test: ',
            '!1 Yazoo - Only You (JamesPrestonUK)',
            '!2 Yazoo - Bad Connection (smellthemagic)',
            but_not='Next: '
        )
        assert_that(job.last_link).is_none()

    with job, Pick(rq=rq, lj=job).executest(hook, alias='3'):
        hook.assert_failure('3 is not available; max: 2')
        assert_that(job.last_link).is_none()

    with job, Pick(rq=rq, lj=job).executest(hook, alias='1'):
        hook.assert_success('Next: (LRB) Yazoo - Only You (JamesPrestonUK)')
        only_you_link = 'https://www.dropbox.com/sh/i3uj2fwxle0dag6/AAAgK-D506DtEXoH1NiJoKVBa?dl=0'
        assert_that(job.last_link).is_equal_to(only_you_link)

    with job, Pick(rq=rq, lj=job).executest(hook, alias='2'):
        hook.assert_success("Next: (OFFICIAL) (LRB) Yazoo - Bad Connection (smellthemagic)")
        bad_connection_link = 'https://www.mediafire.com/file/3sb8lzs0khdutft/SM_Moon-Crystal-Power_v1_p.psarc/file'
        assert_that(job.last_link).is_equal_to(bad_connection_link)


def test_not_playable(rq, hook):
    with Request(rq=rq).executest(hook, args='Miles Away'):
        hook.assert_failure(
            'Matches for <Miles Away> not playable: ',
            'Josh Ritter - Miles Away (Djpavs)',
        )

    with Request(rq=rq).executest(hook, args='Red Paper Lanterns'):
        hook.assert_failure(
            'Matches for <Red Paper Lanterns> not playable: ',
            'Maybeshewill - Red Paper Lanterns (temoux)',
        )


def test_bump(rq, hook):
    with Request(rq=rq).executest(hook, args='Hockey'), Request(rq=rq).executest(hook, args='Yazoo'), \
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
         Request(rq=rq).executest(hook, args='Hockey'), Next(rq=rq).executest(hook):
        pass

    with Played(rq=rq).executest(hook):
        hook.assert_success('Requests played: <>, Hockey Dad - I Wanna Be Everybody (AlQapone)')


def test_last(rq, hook):
    with Last(rq=rq).executest(hook):
        hook.assert_failure('No requests have been played yet')

    with Request(rq=rq).executest(hook, args='Hockey'), Next(rq=rq).executest(hook):
        pass

    with Last(rq=rq).executest(hook):
        hook.assert_success('Last: (LBV) Hockey Dad - I Wanna Be Everybody (AlQapone) by ADMIN _test')


def test_playlist(rq, hook):
    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (0/0): empty')

    with Request(rq=rq).executest(hook, args=''):
        pass

    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (1/1): <>')

    with Request(rq=rq).executest(hook, args='Hockey'):
        pass

    with Playlist(rq=rq).executest(hook):
        hook.assert_success('Playlist (2/2): <>, Hockey Dad - I Wanna Be Everybody (AlQapone)')

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


class MockJob(LinkJob):
    def __init__(self):
        self.last_link = None

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self.last_link = None

    def handle(self, link: str):
        self.last_link = link
