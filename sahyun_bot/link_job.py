import inspect
import sys
import webbrowser
from typing import List

import pyperclip

from sahyun_bot.link_job_properties import LinkJob
# noinspection PyUnresolvedReferences
from sahyun_bot.links import *
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


class BrowseLink(LinkJob):
    def handle(self, link: str):
        webbrowser.open(link, new=2, autoraise=False)


class CopyLinkToPaste(LinkJob):
    def handle(self, link: str):
        LOG.warning('Link %s copied to clipboard.', link)
        pyperclip.copy(link)


class IgnoreLink(LinkJob):
    def handle(self, link: str):
        pass


class LinkJobFactory(LinkJob):
    """
    Handles links based on dynamically resolved LinkJobs in sahyun_bot.links package.

    Uses fallback if all else fails.
    """
    def __init__(self, fallback: LinkJob, **settings):
        self.__fallback = fallback

        self.__jobs: List[LinkJob] = []
        for module_name, module in sys.modules.items():
            if 'sahyun_bot.links.' in module_name:
                for link_job_name, link_job_class in inspect.getmembers(module, self.__is_link_job):
                    self.__create_and_cache(link_job_class, **settings)

    def supports(self, link: str) -> bool:
        for job in self.__jobs:
            if job.supports(link):
                return True

        return self.__fallback.supports(link)

    def handle(self, link: str):
        for job in self.__jobs:
            if job.supports(link):
                try:
                    return job.handle(link)
                except Exception as e:
                    debug_ex(e, f'download {link}', LOG)

        self.__fallback.handle(link)

    def __is_link_job(self, item) -> bool:
        return inspect.isclass(item) and issubclass(item, LinkJob)

    def __create_and_cache(self, link_job_class, **settings):
        try:
            link_job = link_job_class(**settings)
        except Exception as e:
            LOG.warning('LinkJob <!%s> not available. See logs.', link_job_class.__name__)
            return debug_ex(e, f'create command for class {link_job_class}', LOG, silent=True)

        self.__jobs.append(link_job)
