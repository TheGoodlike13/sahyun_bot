import logging
import os
from itertools import chain

LOG = logging.getLogger(__name__.rpartition('.')[2].replace('_', ''))


def nuke_from_orbit(reason: str):
    LOG.critical('Forcing shutdown of the application. Reason: {}'.format(reason))
    # noinspection PyProtectedMember
    os._exit(1)


UTILITY_MODULES_TO_LOAD = [
    'itertools.py',
    'urllib.parse.py'
]


def should_be_loaded(m):
    is_self = m == __name__.rpartition('.')[2]
    is_python = m[-3:] == '.py'
    is_private = m[:1] == '_'
    is_essential = m[:3] == 'bot' or m[-12:] == '_settings.py'
    return not is_self and is_python and not is_private and not is_essential


if __name__ == '__main__':
    """
    This main function is intended to be run as interactive shell.
    It loads all modules into locals() so you can access them immediately, as well as some other utilities.
    For a saner main() method, use bot.py
    """

    # first we manually load some essentials
    from sahyun_bot.bot_modules import *

    # then we dynamically load the rest
    for module in chain(os.listdir(os.path.dirname(__file__)), UTILITY_MODULES_TO_LOAD):
        if should_be_loaded(module):
            m = __import__(module[:-3], globals(), locals(), ['*'], 0)
            for item in dir(m):
                if item[:1] != '_' and item not in locals():
                    locals()[item] = getattr(m, item)
