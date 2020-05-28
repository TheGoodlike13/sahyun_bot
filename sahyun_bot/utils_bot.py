from sahyun_bot.commander import TheCommander
from sahyun_bot.commander_settings import ResponseHook
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


def setup_console(tc: TheCommander):
    LOG.warning('Waiting for commands.')

    hook = ToConsole()
    while True:
        line = input('>>> ')
        if line == 'exit()':
            break

        tc.execute('_console', line, hook)


class ToConsole(ResponseHook):
    def to_sender(self, message: str):
        self.to_channel(message)
        return True

    def to_channel(self, message: str):
        LOG.warning(message)
        return True
