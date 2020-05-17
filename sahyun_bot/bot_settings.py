import logging.config

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_COOKIE_FILE, TEST_COOKIE_FILE
from sahyun_bot.utils import config, read_config, parse_bool

config.read('config.ini')

s_log = read_config('system', 'LoggingConfigFilename', fallback='config_log_default.ini')
logging.config.fileConfig(s_log)  # we initialize logging first to avoid dangling loggers from being created
logging.debug('---------------------------------------------------------')
logging.debug('                      NEW EXECUTION                      ')
logging.debug('---------------------------------------------------------')

s_debug = read_config('system', 'HttpDebugMode', convert=parse_bool, fallback=False)

c_api_key = read_config('customsforge', 'ApiKey')
c_user = read_config('customsforge', 'Username')
c_pass = read_config('customsforge', 'Password')
c_batch = read_config('customsforge', 'BatchSize', convert=int, fallback=DEFAULT_BATCH_SIZE)
c_timeout = read_config('customsforge', 'Timeout', convert=int, fallback=DEFAULT_TIMEOUT)
c_jar = read_config('customsforge', 'CookieFilename', fallback=DEFAULT_COOKIE_FILE, allow_empty=True)
c_jar = DEFAULT_COOKIE_FILE if c_jar == TEST_COOKIE_FILE else c_jar

elastic_settings.init()
