import logging
import os


def nuke_from_orbit(reason: str):
    logging.critical('Forcing shutdown of the application. Reason: {}'.format(reason))
    # noinspection PyProtectedMember
    os._exit(1)
