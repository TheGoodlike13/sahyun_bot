"""
Trivial commands that do not touch any application functionality. Usually do not even need any testing.
"""

from datetime import datetime

from sahyun_bot.commander_settings import Command, ResponseHook


class Time(Command):
    """
    Prints current time in UTC.
    """
    def execute(self, user: str, args: str, respond: ResponseHook):
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        respond.to_sender(f'The time is now {now} UTC')
