"""
Trivial commands that do not touch any application functionality. Usually do not even need any testing.
"""

from datetime import datetime

from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.users_settings import UserRank, User


class Time(Command):
    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, args: str, respond: ResponseHook) -> bool:
        """
        Prints current time in UTC.
        """
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        respond.to_sender(f'The time is now {now} UTC')
        return True
