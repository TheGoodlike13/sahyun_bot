from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.twitchy import Twitchy
from sahyun_bot.users import Users
from sahyun_bot.users_settings import User, UserRank


class Hosts(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__users: Users = beans.get('us')
        self.__twitch: Twitchy = beans.get('tw', None)

    def is_available(self) -> bool:
        return self.__twitch is not None

    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        """
        Prints the list of hosts for the channel.
        """
        streamer = self.__users.admin().nick
        hosts = self.__twitch.hosts(streamer)
        message = ', '.join(hosts)
        respond.to_sender(f'Hosts: {message}')
