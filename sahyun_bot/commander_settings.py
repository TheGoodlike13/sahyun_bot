from typing import Iterator

from sahyun_bot.users_settings import UserRank, User
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


class ResponseHook:
    """
    Base class for handling responses to the commands.
    """
    def to_sender(self, message: str) -> bool:
        """
        Respond directly to sender.
        :returns true, always
        """
        raise NotImplementedError

    def to_channel(self, message: str) -> bool:
        """
        Send message to the channel, not specific sender.
        :returns true, always
        """
        raise NotImplementedError

    def to_debug(self, message: str):
        """
        Write a debug message. Feel free to override for testing purposes.
        """
        LOG.debug(message)


class Command:
    """
    Base class for all commands. All implementations of this class in 'commands' package are dynamically loaded.

    Abstract implementations of this class should start with 'Base'. Conversely, non-abstract implementations
    should never start with 'Base'.

    All 'commands' are passed in as dict. This dict is a reference shared with TheCommander and should not be
    modified.

    The beans passed into the commands are named the same as globals from 'modules.py'.
    If some bean is not available, prefer to return false with #is_available rather than throwing an exception.
    """
    def __init__(self, **beans):
        pass

    def is_available(self) -> bool:
        """
        :returns true if all required modules are available, false if any of them is missing
        """
        return True

    def alias(self) -> Iterator[str]:
        """
        :returns all ways to call the command, e.g. Time -> ['time'], Playlist -> ['playlist', 'list']
        """
        yield type(self).__name__.lower()

    def the_alias(self) -> str:
        """
        :returns first alias
        """
        return next(self.alias())

    def min_rank(self) -> UserRank:
        """
        :returns minimum rank required to use this command; ADMIN by default
        """
        return UserRank.ADMIN

    def execute(self, user: User, alias: str, args: str, respond: ResponseHook) -> bool:
        """
        Executes the command with given args & responds to given hook.
         
        At this stage, it is safe to assume that the user is not timed out & is authorized to use the command.
        Further authorization is only needed if the command itself is dynamic with respect to the user role.
        
        :param user: one who requested command execution
        :param alias: the alias of this command that was used to execute it
        :param args: parameters passed in with the command, unparsed
        :param respond: callback to allow responding to the command
        :returns true if execution failed, false or None if it succeeded
        """
        raise NotImplementedError

    def executest(self,
                  respond: ResponseHook,
                  rank: UserRank = UserRank.ADMIN,
                  alias: str = None,
                  args: str = '') -> ResponseHook:
        """
        Same as execute, but returns ResponseHook. Allows using this method call as context for hook cleanup.
        """
        user = User(nick='_test', rank=rank)
        failure = self.execute(user, alias or self.the_alias(), args, respond)
        respond.to_debug('failure' if failure else 'success')
        return respond

    def _all_args(self, alias: str, args: str) -> Iterator[str]:
        """
        Helper for parsing commands which use alias as an argument.

        :returns infinite iterator containing all args and empty strings beyond that
        """
        yield alias
        yield from args.split()
        while True:
            yield ''
