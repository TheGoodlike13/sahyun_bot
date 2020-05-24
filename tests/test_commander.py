import pytest
from assertpy import assert_that

from sahyun_bot.commander import TheCommander


@pytest.fixture
def comm_basic():
    return TheCommander()


def test_not_command(comm_basic, hook):
    with comm_basic.execute('_test', '', hook):
        assert_that(hook.all()).is_empty()

    with comm_basic.execute('_test', 'Time for some random IRC chatter!', hook):  # !time is a command
        assert_that(hook.all()).is_empty()


def test_commands_resolved_automatically(comm_basic, hook):
    with comm_basic.execute('_test', '!time', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')

    with comm_basic.execute('_test', '!TIME', hook):
        assert_that(hook.all_to_sender()).contains('The time is now ', ' UTC')
