from typing import Callable

from elasticsearch import Elasticsearch
from elasticsearch_dsl.connections import get_connection

from sahyun_bot.elastic import CustomDLC
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

DOCUMENTS = frozenset([
    CustomDLC,
])


def setup_elastic() -> bool:
    return _with_elastic('setup', _setup)


def purge_elastic() -> bool:
    return _with_elastic('purge', _purge)


def _with_elastic(do: str, action: Callable[[Elasticsearch], None]) -> bool:
    try:
        action(get_connection())
        return True
    except Exception as e:
        LOG.warning('Could not %s elastic. Perhaps client is down?', do)
        return debug_ex(e, f'{do} elastic', log=LOG, silent=True)


def _setup(es):
    for doc in DOCUMENTS:
        index = doc.index_name()
        if es.indices.exists(index):
            mapping_on_server = es.indices.get_mapping(index)[index]['mappings']
            if mapping_on_server != doc.mapping():
                LOG.critical('Mapping mismatch for %s! Using this index may produce unpredictable results!', index)
        else:
            LOG.warning('Initializing index: %s', index)
            doc.init()


def _purge(es):
    for doc in DOCUMENTS:
        LOG.critical('Deleting index & its contents (if it exists): %s', doc.index_name())
        doc._index.delete(ignore=[404])
