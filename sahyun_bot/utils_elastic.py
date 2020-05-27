import webbrowser
from typing import Callable, FrozenSet, List, Iterator

from elasticsearch import Elasticsearch
from elasticsearch_dsl.connections import get_connection
from tldextract import extract

from sahyun_bot.elastic import CustomDLC, ManualUserRank
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

DOCUMENTS = frozenset([
    CustomDLC,
    ManualUserRank,
])


def print_elastic_indexes():
    for doc in DOCUMENTS:
        LOG.warning('Using %s index: <%s>.', doc.__name__, doc.index_name())


def setup_elastic() -> bool:
    """
    Initializes all indexes if they do not yet exist. See set of documents to initialize above.
    Also verifies if the mappings in the index match.
    """
    return _with_elastic('setup', _setup)


def purge_elastic() -> bool:
    """
    Deletes all indexes that are associated with this application. Intended for use with tests or while developing.
    This will delete all data if used!
    """
    return _with_elastic('purge', _purge)


def find(query: str) -> List[CustomDLC]:
    """
    Searches for matching CDLCs in the index.
    """
    result = list(CustomDLC.request(query))
    if not result:
        LOG.warning('No CDLCs matching <%s> were found.', query)

    for hit in result:
        LOG.warning('Found CDLC <%s>: <%s>', hit.full_title, hit.link)

    return result


def browse(query: str):
    """
    Searches for matching CDLCs in the index and opens any found links in the browser.
    """
    for hit in find(query):
        webbrowser.open(hit.link, new=2, autoraise=False)


def domains() -> FrozenSet[str]:
    """
    :returns set of domains for all links in the current index.
    """
    return frozenset(extract(hit.link).registered_domain for hit in CustomDLC.search().scan())


def domain_example(domain: str) -> str:
    link = next(domain_all(domain), '')
    if not link:
        LOG.warning('No example for domain <%s> found.', domain)

    return link


def domain_all(domain: str) -> Iterator[str]:
    for hit in CustomDLC.search().scan():
        if extract(hit.link).registered_domain == domain:
            LOG.warning('Found CDLC #%s <%s>', hit.id, hit.full_title)
            yield hit.link


def _with_elastic(do: str, action: Callable[[Elasticsearch], None]) -> bool:
    try:
        action(get_connection())
        return True
    except Exception as e:
        LOG.warning('Could not %s elastic. Perhaps client is down?', do)
        return debug_ex(e, f'{do} elastic', LOG, silent=True)


def _setup(es):
    for doc in DOCUMENTS:
        index = doc.index_name()
        if es.indices.exists(index):
            mapping_on_server = es.indices.get_mapping(index)[index]['mappings']
            if mapping_on_server != doc.mapping():
                LOG.critical('Mapping mismatch for %s! Using this index may produce unpredictable results!', index)
        else:
            LOG.warning('Initializing index: %s.', index)
            doc.init()


def _purge(es):
    for doc in DOCUMENTS:
        LOG.critical('Deleting index & its contents (if it exists): %s', doc.index_name())
        doc._index.delete(ignore=[404])
