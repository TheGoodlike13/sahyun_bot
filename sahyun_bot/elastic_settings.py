"""
Initializes settings for elastic.py.

To make the index dynamic (which also allows to switch it out for tests), the value must be explicitly initialized
by some other module. If this does not happen, and somebody attempts to load elastic.py, 'ready_or_die' will get
executed which will shut down the application, thus preventing any shenanigans with the wrong parameters being used.

At least in normal circumstances :)
"""
from datetime import timezone, datetime
from typing import Optional, List, Union

from elasticsearch_dsl import Document, Date, integer_types, ValidationException, Search
from elasticsearch_dsl.query import Query

from sahyun_bot.the_danger_zone import nuke_from_orbit
from sahyun_bot.utils import NON_EXISTENT
from sahyun_bot.utils_settings import read_config, parse_bool, parse_list

DEFAULT_HOST = 'localhost'
DEFAULT_CUSTOMSFORGE_INDEX = 'cdlcs'
DEFAULT_USER_INDEX = 'users'

DEFAULT_FUZZINESS = 'auto:5,11'
DEFAULT_SHINGLE_CEILING = 3

DEFAULT_PLATFORMS = ['pc']
DEFAULT_PARTS = ['lead', 'rhythm']
DEFAULT_OFFICIAL = False

TEST_CUSTOMSFORGE_INDEX = DEFAULT_CUSTOMSFORGE_INDEX + '_test'
TEST_USER_INDEX = DEFAULT_USER_INDEX + '_test'
TEST_ONLY_VALUES = frozenset([
    TEST_CUSTOMSFORGE_INDEX,
    TEST_USER_INDEX,
])

e_host = NON_EXISTENT

e_cf_index = NON_EXISTENT
e_rank_index = NON_EXISTENT

e_fuzzy = NON_EXISTENT
e_shingle = NON_EXISTENT

e_explain = NON_EXISTENT
e_refresh = False

e_platforms = NON_EXISTENT
e_parts = NON_EXISTENT
e_allow_official = NON_EXISTENT


def important_values() -> List:
    return [e_cf_index, e_rank_index]


def ready_or_die():
    """
    Immediately shuts down the application if the module is not properly configured.
    Make the call immediately after imports in every module that depends on this configuration to be loaded.
    """
    if NON_EXISTENT in important_values():
        nuke_from_orbit('programming error - elastic module imported before elastic_settings is ready!')


def init():
    global e_host
    global e_cf_index
    global e_rank_index
    global e_fuzzy
    global e_shingle
    global e_explain
    global e_platforms
    global e_parts
    global e_allow_official

    e_host = read_config('elastic', 'Host', fallback=DEFAULT_HOST)
    e_cf_index = read_config('elastic', 'CustomsforgeIndex', fallback=DEFAULT_CUSTOMSFORGE_INDEX)
    e_rank_index = read_config('elastic', 'RankIndex', fallback=DEFAULT_USER_INDEX)
    e_fuzzy = read_config('elastic', 'Fuzziness', fallback=DEFAULT_FUZZINESS)
    e_shingle = read_config('elastic', 'ShingleCeiling', convert=int, fallback=DEFAULT_SHINGLE_CEILING)
    e_explain = read_config('elastic', 'Explain', convert=parse_bool, fallback=False)
    # noinspection PyTypeChecker
    e_platforms = read_config('elastic', 'Platforms', convert=parse_list, fallback=DEFAULT_PLATFORMS)
    # noinspection PyTypeChecker
    e_parts = read_config('elastic', 'Parts', convert=parse_list, fallback=DEFAULT_PARTS)
    e_allow_official = read_config('elastic', 'RandomOfficial', convert=parse_bool, fallback=DEFAULT_OFFICIAL)

    e_shingle = max(2, e_shingle)

    for value in important_values():
        if value in TEST_ONLY_VALUES:
            nuke_from_orbit('configuration error - cannot use TEST values for REAL initialization')


def init_test():
    global e_host
    global e_cf_index
    global e_rank_index
    global e_fuzzy
    global e_shingle
    global e_explain
    global e_refresh
    global e_platforms
    global e_parts
    global e_allow_official

    e_host = DEFAULT_HOST
    e_cf_index = TEST_CUSTOMSFORGE_INDEX
    e_rank_index = TEST_USER_INDEX
    e_fuzzy = DEFAULT_FUZZINESS
    e_shingle = DEFAULT_SHINGLE_CEILING
    e_explain = True
    e_refresh = True
    e_platforms = DEFAULT_PLATFORMS
    e_parts = DEFAULT_PARTS
    e_allow_official = DEFAULT_OFFICIAL


RANDOM_SORT = {
    '_script': {
        'script': 'Math.random()',
        'type': 'number',
    },
}


class BaseDoc(Document):
    @classmethod
    def index_name(cls) -> Optional[str]:
        return cls._index._name if cls._index else None

    @classmethod
    def mapping(cls) -> Optional[dict]:
        return cls._doc_type.mapping.to_dict()

    @classmethod
    def search(cls, **kwargs) -> Search:
        return super().search(**kwargs).extra(explain=e_explain)

    @classmethod
    def as_lucine(cls, query: Union[Query, dict], **kwargs) -> str:
        """
        :returns given query as it will be interpreted by the index of this document in Lucine format
        """
        kwargs['explain'] = True
        kwargs['rewrite'] = True

        es = cls._get_connection()
        body = query if isinstance(query, dict) else {'query': query.to_dict()}
        result = es.indices.validate_query(body, cls._default_index(), **kwargs)
        if 'error' in result:
            raise ValueError(result['error'])

        return result['explanations'][0]['explanation']

    def explain(self, query: Query, **kwargs) -> dict:
        """
        :returns lucine query, whether it matches this document & basic explanation why or why not
        """
        es = self._get_connection()
        body = {'query': query.to_dict()}
        response = es.explain(self._get_index(), self.meta.id, body=body, **kwargs)
        return {
            'search': self.as_lucine(body),
            'match': response['matched'],
            'reason': response['explanation'],
        }

    def terms(self, *fields: str, **kwargs) -> dict:
        """
        :returns for every field, the terms that have been analyzed for this particular document
        """
        vectors = self.term_vectors(*fields, **kwargs)
        return {field_name: list(data['terms'].keys()) for field_name, data in vectors.items()}

    def term_vectors(self, *fields: str, **kwargs) -> dict:
        """
        :returns for every field, information about the terms that have been analyzed for this particular document
        """
        es = self._get_connection()
        response = es.termvectors(index=self._get_index(), id=self.meta.id, fields=fields, **kwargs)
        return response['term_vectors']

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
