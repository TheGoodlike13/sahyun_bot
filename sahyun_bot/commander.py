import inspect
import sys

from sahyun_bot.commander_settings import *
# noinspection PyUnresolvedReferences
from sahyun_bot.commands import *
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


class TheCommander:
    """
    Executes commands. The commands are dynamically resolved from sahyun_bot.commands package.

    Given beans and other commands will be passed into every command constructor.
    """
    def __init__(self, **beans):
        self.__commands = {}

        for module_name, module in sys.modules.items():
            if 'sahyun_bot.commands.' in module_name:
                for command_class_name, command_class in inspect.getmembers(module, self.__is_command_class):
                    if not self.__is_abstract(command_class_name):
                        self.__create_and_cache(command_class, beans)

    def executest(self, nick: str, message: str) -> str:
        """
        :returns same as #execute, but joins all messages into a single string for easier testing
        """
        return '\n'.join(self.execute(nick, message))

    def execute(self, nick: str, message: str) -> List[str]:
        """
        :returns result of executing the command as messages to display to the executor
        """
        if not message or not message[:1] == '!':
            return []

        name, space, params = message[1:].partition(' ')
        name = name.lower()

        command = self.__commands.get(name, None)
        if not command:
            LOG.warning(f'No command with alias <{name}> exists.')
            return []

        try:
            return self.__execute(command, nick, params)
        except Exception as e:
            debug_ex(e, f'executing <{command}>', LOG)
            return []

    def __is_command_class(self, item) -> bool:
        return inspect.isclass(item) and issubclass(item, Command)

    def __is_abstract(self, command_class_name: str):
        return command_class_name == 'Command' or 'Base' in command_class_name

    def __create_and_cache(self, command_class, beans):
        try:
            command = command_class(commands=self.__commands, **beans)
        except Exception as e:
            LOG.warning('Command <!%s> (and aliases) not available. See logs.', command_class.__name__.lower())
            return debug_ex(e, f'create command for class {command_class}', LOG, silent=True)

        self.__register(command)

    def __register(self, command: Command):
        for alias in command.alias():
            if self.__commands.setdefault(alias, command) is not command:
                raise RuntimeError(f'Programming error: multiple commands have the same alias: {alias}')

    def __execute(self, command: Command, nick: str, params: str) -> List[str]:
        try:
            return command.execute(nick, params)
        except CommandError as e:
            return list(e.args)
