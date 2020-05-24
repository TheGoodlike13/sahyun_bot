import pytest
from assertpy import assert_that

from sahyun_bot.commander import TheCommander


@pytest.fixture
def comm_basic():
    return TheCommander()


def test_not_command(comm_basic):
    assert_that(comm_basic.executest('test', '')).is_empty()
    assert_that(comm_basic.executest('test', 'Time for some random IRC chatter!')).is_empty()  # !time is a command


def test_commands_resolved_automatically(comm_basic):
    assert_that(comm_basic.executest('test', '!time')).contains('test: The time is now ', ' UTC.')
    assert_that(comm_basic.executest('test', '!TIME')).contains('test: The time is now ', ' UTC.')
