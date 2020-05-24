"""
Creates instances of all singletons in the application. Can be considered the equivalent of a bean factory.
Globally accessible only for the purposes of easy REPL usage.
It should be imported by any module with __main__ method, which can then initiate the process of the application.
"""
import atexit

from elasticsearch_dsl import connections

from sahyun_bot.bot_settings import *
from sahyun_bot.commander import TheCommander
from sahyun_bot.elastic_settings import *
from sahyun_bot.irc_bot import botyun
from sahyun_bot.the_loaderer import *
from sahyun_bot.the_loaderer_settings import *
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


def init_module(module: Any, desc: str):
    LOG.warning('%s is %savailable.', desc, '' if module else 'un')
    if module and hasattr(module, 'close') and callable(module.close):
        atexit.register(module.close)
    return module


LOG.warning('Please check config.ini file if any module is unavailable.')

cf = CustomsforgeClient(api_key=c_api_key,
                        batch_size=c_batch,
                        timeout=c_timeout,
                        cookie_jar_file=c_jar,
                        username=c_user,
                        password=c_pass) if c_api_key else None
init_module(cf, 'Customsforge client')

es = connections.create_connection(hosts=[e_host]) if e_host else None
if init_module(es, 'Elasticsearch client'):
    LOG.warning('Using CDLC index: <%s>.', e_cf_index)

tl = TheLoaderer(cf=cf, max_threads=l_max)
init_module(tl, 'The loaderer')

tc = TheCommander(cf=cf, es=es, tl=tl)
init_module(tc, 'The commander')

bot = botyun(tc=tc,
             nickname=i_nick,
             token=i_token,
             channels=i_channels,
             max_threads=i_max) if i_nick and i_token else None
init_module(bot, 'IRC bot')
