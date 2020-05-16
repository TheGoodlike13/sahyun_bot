import pytest
from assertpy import assert_that

from sahyun_bot.utils import config, identity, parse_bool, read_config


@pytest.fixture
def objects():
    return [None, '', 13, 3.14, True]


@pytest.fixture
def true():
    return ['1', 'yes', 'true', 'on', 'True']


@pytest.fixture
def false():
    return ['0', 'no', 'false', 'off', 'False']


def test_identity(objects):
    for o in objects:
        assert_that(identity(o)).is_same_as(o)


def test_parse_bool(true, false):
    assert_that(parse_bool).raises(ValueError).when_called_with('')
    assert_that(parse_bool('', fallback=True)).is_true()

    for t in true:
        assert_that(parse_bool(t)).is_true()

    for f in false:
        assert_that(parse_bool(f)).is_false()


def test_read_config():
    config.add_section('section')
    config.set('section', 'string', ' value ')
    config.set('section', 'int', ' 1 ')
    config.set('section', 'float', ' 2.71 ')
    config.set('section', 'bool', ' yes ')
    config.set('section', 'empty', '')
    config.set('section', 'blank', '')

    assert_that(read_config('section', 'string')).is_equal_to('value')
    assert_that(read_config('section', 'int', convert=int)).is_equal_to(1)
    assert_that(read_config('section', 'float', convert=float)).is_equal_to(2.71)
    assert_that(read_config('section', 'bool', convert=parse_bool)).is_true()

    assert_that(read_config('section', 'missing')).is_none()
    assert_that(read_config('section', 'missing', fallback='not_anymore')).is_equal_to('not_anymore')
    assert_that(read_config('section', 'string', convert=int, fallback=10)).is_equal_to(10)

    assert_that(read_config('section', 'empty')).is_none()
    assert_that(read_config('section', 'empty', fallback='used')).is_equal_to('used')
    assert_that(read_config('section', 'blank', fallback='used')).is_equal_to('used')
    assert_that(read_config('section', 'empty', fallback='ignored', allow_empty=True)).is_equal_to('')
    assert_that(read_config('section', 'blank', fallback='still_ignored', allow_empty=True)).is_equal_to('')
