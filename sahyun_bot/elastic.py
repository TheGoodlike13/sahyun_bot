import logging
from datetime import datetime, timezone
from typing import Optional, List

from elasticsearch_dsl import Text, Keyword, Boolean, Long, Date, A
from elasticsearch_dsl.connections import get_connection

from sahyun_bot import elastic_settings
from sahyun_bot.elastic_settings import BaseDoc
from sahyun_bot.utils import debug_ex

elastic_settings.ready_or_die()

LOG = logging.getLogger(__name__.rpartition('.')[2])


# noinspection PyProtectedMember
def setup_elastic() -> bool:
    try:
        if not get_connection().indices.exists(CustomDLC._index._name):
            LOG.debug('Initializing index: ' + CustomDLC._index._name)
            CustomDLC.init()
    except Exception as e:
        LOG.warning('Could not setup elastic. Perhaps client is down?')
        return debug_ex(e, 'setup elastic', log=LOG)

    return True


# noinspection PyProtectedMember
def purge_elastic() -> bool:
    """
    Utility function to cleanup index. Intended to be used while developing or testing.
    """
    try:
        LOG.warning('Deleting index & its contents: ' + CustomDLC._index._name)
        CustomDLC._index.delete(ignore=[404])
        return True
    except Exception as e:
        return debug_ex(e, 'purge elastic', log=LOG)


# noinspection PyTypeChecker
class CustomDLC(BaseDoc):
    artist = Text(required=True)
    title = Text(required=True)
    album = Text(required=True)
    author = Text(required=True)
    tuning = Keyword(required=True)
    parts = Keyword(multi=True, required=True)
    platforms = Keyword(multi=True, required=True)
    has_dynamic_difficulty = Boolean(required=True)
    is_official = Boolean(required=True)

    version_timestamp = Long(required=True)
    version_time = Date(required=True, default_timezone='UTC')

    indirect_link = Keyword(required=True)
    direct_link = Keyword()
    music_video = Keyword()

    from_auto_index = Boolean(required=True)

    class Index:
        name = elastic_settings.e_cf_index
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).extra(explain=elastic_settings.e_explain)

    def save(self, **kwargs):
        if not self.version_time:
            self.version_time = datetime.fromtimestamp(self.version_timestamp, timezone.utc)

        if not self.from_auto_index:
            self.from_auto_index = False

        return super(CustomDLC, self).save(**kwargs)

    @property
    def full_title(self) -> str:
        return self.artist + ' - ' + self.title

    @property
    def link(self) -> str:
        return self.direct_link if self.direct_link else self.indirect_link


def last_auto_index_time() -> Optional[int]:
    s = CustomDLC.search().filter('term', from_auto_index=True)
    s.aggs.metric('last_auto_index_time', A('max', field='version_timestamp'))
    response = s.execute()
    return response.aggs.last_auto_index_time.value


def request(query: str) -> List[CustomDLC]:
    s = CustomDLC.search().query('multi_match', query=query, fields=elastic_settings.e_req_fields)
    return list(s[:elastic_settings.e_req_max])
