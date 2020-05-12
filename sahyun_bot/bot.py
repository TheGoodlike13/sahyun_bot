import atexit
import http.client
import sys
from configparser import ConfigParser

from sahyun_bot.customsforge import CustomsForgeClient

# in this section, we read all parameters expected in the config file
config = ConfigParser()
config.read('config.ini')

c_api_key = config.get('customsforge', 'ApiKey', fallback=None)
c_user = config.get('customsforge', 'Username', fallback=None)
c_pass = config.get('customsforge', 'Password', fallback=None)
c_batch = config.getint('customsforge', 'BatchSize', fallback=100)

s_debug = config.getboolean('system', 'HttpDebugMode', fallback=False)


# in this section we initialize all objects the bot will make use of, but avoid launching anything (e.g. connect to IRC)
def init_module(module, desc, cleanup=False):
    print('{} is available.'.format(desc)) if module else print('{} could not be configured.'.format(module))
    if module and cleanup:
        atexit.register(module.close)


print('If any module is unavailable, please check your config.ini file')
client = CustomsForgeClient(c_api_key, c_batch, c_user, c_pass) if c_api_key else None
init_module(client, 'Customsforge client', cleanup=True)

http.client.HTTPConnection.debuglevel = 1 if s_debug else 0


# in this section we launch all relevant modules into action, enabling bot functionality in full
if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Main will only execute when there are no parameters.')
