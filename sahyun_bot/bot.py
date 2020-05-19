"""
Main module of the application. Launches the bot, begins listening to commands and executing them.
"""

from sahyun_bot.modules import *
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


def run_main():
    LOG.warning('Bot launched successfully.')


if __name__ == '__main__':
    run_main()
