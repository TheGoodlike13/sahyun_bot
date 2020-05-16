import atexit
import http.client
import logging.config
import sys
from typing import Any

from elasticsearch_dsl import connections

from sahyun_bot.customsforge import CustomsForgeClient, DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_COOKIE_FILE, \
    TEST_COOKIE_FILE
from sahyun_bot.utils import config, read_config, parse_bool

# in this section, we read all parameters expected in the config.ini file
config.read('config.ini')

s_log = read_config('system', 'LoggingConfig', fallback='config_log_default.ini')
logging.config.fileConfig(s_log)  # we initialize logging first to avoid dangling loggers from being created
logging.debug('---------------------------------------------------------')
logging.debug('                      NEW EXECUTION                      ')
logging.debug('---------------------------------------------------------')

s_debug = read_config('system', 'HttpDebugMode', parse_bool)

c_api_key = read_config('customsforge', 'ApiKey')
c_user = read_config('customsforge', 'Username')
c_pass = read_config('customsforge', 'Password')
c_batch = read_config('customsforge', 'BatchSize', fallback=DEFAULT_BATCH_SIZE, convert=int)
c_timeout = read_config('customsforge', 'Timeout', fallback=DEFAULT_TIMEOUT, convert=int)
c_jar = read_config('customsforge', 'CookieFilename', fallback=DEFAULT_COOKIE_FILE, allow_empty=True)
c_jar = DEFAULT_COOKIE_FILE if c_jar == TEST_COOKIE_FILE else c_jar

e_host = read_config('elastic', 'Host', fallback='localhost')


# in this section we initialize all objects the bot will make use of, but avoid launching anything (e.g. connect to IRC)
def init_module(module: Any, desc: str):
    logging.info('%s is available', desc) if module else logging.warning('%s could not be configured', desc)
    if module and hasattr(module, 'close') and callable(module.close):
        atexit.register(module.close)


logging.info('Please check config.ini file if any module is unavailable')

http.client.HTTPConnection.debuglevel = 1 if s_debug else 0

cf = CustomsForgeClient(api_key=c_api_key,
                        batch_size=c_batch,
                        timeout=c_timeout,
                        cookie_jar_file=c_jar,
                        username=c_user,
                        password=c_pass) if c_api_key else None
init_module(cf, 'Customsforge client')

es = connections.create_connection(hosts=[e_host]) if e_host else None
init_module(es, 'Elasticsearch client')


# in this section we launch all relevant modules into action, enabling bot functionality in full
def run_main():
    from sahyun_bot.elastic import setup_elastic

    logging.info('Bot launched')
    setup_elastic()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        run_main()
    else:
        # here we import all kinds of utilities so repl can be used more conveniently

        from sahyun_bot.customsforge import *
        from sahyun_bot.elastic import *
        from sahyun_bot.utils import *
        # noinspection PyUnresolvedReferences
        from time import time
        # noinspection PyUnresolvedReferences
        from datetime import date, datetime
        # noinspection PyUnresolvedReferences
        from urllib.parse import *
        # noinspection PyUnresolvedReferences
        import html
        # noinspection PyUnresolvedReferences
        import os
