import logging.config

from sahyun_bot.bot_modules import *
from sahyun_bot.elastic_settings import *


def run_main():
    from sahyun_bot.elastic import setup_elastic

    logging.info('Bot launched')
    setup_elastic()


if __name__ == '__main__':
    logging.warning('Elastic index: %s', e_cf_index)
    run_main()
