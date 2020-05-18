import atexit
from typing import Any

from elasticsearch_dsl import connections

from sahyun_bot.bot_settings import *
from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic_settings import *
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


def init_module(module: Any, desc: str):
    LOG.warning('%s is %savailable.', desc, '' if module else 'un')
    if module and hasattr(module, 'close') and callable(module.close):
        atexit.register(module.close)
    return module


LOG.warning('Please check config.ini file if any module is unavailable.')

cf = CustomsForgeClient(api_key=c_api_key,
                        batch_size=c_batch,
                        timeout=c_timeout,
                        cookie_jar_file=c_jar,
                        username=c_user,
                        password=c_pass) if c_api_key else None
init_module(cf, 'Customsforge client')

es = connections.create_connection(hosts=[e_host]) if e_host else None
if init_module(es, 'Elasticsearch client'):
    LOG.warning('Using CDLC index: [%s]', e_cf_index)
