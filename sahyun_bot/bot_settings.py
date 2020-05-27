"""
Initializes configuration for the bot. Should only be imported by modules.py.
"""
import http.client
import logging.config

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge_settings import *
from sahyun_bot.irc_bot_settings import *
from sahyun_bot.utils_settings import config, read_config, parse_bool

config.read('config.ini')

s_log = read_config('system', 'LoggingConfigFilename', fallback='config_log_default.ini')
logging.config.fileConfig(s_log)  # we initialize logging first to avoid dangling loggers from being created
logging.info('---------------------------------------------------------')
logging.info('                      NEW EXECUTION                      ')
logging.info('---------------------------------------------------------')

s_debug = read_config('system', 'HttpDebugMode', convert=parse_bool, fallback=False)
http.client.HTTPConnection.debuglevel = 1 if s_debug else 0

c_api_key = read_config('customsforge', 'ApiKey')
c_user = read_config('customsforge', 'Username')
c_pass = read_config('customsforge', 'Password')
c_batch = read_config('customsforge', 'BatchSize', convert=int, fallback=DEFAULT_BATCH_SIZE)
c_timeout = read_config('customsforge', 'Timeout', convert=int, fallback=DEFAULT_TIMEOUT)
c_jar = read_config('customsforge', 'CookieFilename', fallback=DEFAULT_COOKIE_FILE, allow_empty=True)
c_jar = DEFAULT_COOKIE_FILE if c_jar == TEST_COOKIE_FILE else c_jar

i_nick = read_config('irc', 'Nick')
i_token = read_config('irc', 'Token')
# noinspection PyTypeChecker
i_streamer = read_config('irc', 'Channel', fallback='')
i_max = read_config('irc', 'MaxWorkers', convert=int, fallback=MAX_CONCURRENT_COMMANDS)

elastic_settings.init()
