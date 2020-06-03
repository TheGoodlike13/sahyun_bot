from abc import ABC

from sahyun_bot.utils_settings import read_config

LINK_JOB_DEFAULT = 'ignore'

lj_default = read_config('links', 'Default', fallback=LINK_JOB_DEFAULT)


class LinkJob(ABC):
    """
    Strategy for handling links.
    """
    def supports(self, link: str) -> bool:
        """
        :returns true if this job supports given link
        """
        return True

    def handle(self, link: str):
        """
        Performs some task with the given link.
        """
        raise NotImplementedError
