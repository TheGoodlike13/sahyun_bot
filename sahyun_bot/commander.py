import inspect
import sys
from typing import Dict

from sahyun_bot.commander_settings import *
# noinspection PyUnresolvedReferences
from sahyun_bot.commands import *
from sahyun_bot.users import Users
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


class TheCommander:
    """
    Executes commands. Available commands are dynamically resolved from sahyun_bot.commands package.

    Given beans and other commands will be passed into every command constructor.
    """
    def __init__(self, **beans):
        self._users: Users = beans.get('us')  # user factory is always available

        self.__commands: Dict[str, Command] = {}

        for module_name, module in sys.modules.items():
            if 'sahyun_bot.commands.' in module_name:
                for command_class_name, command_class in inspect.getmembers(module, self.__is_command_class):
                    if not self.__is_abstract(command_class_name):
                        self.__create_and_cache(command_class, **beans)

    def executest(self, sender: str, message: str, respond: ResponseHook) -> ResponseHook:
        """
        Same as execute, but returns ResponseHook. Allows using this method call as context for hook cleanup.
        """
        success = self.execute(sender, message, respond)
        respond.to_debug('success' if success else 'failure')
        return respond

    def execute(self, sender: str, message: str, respond: ResponseHook) -> bool:
        """
        Parses a message by some sender. If it is an available command, executes it.
        Sender starting with underscore is considered admin (e.g., _console, _test). Such names are not allowed
        by twitch by default.

        Before execution, the command will be checked against timeouts and user rights.

        Hook will be used to send a response, if any.
        Most generic errors (e.g. no such command) will simply be ignored.

        :returns true if execution succeeded, false if it failed or never executed in the first place
        """
        if message and message[:1] == '!':
            name, space, args = message[1:].partition(' ')
            name = name.lower()

            command = self.__commands.get(name, None)
            if not command:
                return LOG.warning('No command with alias <%s> exists.', name)

            user = self._users.get_admin() if sender[:1] == '_' else self._users.get(sender)
            if not user.has_right(command.min_rank()):
                if self.__just_needs_to_follow(command, user):
                    respond.to_sender(f'Please follow the channel to use !{name}')

                return LOG.warning('<%s> is not authorized to use !%s.', user, name)

            try:
                return command.execute(user, args, respond)
            except Exception as e:
                respond.to_sender('Unexpected error occurred. Please try later.')
                debug_ex(e, f'executing <{command}>', LOG)

    def __just_needs_to_follow(self, command, user):
        return user.rank == UserRank.VWR and command.min_rank() == UserRank.FLWR

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

        self._add_command(command)

    def _add_command(self, command: Command):
        """
        Registers given command to this commander. Should only be used by automatic loading (during initialization)
        or tests.
        """
        for alias in command.alias():
            if self.__commands.setdefault(alias, command) is not command:
                raise RuntimeError(f'Programming error: multiple commands have the same alias: {alias}')
