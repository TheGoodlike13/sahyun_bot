import http.client
import sys
from configparser import ConfigParser

from sahyun_bot.customsforge import CustomsForgeClient

# in this section, we read all parameters expected in the config file
config = ConfigParser()
config.read('config.ini')

customsforgeApiKey = config.get('customsforge', 'ApiKey', fallback=None)
customsforgeBatchSize = config.getint('customsforge', 'BatchSize', fallback=100)

systemEnableHttpDebug = config.getboolean('system', 'HttpDebugMode', fallback=False)


# in this section we initialize all objects the bot will make use of, but avoid launching anything (e.g. connect to IRC)
client = CustomsForgeClient(customsforgeApiKey, customsforgeBatchSize) if customsforgeApiKey else None

http.client.HTTPConnection.debuglevel = 1 if systemEnableHttpDebug else 0


# in this section we print the status of all modules
print('Customsforge client available.') if client else print('Could not configure customsforge client.')


# in this section we launch all relevant modules into action, enabling bot functionality in full
if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Main will only execute when there are no parameters.')
