"""
Initializes settings for elastic.py.

To make the index dynamic (which also allows to switch it out for tests), the value must be explicitly initialized
by some other module. If this does not happen, and somebody attempts to load elastic.py, 'ready_or_die' will get
executed which will shut down the application, thus preventing any shenanigans with the wrong parameters being used.

At least in normal circumstances :)
"""
from datetime import timezone, datetime
from typing import Optional, List

from elasticsearch_dsl import Document, Date, integer_types, ValidationException

from sahyun_bot.the_danger_zone import nuke_from_orbit
from sahyun_bot.utils import NON_EXISTENT
from sahyun_bot.utils_settings import read_config, parse_bool, parse_list

DEFAULT_HOST = 'localhost'
DEFAULT_CUSTOMSFORGE_INDEX = 'cdlcs'
DEFAULT_USER_INDEX = 'users'

DEFAULT_REQUEST_FIELDS = (
    'artist',
    'title',
)
DEFAULT_REQUEST_MATCH_CEILING = 3

TEST_CUSTOMSFORGE_INDEX = DEFAULT_CUSTOMSFORGE_INDEX + '_test'
TEST_USER_INDEX = DEFAULT_USER_INDEX + '_test'
TEST_ONLY_VALUES = frozenset([
    TEST_CUSTOMSFORGE_INDEX,
    TEST_USER_INDEX,
])

e_host = NON_EXISTENT

e_cf_index = NON_EXISTENT
e_rank_index = NON_EXISTENT

e_req_fields = NON_EXISTENT
e_req_max = NON_EXISTENT
e_explain = NON_EXISTENT

e_refresh = False


def values() -> List:
    return [e_host, e_cf_index, e_rank_index, e_req_fields, e_req_max, e_explain]


def ready_or_die():
    """
    Immediately shuts down the application if the module is not properly configured.
    Make the call immediately after imports in every module that depends on this configuration to be loaded.
    """
    if NON_EXISTENT in values():
        nuke_from_orbit('programming error - elastic module imported before elastic_settings is ready!')


def init():
    global e_host
    global e_cf_index
    global e_rank_index
    global e_req_fields
    global e_req_max
    global e_explain

    e_host = read_config('elastic', 'Host', fallback=DEFAULT_HOST)
    e_cf_index = read_config('elastic', 'CustomsforgeIndex', fallback=DEFAULT_CUSTOMSFORGE_INDEX)
    e_rank_index = read_config('elastic', 'UserRankIndex', fallback=DEFAULT_USER_INDEX)
    # noinspection PyTypeChecker
    e_req_fields = read_config('elastic', 'RequestFields', convert=parse_list, fallback=DEFAULT_REQUEST_FIELDS)
    e_req_max = read_config('elastic', 'RequestMatchCeiling', convert=int, fallback=DEFAULT_REQUEST_MATCH_CEILING)
    e_explain = read_config('elastic', 'Explain', convert=parse_bool, fallback=False)

    e_req_max = e_req_max if e_req_max > 0 else DEFAULT_REQUEST_MATCH_CEILING

    for e in values():
        if e in TEST_ONLY_VALUES:
            nuke_from_orbit('configuration error - cannot use TEST values for REAL initialization')


def init_test():
    global e_host
    global e_cf_index
    global e_rank_index
    global e_req_fields
    global e_req_max
    global e_explain
    global e_refresh

    e_host = DEFAULT_HOST
    e_cf_index = TEST_CUSTOMSFORGE_INDEX
    e_rank_index = TEST_USER_INDEX
    e_req_fields = DEFAULT_REQUEST_FIELDS
    e_req_max = DEFAULT_REQUEST_MATCH_CEILING
    e_explain = True
    e_refresh = True


class BaseDoc(Document):
    @classmethod
    def index_name(cls) -> Optional[str]:
        return cls._index._name if cls._index else None

    @classmethod
    def mapping(cls) -> Optional[dict]:
        return cls._doc_type.mapping.to_dict()

    @classmethod
    def search(cls, **kwargs):
        return super().search(**kwargs).extra(explain=e_explain)

    def delete(self, **kwargs):
        kwargs.setdefault('refresh', e_refresh)
        super().delete(**kwargs)

    def update(self, **kwargs):
        kwargs.setdefault('refresh', e_refresh)
        return super().update(**kwargs)

    def save(self, **kwargs):
        kwargs.setdefault('refresh', e_refresh)
        return super().save(**kwargs)


class EpochSecond(Date):
    def __init__(self, *args, **kwargs):
        kwargs.pop('default_timezone', None)
        kwargs['format'] = 'epoch_second'
        super().__init__(default_timezone=timezone.utc, *args, **kwargs)

    def _deserialize(self, data):
        if not isinstance(data, integer_types):
            raise ValidationException(f'Could not parse epoch second from the value <{data}>')

        return datetime.fromtimestamp(data, tz=timezone.utc)
