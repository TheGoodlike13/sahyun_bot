"""
Creates instances of all singletons in the application. Can be considered the equivalent of a bean factory.
Globally accessible only for the purposes of easy REPL usage.
It should be imported by any module with __main__ method, which can then initiate the process of the application.
"""
import atexit

from elasticsearch_dsl import connections

from sahyun_bot.bot_settings import *
from sahyun_bot.commander import TheCommander
from sahyun_bot.commander_settings import *
from sahyun_bot.down import Downtime
from sahyun_bot.down_settings import *
from sahyun_bot.elastic_settings import *
from sahyun_bot.irc_bot import botyun
from sahyun_bot.link_job import BrowseLink, CopyLinkToPaste, LinkJobFactory, IgnoreLink
from sahyun_bot.link_job_properties import *
from sahyun_bot.the_loaderer import *
from sahyun_bot.twitchy import Twitchy
from sahyun_bot.twitchy_settings import *
from sahyun_bot.users import Users
from sahyun_bot.users_settings import *
from sahyun_bot.utils import choose
from sahyun_bot.utils_elastic import print_elastic_indexes
from sahyun_bot.utils_logging import get_logger
from sahyun_bot.utils_queue import MemoryQueue

LOG = get_logger(__name__)


def init_module(module: Any, desc: str):
    LOG.warning('%s is %savailable.', desc, 'un' if module is None else '')
    if module and hasattr(module, 'close') and callable(module.close):
        atexit.register(module.close)
    return module


LOG.warning('Please check config.ini file if any module is unavailable.')

cf = CustomsforgeClient(batch_size=c_batch,
                        timeout=c_timeout,
                        cookie_jar_file=c_jar,
                        email=c_email,
                        password=c_pass)
init_module(cf, 'Customsforge client')
init_module(c_jar, 'Cookie jar for customsforge')

tw = Twitchy(client_id=t_id, client_secret=t_secret) if t_id and t_secret else None
init_module(tw, 'Twitch API')

es = connections.create_connection(hosts=[e_host]) if e_host else None
if init_module(es, 'Elasticsearch client'):
    print_elastic_indexes()

dt = Downtime(config=d_down) if d_down else None
init_module(dt, 'Downtime for commands')

# following modules are always available (may still have limited functionality)
us = Users(streamer=i_streamer, tw=tw, cache_follows=u_cache_f, cache_viewers=u_cache_w)
init_module(us, 'User factory')

tl = TheLoaderer(cf=cf, max_threads=l_max)
init_module(tl, 'The loaderer')

lb = BrowseLink()
lc = CopyLinkToPaste()
li = IgnoreLink()

lj_config = {
    'fallback': choose(lj_default, browse=lb, copy=lc, ignore=li)
}
lj = LinkJobFactory(**lj_config)
init_module(lj, 'Link jobs')

rq = MemoryQueue()
init_module(rq, 'Request queue')

tc_config = {
    'max_search': cm_search,
    'max_pick': cm_pick,
    'max_print': cm_print,
}
tc = TheCommander(cf=cf, tw=tw, es=es, dt=dt, us=us, tl=tl, lj=lj, rq=rq, **tc_config)
init_module(tc, 'The commander')

bot = botyun(tc=tc,
             nickname=i_nick,
             token=i_token,
             channels=[i_streamer] if i_streamer else [],
             max_threads=i_max) if i_nick and i_token else None
init_module(bot, 'IRC bot')
