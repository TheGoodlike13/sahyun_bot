from assertpy import assert_that

from sahyun_bot.utils import identity


def test_identity():
    for o in [None, '', 13, 3.14, True]:
        assert_that(identity(o)).is_same_as(o)
