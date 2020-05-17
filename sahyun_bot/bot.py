import logging.config
import sys

from sahyun_bot.bot_modules import *


def run_main():
    from sahyun_bot.elastic import setup_elastic

    logging.info('Bot launched')
    setup_elastic()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        run_main()
    else:
        # here we import all kinds of utilities so repl can be used more conveniently
        # noinspection PyUnresolvedReferences
        from urllib.parse import *
        # noinspection PyUnresolvedReferences
        from sahyun_bot.elastic_settings import *
        # noinspection PyUnresolvedReferences
        from sahyun_bot.customsforge import *
        # noinspection PyUnresolvedReferences
        from sahyun_bot.elastic import *
        # noinspection PyUnresolvedReferences
        from sahyun_bot.the_loaderer import *
