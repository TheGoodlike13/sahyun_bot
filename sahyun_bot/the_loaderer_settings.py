from sahyun_bot.utils_settings import read_config

DEFAULT_MAX_THREADS = 8

l_max = read_config('load', 'MaxWorkers', convert=int, fallback=DEFAULT_MAX_THREADS)
