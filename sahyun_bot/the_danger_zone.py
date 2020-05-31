from itertools import chain

from sahyun_bot.utils_logging import get_logger

LOG = get_logger('thedangerzone')  # __name__ becomes main


def nuke_from_orbit(reason: str):
    """
    Forcibly and immediately shuts down the application. To be used when data integrity is at risk.
    """
    LOG.critical(f'Forcing shutdown of the application. Reason: {reason}')
    import os
    os._exit(1)


if __name__ == '__main__':
    """
    Main function for an interactive shell. Loads a bunch of utils into locals() so they can be used immediately.
    Use bot.py for a sane main function.
    """
    from sahyun_bot.modules import *
    from sahyun_bot.elastic import *
    from sahyun_bot.utils_elastic import setup_elastic_usage

    setup_elastic_usage(us, tl, use_elastic=True)

    local_utils = [m[:-3] for m in os.listdir(os.path.dirname(__file__)) if m[:5] == 'utils']
    other_utils = ['datetime', 'itertools', 'urllib.parse', 'dictdiffer', 'humanize']

    for u in chain(local_utils, other_utils):
        m = __import__(u, globals(), locals(), ['*'], 0)
        for item in dir(m):
            if item[:1] != '_' and item not in locals():
                locals()[item] = getattr(m, item)
