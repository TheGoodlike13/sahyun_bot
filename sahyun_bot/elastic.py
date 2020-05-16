import logging
from datetime import datetime, timezone

from elasticsearch import ElasticsearchException
from elasticsearch_dsl import Document, Text, Keyword, Boolean, Integer, Join, Date
from elasticsearch_dsl.connections import get_connection

from sahyun_bot.utils import debug_ex

LOG = logging.getLogger(__name__.rpartition('.')[2])

CUSTOMSFORGE_TEMPLATE = 'cdoc'
CUSTOMSFORGE_INDEX = 'cdlcs'


# noinspection PyProtectedMember
def setup_elastic() -> bool:
    try:
        client = get_connection()
        if not client.ping():
            LOG.warning('Client is down')
            return False

        if not client.indices.exists(CUSTOMSFORGE_INDEX):
            LOG.debug('Initializing index template')
            CustomsforgeDocument._index.as_template(CUSTOMSFORGE_TEMPLATE).save()
    except ElasticsearchException as e:
        return debug_ex(LOG, e, 'setup elastic')


# noinspection PyProtectedMember
def purge_elastic():
    """
    Utility function to cleanup index. Intended to be used while still developing.
    """
    try:
        LOG.warning('Deleting index template')
        get_connection().indices.delete_template(CUSTOMSFORGE_TEMPLATE, ignore=[404])
    except ElasticsearchException as e:
        debug_ex(LOG, e, 'purge elastic')

    try:
        LOG.warning('Deleting index & its contents')
        CustomsforgeDocument._index.delete(ignore=[404])
    except ElasticsearchException as e:
        debug_ex(LOG, e, 'purge elastic')


class CustomsforgeDocument(Document):
    last_time_saved = Date(required=True, default_timezone='UTC')
    cdlc_link = Join(relations={'cdlc': 'link'})

    @classmethod
    def _matches(cls, hit):
        return False

    class Index:
        name = CUSTOMSFORGE_INDEX
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    def save(self, **kwargs):
        self.last_time_saved = datetime.now(timezone.utc)
        return super(CustomsforgeDocument, self).save(**kwargs)


class DirectLink(CustomsforgeDocument):
    link = Keyword(required=True)

    @classmethod
    def _matches(cls, hit):
        join = hit['_source']['cdlc_link']
        return isinstance(join, dict) and join.get('name', None) == 'link'

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).filter('term', cdlc_link='link')

    def save(self, **kwargs):
        self.meta.routing = self.cdlc_link.parent
        return super(DirectLink, self).save(**kwargs)


class CustomDLC(CustomsforgeDocument):
    artist = Text(required=True)
    title = Text(required=True)
    album = Text(required=True)
    author = Text(required=True)
    tuning = Keyword(required=True)
    parts = Keyword(multi=True, required=True)
    platforms = Keyword(multi=True, required=True)
    has_dynamic_difficulty = Boolean(required=True)
    is_official = Boolean(required=True)
    version_timestamp = Integer(required=True)
    music_video = Keyword()

    version_time = Date(required=True, default_timezone='UTC')

    @classmethod
    def _matches(cls, hit):
        return hit['_source']['cdlc_link'] == 'cdlc'

    @classmethod
    def search(cls, **kwargs):
        return cls._index.search(**kwargs).filter('term', cdlc_link='cdlc')

    # noinspection PyTypeChecker
    def save(self, **kwargs):
        self.cdlc_link = 'cdlc'
        self.version_time = datetime.fromtimestamp(self.version_timestamp, timezone.utc)
        return super(CustomDLC, self).save(**kwargs)

    def add_link(self, link: str):
        direct_link = DirectLink(
            _routing=self.meta.id,
            _index=self.meta.index,
            cdlc_link={
                'name': 'link',
                'parent': self.meta.id
            },
            link=link
        )
        direct_link.save()
