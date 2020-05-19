import logging
from typing import TypeVar
from urllib.parse import urlparse, parse_qs

# general purpose generic variable to be used in generic functions
T = TypeVar('T')

# if next(it, NON_EXISTENT) is NON_EXISTENT: <do stuff if 'it' was empty>
NON_EXISTENT = object()


def identity(o: T) -> T:
    return o


# noinspection PyUnusedLocal
def always_true(o: T) -> bool:
    return True


# noinspection PyUnusedLocal
def always_false(o: T) -> bool:
    return False


def debug_ex(e: Exception,
             trying_to: str = 'do something (check traceback)',
             *args,
             log: logging.Logger = None,
             silent: bool = False):
    log = log or logging.root
    if silent:
        log.debug('Error while trying to %s: %s: %s', trying_to.format(*args), type(e).__name__, e, exc_info=True)
    else:
        log.error('Error while trying to %s: %s: %s', trying_to.format(*args), type(e).__name__, e)
        log.debug('Traceback:', exc_info=True)


def clean_link(link: str) -> str:
    try:
        url_parts = urlparse(link or '')
        if 'youtube.com' in url_parts.netloc:
            video_id = parse_qs(url_parts.query).get('v', None)
            if video_id:
                return f'https://youtu.be/{video_id[0]}'
        elif url_parts.scheme == 'http':
            return link[:4] + 's' + link[4:]
    except ValueError:
        pass

    return link or ''
