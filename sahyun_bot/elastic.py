from __future__ import annotations

from typing import Optional, Iterator

from elasticsearch_dsl import Text, Keyword, Boolean, Long, A

from sahyun_bot import elastic_settings
from sahyun_bot.elastic_settings import BaseDoc, EpochSecond
from sahyun_bot.utils_logging import get_logger

elastic_settings.ready_or_die()

LOG = get_logger(__name__)


# noinspection PyTypeChecker
class CustomDLC(BaseDoc):
    id = Long(required=True)
    artist = Text(required=True, fields={'raw': Keyword()})
    title = Text(required=True, fields={'raw': Keyword()})
    album = Text(required=True, fields={'raw': Keyword()})
    tuning = Keyword(required=True)
    instrument_info = Keyword(multi=True)
    parts = Keyword(multi=True, required=True)
    platforms = Keyword(multi=True, required=True)
    has_dynamic_difficulty = Boolean(required=True)
    is_official = Boolean(required=True)

    author = Keyword(required=True)
    version = Keyword(required=True)

    direct_download = Keyword()
    download = Keyword(required=True)
    info = Keyword(required=True)
    video = Keyword()
    art = Keyword()

    snapshot_timestamp = Long(required=True, fields={'as_date': EpochSecond()})

    from_auto_index = Boolean()

    class Index:
        name = elastic_settings.e_cf_index
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    @property
    def full_title(self) -> str:
        return self.artist + ' - ' + self.title

    @property
    def link(self) -> str:
        return self.direct_download if self.direct_download else self.download

    @classmethod
    def earliest_non_index(cls) -> Optional[int]:
        s = cls.search().exclude('term', from_auto_index=True)
        s.aggs.metric('earliest_non_index', A('min', field='snapshot_timestamp'))
        response = s[0:0].execute()
        return response.aggs.earliest_non_index.value

    @classmethod
    def latest_auto_time(cls) -> Optional[int]:
        """
        When indexing, it is imperative that any automatic process sets the 'from_auto_index' flag. This way the process
        can know which CDLCs came from it. We can use this knowledge to find the timestamp stored with the CDLC to
        continue the process from where it finished last time.

        :returns timestamp which can be used to resume automatic indexing
        """
        ceiling = cls.earliest_non_index()

        s = cls.search().filter('term', from_auto_index=True)
        if ceiling:
            s = s.filter('range', snapshot_timestamp={'lte': ceiling})

        s.aggs.metric('latest_auto_time', A('max', field='snapshot_timestamp'))
        response = s[0:0].execute()
        return response.aggs.latest_auto_time.value

    @classmethod
    def request(cls, query: str) -> Iterator[CustomDLC]:
        """
        :returns CDLCs that loosely match the search query, in order of descending relevance
        """
        s = cls.search().query('multi_match', query=query, fields=elastic_settings.e_req_fields)
        for hit in s[:elastic_settings.e_req_max]:
            yield hit
