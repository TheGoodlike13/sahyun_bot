"""
Trivial commands that do not touch any application functionality. Usually do not even need any testing.
"""
import time
from datetime import datetime
from threading import Thread

from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.users_settings import UserRank, User


class Time(Command):
    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        """
        Responds with current time in UTC.
        """
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')
        respond.to_sender(f'The time is now {now} UTC')


class Joke(Command):
    def min_rank(self) -> UserRank:
        return UserRank.VWR

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook):
        """
        Tells the most awesome joke ever.
        """
        Thread(target=self.__joke_time, args=[respond]).start()

    def __joke_time(self, respond: ResponseHook):
        respond.to_sender('First, a joke. What do you get when you cross an owl with a bungee cord?')
        time.sleep(12)
        respond.to_sender('My ass. Nyah, he he, he he, he ha')
        time.sleep(5)
        respond.to_sender('ENOUGH')
