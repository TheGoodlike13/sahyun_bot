import atexit
import logging
from typing import Any

from elasticsearch_dsl import connections

from sahyun_bot.bot_settings import *
from sahyun_bot.customsforge import CustomsForgeClient


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

es = connections.create_connection(hosts=[elastic_settings.e_host]) if elastic_settings.e_host else None
init_module(es, 'Elasticsearch client')
