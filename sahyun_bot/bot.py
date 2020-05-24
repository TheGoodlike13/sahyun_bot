"""
Main module of the application. Launches the bot, begins listening to commands and executing them.
"""
from sahyun_bot.modules import *
from sahyun_bot.utils_bot import setup_console
from sahyun_bot.utils_elastic import setup_elastic
from sahyun_bot.utils_logging import get_logger

LOG = get_logger('bot')  # __name__ becomes main


def run_main():
    LOG.warning('Launching bot...')
    setup_elastic()
    bot.launch_in_own_thread()
    setup_console(tc)


if __name__ == '__main__':
    run_main()
