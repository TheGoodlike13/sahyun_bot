from asyncio import run_coroutine_threadsafe, new_event_loop
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

import pydle

from sahyun_bot.commander import TheCommander
from sahyun_bot.commander_settings import ResponseHook
from sahyun_bot.irc_bot_settings import *
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

TWITCH_IRC = 'irc.twitch.tv'
TWITCH_IRC_PORT = 6697


class ToIrc(ResponseHook):
    def __init__(self, bot: pydle.Client, channel: str, sender: str):
        self.__bot = bot
        self.__channel = channel
        self.__sender = sender

    def to_sender(self, message: str):
        self.to_channel(f'{self.__sender}: {message}')

    def to_channel(self, message: str):
        run_coroutine_threadsafe(self.__bot.message(self.__channel, message), self.__bot.eventloop)


# noinspection PyPep8Naming
class botyun(pydle.Client):
    def __init__(self,
                 tc: TheCommander,
                 nickname: str,
                 token: str,
                 channels: List[str],
                 max_threads: int = MAX_CONCURRENT_COMMANDS):
        self.__tc = tc
        self.__token = token
        self.__channels = [f'#{c}' for c in channels]
        self.__pool = ThreadPoolExecutor(max_threads + 1)  # the extra thread is where the event loop should run

        self.eventloop = None
        super().__init__(nickname=nickname, eventloop='this prevents default loop from being initialized')

    def launch_in_own_thread(self):
        self.__pool.submit(self.__launch)

    def close(self):
        if self.eventloop and not isinstance(self.eventloop, str):
            self.eventloop.call_soon_threadsafe(self.eventloop.stop)

        self.__pool.shutdown()

    async def on_message(self, target, source, message):
        hook = ToIrc(bot=self, channel=target, sender=source)
        await self.eventloop.run_in_executor(self.__pool, self.__tc.execute, source, message, hook)

    def __launch(self):
        try:
            self.eventloop = new_event_loop()
            self.run(
                hostname=TWITCH_IRC,
                port=TWITCH_IRC_PORT,
                password=self.__token,
                channels=self.__channels,
                tls=True,
                tls_verify=False,
            )
        except Exception as e:
            LOG.warning('IRC bot launch failed.')
            debug_ex(e, 'launching IRC bot', LOG)
