from assertpy import assert_that

from sahyun_bot.utils import identity, always_true, clean_link, skip_while


def test_identity():
    for o in [None, '', 13, 3.14, True]:
        assert_that(identity(o)).is_same_as(o)


def test_clean_link():
    # noinspection PyTypeChecker
    assert_that(clean_link(None)).is_empty()
    assert_that(clean_link('')).is_empty()
    assert_that(clean_link('http://localhost')).is_equal_to('https://localhost')
    assert_that(clean_link('http://www.youtube.com/watch?v=ID&playlist=')).is_equal_to('https://youtu.be/ID')


def test_skip_while():
    # noinspection PyTypeChecker
    assert_that(list(skip_while(None))).is_empty()
    assert_that(list(skip_while([]))).is_empty()
    assert_that(list(skip_while(['a']))).contains('a').is_length(1)
    assert_that(list(skip_while(['a'], always_true))).is_empty()
    assert_that(list(skip_while(['a', 'b'], always_true))).is_empty()
    assert_that(list(skip_while(['a', 'b'], lambda x: x == 'a'))).contains('b').is_length(1)
    assert_that(list(skip_while(['a', 'b'], lambda x: x == 'b'))).contains('a', 'b').is_length(2)
