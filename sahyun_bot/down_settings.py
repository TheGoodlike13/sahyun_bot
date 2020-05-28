from sahyun_bot.utils_settings import read_dynamic_config

d_down = read_dynamic_config('downtime',
                             convert_key=lambda key: key.lower(),
                             fallback='')
