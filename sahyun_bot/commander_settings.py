from typing import Iterator


class ResponseHook:
    """
    Base class for handling responses to the commands.
    """
    def to_sender(self, message: str):
        """
        Respond directly to sender.
        """
        raise NotImplementedError

    def to_channel(self, message: str):
        """
        Send message to the channel, not specific sender.
        """
        raise NotImplementedError


class Command:
    """
    Base class for all commands. All implementations of this class in 'commands' package are dynamically loaded.

    Abstract implementations of this class should start with 'Base'. Conversely, non-abstract implementations
    should never start with 'Base'.

    All 'commands' are passed in as dict. This dict is a reference shared with TheCommander and should not be
    modified.

    The beans passed into the commands are named the same as globals from 'modules.py'. If the command makes use
    of any, it should verify they are available in the constructor.
    """
    def __init__(self, **beans):
        pass

    def alias(self) -> Iterator[str]:
        """
        :returns all ways to call the command, e.g. Time -> ['time'], Playlist -> ['playlist', 'list']
        """
        yield type(self).__name__.lower()

    def execute(self, user: str, args: str, respond: ResponseHook):
        """
        Executes the command with given args & responds to given hook.
         
        At this stage, it is safe to assume that the user is not timed out & is authorized to use the command.
        Further authorization is only needed if the command itself is dynamic with respect to the user role.
        
        :param user: one who requested command execution
        :param args: parameters passed in with the command, unparsed
        :param respond: callback to allow responding to the command
        """
        raise NotImplementedError
