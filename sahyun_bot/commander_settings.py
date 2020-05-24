from typing import Iterator, List


class Command:
    """
    Base class for all commands. All implementations of this class in 'commands' package are dynamically loaded.

    If you wish to create another abstract Command subclass, include 'Base' in its name. Conversely, no fully
    implemented command can have 'Base' in its name.

    If you need any functionality from the application, search the 'beans' parameter in the constructor.
    Keys & values should be equivalent to the global objects created in 'modules.py'.
    """
    def __init__(self, **beans):
        pass

    def alias(self) -> Iterator[str]:
        """
        :returns all ways to call the command, e.g. Time -> ['time'], Playlist -> ['playlist', 'list']
        """
        yield type(self).__name__.lower()

    def execute(self, nick: str, params: str) -> List[str]:
        """
        Executes the command with given parameters. At this stage, it is safe to assume that the user is
        not timed out & is authorized to use the command. Further authorization is only needed if the command
        itself is dynamic with respect to user role.

        :returns result of execution as messages to the user
        :raises CommandError: if execution was unsuccessful, with explanation (if possible)
        """
        raise NotImplementedError


class CommandError(Exception):
    """
    Common error for command execution. Args passed into it are equivalent to returned messages.
    """
    pass
