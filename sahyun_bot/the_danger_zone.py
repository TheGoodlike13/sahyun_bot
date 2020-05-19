import os
from itertools import chain

from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


def nuke_from_orbit(reason: str):
    LOG.critical(f'Forcing shutdown of the application. Reason: {reason}')
    os._exit(1)


if __name__ == '__main__':
    """
    Main function for an interactive shell. Loads a bunch of utils into locals() so they can be used immediately.
    Use bot.py for a sane main function.
    """
    from sahyun_bot.modules import *

    local_utils = [m[:-3] for m in os.listdir(os.path.dirname(__file__)) if m[:5] == 'utils']
    other_utils = ['datetime', 'itertools', 'urllib.parse', 'dictdiffer']

    for u in chain(local_utils, other_utils):
        m = __import__(u, globals(), locals(), ['*'], 0)
        for item in dir(m):
            if item[:1] != '_' and item not in locals():
                locals()[item] = getattr(m, item)
