from assertpy import assert_that

from sahyun_bot.elastic import CustomDLC, last_auto_index_time, request


def test_properties(init_elastic):
    cdlc = CustomDLC.get('3492')
    assert_that(cdlc.full_title).is_equal_to('Porno Graffiti - Hitori No Yoru(Great Teacher Onizuka)')
    assert_that(cdlc.link).is_equal_to('https://customsforge.com/process.php?id=3492')

    cdlc.update(direct_link='direct_link')

    same_cdlc = list(CustomDLC.search().query('match', id='3492'))
    assert_that(same_cdlc).is_length(1)
    assert_that(same_cdlc[0].link).is_equal_to('direct_link')


def test_last_auto_index_time(init_elastic):
    assert_that(last_auto_index_time()).is_none()

    CustomDLC.get('8623').update(from_auto_index=True)

    assert_that(last_auto_index_time()).is_equal_to(1318910400)


def test_request(init_elastic):
    assert_that(request('definitely not here')).is_empty()

    cdlcs = request("you're")
    assert_that(cdlcs).is_length(1)
    assert_that(cdlcs[0].full_title).is_equal_to('Yellowcard - Hang You Up')
