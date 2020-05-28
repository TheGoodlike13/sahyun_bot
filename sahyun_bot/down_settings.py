from sahyun_bot.utils_settings import read_dynamic_config, read_config

DEFAULT_LENIENCY = 1

d_leniency = read_config('downtime', 'Leniency', convert=int, fallback=DEFAULT_LENIENCY)
d_down = read_dynamic_config('downtime',
                             ignore=['Leniency'],
                             convert_key=lambda key: key.lower(),
                             fallback='')
