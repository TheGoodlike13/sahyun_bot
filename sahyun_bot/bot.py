import sys
from configparser import ConfigParser

from sahyun_bot.customsforge import CustomsForgeClient

config = ConfigParser()
config.read('config.ini')

client = CustomsForgeClient(config['customsforge']['ApiKey'])


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Main will only execute when there are no parameters.')
