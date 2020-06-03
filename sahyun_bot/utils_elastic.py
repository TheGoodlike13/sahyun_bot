import webbrowser
from typing import Callable, FrozenSet, List, Iterator, Type

from elasticsearch import Elasticsearch
from elasticsearch_dsl.analysis import Analyzer
from elasticsearch_dsl.connections import get_connection
from tldextract import extract

from sahyun_bot.elastic import CustomDLC, ManualUserRank
from sahyun_bot.elastic_settings import BaseDoc, TEST_ONLY_VALUES
from sahyun_bot.the_danger_zone import nuke_from_orbit
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

DOCUMENTS = frozenset([
    CustomDLC,
    ManualUserRank,
])


class ElasticAware:
    def __init__(self, use_elastic: bool = False):
        self.use_elastic = use_elastic

    def set_use_elastic(self, use: bool):
        LOG.warning('Elastic is %sabled for %s.', 'en' if use else 'dis', type(self).__name__)
        self.use_elastic = use


def print_elastic_indexes():
    for doc in DOCUMENTS:
        LOG.warning('Using %s index: <%s>.', doc.__name__, doc.index_name())


def setup_elastic(*modules: ElasticAware) -> bool:
    """
    Initializes all indexes if they do not yet exist. See set of documents to initialize above.
    Also verifies if the mappings in the index match.
    """
    is_setup = _with_elastic('setup', _setup)
    setup_elastic_usage(*modules, use_elastic=is_setup)
    return is_setup


def setup_elastic_usage(*modules: ElasticAware, use_elastic: bool):
    for m in modules:
        m.set_use_elastic(use_elastic)


def purge_elastic() -> bool:
    """
    Deletes all indexes that are associated with this application. Intended for use with tests or while developing.
    This will delete all data if used!
    """
    return _with_elastic('purge', _purge)


def migrate(doc: Type[BaseDoc], index: str) -> bool:
    """
    When changes are made to a document, it needs to be re-indexed to take effect. Failing to do so can lead to
    crashes or weird search results.

    The procedure to migrate safely is as follows:
    1. Perform any changes (e.g. development) on the document.
    2. Restart the bot in REPL mode.
    3. Once it is ready, change the document index name in config.ini file. Copy this name as well.
    4. Execute this function with document class and the copied name as parameters.
    5. Wait.
    6. If it takes longer than 60 seconds, the call may exit abruptly - it likely means the indexing has succeeded.
       But additional checking needs to be done to be sure (such as count of documents in the new index).
    7. That is all, bot is ready to go with new document settings.

    :returns re-indexes given document to another index
    """
    if index in TEST_ONLY_VALUES:
        nuke_from_orbit('Cannot migrate to test indexes!')

    return _with_elastic(f'migrate {doc.__name__} for', lambda es: _migrate(es, doc, index))


def find(query: str, results: int = None) -> List[CustomDLC]:
    """
    Searches for matching CDLCs in the index.
    """
    s = CustomDLC.search(query)
    result = list(s[:results] if results else s)
    if not result:
        LOG.warning('No CDLCs matching <%s> were found.', query)

    for hit in result:
        LOG.warning('(%5.2f) Found CDLC#%05d %s: <%s>', hit.meta.score, hit.id, hit, hit.link)

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


def domain_example(domain: str, skip: int = 0) -> str:
    all_links = domain_all(domain)

    link = ''
    for i in range(skip + 1):
        link = next(all_links, '')
        if not link:
            return LOG.warning('No more examples for domain <%s> found.', domain)

    return link


def domain_all(domain: str) -> Iterator[str]:
    for hit in CustomDLC.search().scan():
        if extract(hit.link).registered_domain == domain:
            LOG.warning('Found CDLC#%05d <%s>', hit.id, hit)
            yield hit.link


def tokenize(analyzer: Analyzer, text: str):
    LOG.warning(f'Analyzing <{text}> with {analyzer._name}.')
    result = analyzer.simulate(text)

    for token in result.tokens:
        LOG.warning(f'POS {token.position}: {token.token} [{token.start_offset}:{token.end_offset}] ({token.type})')


def _with_elastic(do: str, action: Callable[[Elasticsearch], None]) -> bool:
    try:
        action(get_connection())
        return True
    except Exception as e:
        LOG.warning('Could not %s elastic. Perhaps client is down?', do)
        return debug_ex(e, f'{do} elastic', LOG, silent=True)


def _setup(es: Elasticsearch):
    for doc in DOCUMENTS:
        index = doc.index_name()
        if es.indices.exists(index):
            mapping_on_server = es.indices.get_mapping(index)[index]['mappings']
            if mapping_on_server != doc.mapping():
                LOG.critical('Mapping mismatch for %s! Using this index may produce unpredictable results!', index)
        else:
            LOG.warning('Initializing index: %s.', index)
            doc.init()


def _purge(es: Elasticsearch):
    for doc in DOCUMENTS:
        LOG.critical('Deleting index & its contents (if it exists): %s', doc.index_name())
        doc._index.delete(ignore=[404])


def _migrate(es: Elasticsearch, doc: Type[BaseDoc], index: str):
    original_index = doc.index_name()
    if not es.indices.exists(original_index):
        raise ValueError(f'Original index does not exist: {original_index}')

    if es.indices.exists(index):
        raise ValueError(f'Index already exists: {index}')

    doc._index._name = index
    LOG.warning('Initializing index: %s.', index)
    doc.init()

    LOG.warning('Copying data from %s to %s.', original_index, index)
    es.reindex({'source': {'index': original_index}, 'dest': {'index': index}}, request_timeout=60)

    LOG.critical('Deleting original index & its contents: %s', doc.index_name())
    es.indices.delete(original_index)

    LOG.warning(f'Index for {doc.__name__} has been migrated to {index}.')
    LOG.warning(f'Please update your config.ini file to keep these changes!')
