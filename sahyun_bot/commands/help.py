"""
Commands which help with the use of the bot, e.g. print instructions.
"""
from typing import Dict, Iterator

from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.users_settings import User, UserRank


class Commands(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__commands: Dict[str, Command] = beans.get('commands')

    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        commands = ', '.join(self.__commands_for_rank(user))
        respond.to_sender(f'Commands: {commands}')

    def __commands_for_rank(self, user: User) -> Iterator[str]:
        skip = []
        for name, command in self.__commands.items():
            if name not in skip and user.has_right(command.min_rank()):
                skip.extend(command.alias())
                yield f'!{command.the_alias()}'
