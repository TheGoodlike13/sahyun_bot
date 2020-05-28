"""
Commands which assist with administrating the bot.

Other ADMIN-only commands may still exist in other modules, where they are more applicable.
"""

from sahyun_bot.commander_settings import Command, ResponseHook
from sahyun_bot.the_loaderer import TheLoaderer
from sahyun_bot.users import Users
from sahyun_bot.users_settings import User


class Lock(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__commander = beans.get('tc')  # TheCommander is always available

    def execute(self, user: User, args: str, respond: ResponseHook):
        """
        Stops the bot from executing any further commands unless the user is ADMIN.
        """
        is_admin_only = self.__commander.flip_admin_switch()
        message = 'is now' if is_admin_only else 'no longer'
        respond.to_sender(f'Bot {message} in ADMIN only mode')


class Index(Command):
    def __init__(self, **beans):
        super().__init__(**beans)
        self.__loaderer: TheLoaderer = beans.get('tl', None)

    def is_available(self) -> bool:
        return self.__loaderer is not None and self.__loaderer.use_elastic

    def execute(self, user: User, args: str, respond: ResponseHook):
        """
        Tries to index CDLCs from customsforge into elasticsearch.
        """
        has_loaded = self.__loaderer.load()
        message = '' if has_loaded else ' could not be'
        respond.to_sender(f'CDLCs{message} indexed')
        return not has_loaded
