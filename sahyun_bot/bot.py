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
    setup_elastic(us, tl)
    bot.launch_in_own_thread()
    setup_console(tc)
    print_error_warning()


def print_error_warning():
    LOG.warning('---------------------------------------------------------')
    LOG.warning('Event loop error may follow, but you can ignore it.')
    LOG.warning('WindowsSelectorEventLoopPolicy is missing sometimes.')
    LOG.warning('No, it is not the Python version, it was added with 3.7.')
    LOG.warning('Apparently, it would fix the problem.')
    LOG.warning('At least that is what somebody on the internet said.')
    LOG.warning('Well, they also said to ignore all errors on close.')
    LOG.warning('I have not found a way to do that.')
    LOG.warning('Must have been a lie.')
    LOG.warning('Well, know that it was worse. Like, way worse.')
    LOG.warning('We are talking multiple pages of errors worse.')
    LOG.warning('I have done my best.')
    LOG.warning('---------------------------------------------------------')


if __name__ == '__main__':
    run_main()
