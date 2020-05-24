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
    Executes commands. Available commands are dynamically resolved from sahyun_bot.commands package.

    Given beans and other commands will be passed into every command constructor.
    """
    def __init__(self, **beans):
        self.__commands = {}

        for module_name, module in sys.modules.items():
            if 'sahyun_bot.commands.' in module_name:
                for command_class_name, command_class in inspect.getmembers(module, self.__is_command_class):
                    if not self.__is_abstract(command_class_name):
                        self.__create_and_cache(command_class, **beans)

    def execute(self, sender: str, message: str, respond: ResponseHook) -> ResponseHook:
        """
        Parses a message by some sender. If it is an available command, executes it.

        Before execution, the command will be checked against timeouts and user rights.

        Hook will be used to send a response, if any.
        Most generic errors (e.g. no such command) will simply be ignored.
        """
        if message and message[:1] == '!':
            name, space, args = message[1:].partition(' ')
            name = name.lower()

            command = self.__commands.get(name, None)
            if not command:
                return LOG.warning(f'No command with alias <{name}> exists.')

            try:
                command.execute(sender, args, respond)
            except Exception as e:
                respond.to_sender('Unexpected error occurred. Please try later.')
                debug_ex(e, f'executing <{command}>', LOG)

        return respond

    def __is_command_class(self, item) -> bool:
        return inspect.isclass(item) and issubclass(item, Command)

    def __is_abstract(self, command_class_name: str):
        return command_class_name == 'Command' or command_class_name[:4] == 'Base'

    def __create_and_cache(self, command_class, **beans):
        try:
            command = command_class(commands=self.__commands, **beans)
        except Exception as e:
            LOG.warning('Command <!%s> (and aliases) not available. See logs.', command_class.__name__.lower())
            return debug_ex(e, f'create command for class {command_class}', LOG, silent=True)

        for alias in command.alias():
            if self.__commands.setdefault(alias, command) is not command:
                raise RuntimeError(f'Programming error: multiple commands have the same alias: {alias}')
