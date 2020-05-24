"""
Trivial commands that do not touch any application functionality. Usually do not even need any testing.
"""

from datetime import datetime
from typing import List

from sahyun_bot.commander_settings import Command


class Time(Command):
    """
    Prints current time in UTC.
    """
    def execute(self, nick: str, params: str) -> List[str]:
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        return [f'{nick}: The time is now {now} UTC']
