"""
Loads CDLC data from one format to another while preserving continuity.

This module provides implementations for the purposes of this application, but any implementation of Source,
Destination or DirectLinkSource are OK, as long as they adhere to the requirements for continuity. It is
assumed that the CDLC data inside these is authentic.

Loading CDLC data manually or through implementations that do not adhere to the contract can ruin the integrity
of the underlying data by breaking assumptions. For that reason, avoid using bootleg implementations or forged files.
"""

import json
import os
import shutil
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timezone
from itertools import dropwhile
from pathlib import Path
from queue import Queue, Empty
from tempfile import NamedTemporaryFile
from threading import Thread, Event
from typing import Iterator, Any, IO

from elasticsearch import Elasticsearch, NotFoundError

from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic import CustomDLC
from sahyun_bot.the_loaderer_settings import DEFAULT_MAX_THREADS
from sahyun_bot.utils import debug_ex, Closeable
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

CONTINUOUS_FROM = 'continuous_from'

CUSTOMSFORGE_STR = frozenset([
    'cf',
    'customsforge',
])
ELASTIC_STR = frozenset([
    'es',
    'elastic',
    'elasticsearch',
    'index',
    'elasticindex',
])


class Source(Closeable):
    def read_all(self, start_from: int = 0) -> Iterator[dict]:
        """
        Generates all CDLCs since given time of update (or beginning, if not given).
        Time is given in epoch seconds.

        If the generated CDLCs are continuous, they should be sorted by time of update, ascending.
        They should also include {'continuous_from': start_from} in the returned dict.
        """
        raise NotImplementedError


class DirectLinkSource:
    def to_direct_link(self, cdlc_id: Any) -> str:
        """
        :returns direct download link for given CDLC id, if it is available
        """
        raise NotImplementedError


class Destination(Closeable):
    def start_from(self) -> int:
        """
        To avoid loading continuous sources from beginning, this value is used as optimization.
        :returns time, in epoch seconds, which should be passed into Source#read_all; 0 means from beginning
        """
        return 0

    def try_write(self, cdlc: dict) -> Any:
        """
        Try to write the given CDLC data into the destination.
        The actual write can be deferred until the Destination object is closed if needed.
        However, if the write is NOT deferred, it should not destroy the integrity or continuity of this destination.

        If the CDLC information is incomplete and requires updating (such as direct link), the internal
        representation of CDLC data should be returned. It will be later passed back into this destination
        for updating purposes. If update is not supported or unnecessary, return None instead.
        """
        raise NotImplementedError

    def update(self, from_write: Any, direct_link: str):
        """
        Update the CDLC data with direct link. Called if and only if try_write returns not None.

        This method should be thread-safe, as it will be called by background threads.

        :param from_write: whatever try_write returned
        :param direct_link: direct download link, if found
        """
        raise NotImplementedError


class Customsforge(Source, DirectLinkSource):
    """
    The prime source for CDLC data. Always continuous.
    """
    def __init__(self, cf: CustomsForgeClient):
        self.__cf = cf

    def read_all(self, start_from: int = 0) -> Iterator[dict]:
        LOG.warning('Loading Customsforge CDLCs from %s.', loading_from(start_from))

        for cdlc in self.__cf.cdlcs(since_exact=start_from):
            cdlc[CONTINUOUS_FROM] = start_from or 0
            yield cdlc

    def to_direct_link(self, cdlc_id: Any) -> str:
        return self.__cf.direct_link(cdlc_id)


class ElasticIndex(Source, DirectLinkSource, Destination):
    """
    Represents CDLC data in the application.

    To preserve continuity, a flag is used during indexing.
    If all indexed documents have this flag, the entire index is continuous.
    If any documents do not have this flag, only documents which pre-date them can be considered continuous.

    In continuous mode, only continuous documents are provided by the Source API.
    Similarly, Destination API attempts to read documents from the last continuous document, even if more up-to-date
    documents exist that are not continuous (even if they have the flag set!)

    Continuous mode has no effect on DirectLinkSource API.
    """
    def __init__(self, continuous: bool = True):
        self.__continuous = continuous

    def __enter__(self):
        self.__start_from = CustomDLC.latest_auto_time() if self.__continuous else None

    def read_all(self, start_from: int = 0) -> Iterator[dict]:
        LOG.warning('Loading elastic index CDLCs from %s (%s).', loading_from(start_from), self.__describe_mode())

        s = CustomDLC.search()
        timestamp_range = {'gte': start_from}
        if self.__continuous:
            s = s.filter('term', from_auto_index=True).sort('snapshot_timestamp').params(preserve_order=True)
            timestamp_range['lte'] = self.start_from()

        if start_from:
            s = s.filter('range', snapshot_timestamp=timestamp_range)

        for hit in s.scan():
            cdlc = hit.to_dict()
            cdlc.pop('from_auto_index', None)
            if self.__continuous:
                cdlc[CONTINUOUS_FROM] = start_from or 0

            yield cdlc

    def to_direct_link(self, cdlc_id: Any) -> str:
        c = CustomDLC.get(cdlc_id, ignore=[404])
        return c.direct_download if c else None

    def start_from(self) -> int:
        return self.__start_from or 0

    def try_write(self, cdlc: dict) -> Any:
        continuous_from = cdlc.pop(CONTINUOUS_FROM, None)
        is_continuous = self.__continuous and continuous_from is not None and continuous_from <= self.start_from()

        cdlc_id = str(cdlc.get('id', None))
        c = CustomDLC(_id=cdlc_id, from_auto_index=is_continuous, **cdlc)
        c.save()
        LOG.warning('Indexed CDLC #%s.', cdlc_id)
        return None if c.direct_download else c

    def update(self, from_write: Any, direct_link: str):
        c = from_write
        if direct_link:
            c.update(direct_download=direct_link)
            LOG.warning('Indexed direct link for CDLC #%s.', c.id)

    def __describe_mode(self):
        return 'only continuous' if self.__continuous else 'both continuous and not'


class ElasticIndexUpdateOnly(Destination):
    """
    Special Destination implementation which only updates links. Useless for anything else, I suppose.
    """
    def try_write(self, cdlc: dict) -> Any:
        direct_link = cdlc.get('direct_download', None)
        return None if direct_link and not direct_link.isspace() else cdlc.get('id', None)

    def update(self, from_write: Any, direct_link: str):
        cdlc_id = from_write
        if cdlc_id and direct_link:
            CustomDLC(_id=str(cdlc_id)).update(direct_download=direct_link)
            LOG.warning('Indexed direct link for CDLC #%s.', cdlc_id)


class ElasticAbsolution(Destination):
    """
    Very special Destination which fixes the one time programming error I committed. See TheLoaderer#fix_sin_against_art
    """
    def try_write(self, cdlc: dict) -> Any:
        cdlc_id = str(cdlc.get('id', None))
        art = cdlc.get('art', '')
        try:
            CustomDLC(_id=cdlc_id).update(art=art)
        except NotFoundError as e:
            LOG.warning('Art update failed for CDLC #%s, probably because it has not been loaded yet.', cdlc_id)
            debug_ex(e, 'fix my sins', LOG, silent=True)

        return None

    def update(self, from_write: Any, direct_link: str):
        raise NotImplementedError('This method should never be called because try_write always returns None.')


class FileDump(Source, Destination):
    """
    File for CDLC dumping (or reading) as JSON.

    While it supports reading from arbitrary time, it is intended for dumping the state of a different source
    so that it can be used as a source itself, e.g. on another system.

    Preserves the continuity from the source as dumped.

    The file is overwritten during dumping, so be careful to not delete existing dumps, etc.
    """
    def __init__(self, file, start_from: int = 0):
        self.__file = file
        self.__start_from = start_from
        self.__contents = []

        self.__write_queue = Queue()
        self.__writer = Thread(target=self.__write_from_queue)
        self.__is_done = Event()
        self.__is_broken = Event()

        # the following variables are only accessed in the writer Thread or after join() on it
        self.__temp_dump = None
        self.__first_dump = True

    def __enter__(self):
        try:
            f = open(self.__file, 'rb')
        except Exception as e:
            debug_ex(e, f'read file <{self.__file}>', LOG, silent=True)
        else:
            with f:
                self.__contents = json.load(f)
                self.__contents.sort(key=lambda c: c.get('snapshot_timestamp', 0))

        self.__writer.start()

    def __exit__(self, *args):
        self.__is_done.set()
        self.__writer.join()

        if self.__is_broken.is_set():
            LOG.error('An error occurred while trying to write to temp file.')

        if self.__temp_dump:
            try:
                with self.__temp_dump:
                    self.__temp_dump.write(']')

                if not self.__is_broken.is_set():
                    shutil.copy(self.__temp_dump.name, self.__file)
                    LOG.warning('CDLC JSON dump file ready: %s.', self.__file)
            except Exception as e:
                LOG.error('Writing to file <%s> failed. Please check temp file if it still exists: %s',
                          self.__file, self.__temp_dump.name)
                return debug_ex(e, f'write from temp to file <{self.__file}>', LOG, silent=True)

            try:
                os.remove(self.__temp_dump.name)
            except Exception as e:
                debug_ex(e, f'clean up temp file {self.__temp_dump.name}', LOG, silent=True)

    def read_all(self, start_from: int = 0) -> Iterator[dict]:
        LOG.warning('Loading JSON file CDLCs from %s.', loading_from(start_from))
        yield from dropwhile(lambda c: c.get('snapshot_timestamp', 0) < start_from, self.__contents)

    def start_from(self) -> int:
        return self.__start_from

    def try_write(self, cdlc: dict) -> Any:
        direct_link = cdlc.get('direct_download', '')
        if direct_link and not direct_link.isspace():
            self.__write_queue.put(cdlc)
            return None

        return cdlc

    def update(self, from_write: Any, direct_link: str):
        cdlc = from_write
        cdlc['direct_download'] = direct_link
        self.__write_queue.put(cdlc)

    def __write_from_queue(self):
        while not self.__is_done.is_set() or not self.__write_queue.empty():
            try:
                cdlc = self.__write_queue.get(timeout=1)
            except Empty:
                continue

            try:
                f = self.__get_temp_file()
                if self.__first_dump:
                    self.__first_dump = False
                else:
                    f.write(',')

                f.write(json.dumps(cdlc, indent=4))
            except Exception as e:
                self.__is_broken.set()
                debug_ex(e, 'write to temp file', LOG)
                break

    def __get_temp_file(self) -> IO:
        if not self.__temp_dump:
            self.__temp_dump = NamedTemporaryFile(mode='w', prefix=f'{self.__file}_', suffix='.json', delete=False)
            self.__temp_dump.write('[')

        return self.__temp_dump


class TheLoaderer:
    def __init__(self,
                 cf: CustomsForgeClient = None,
                 max_threads: int = DEFAULT_MAX_THREADS):
        self.__cf_source = Customsforge(cf) if cf else None
        self.__es_index = ElasticIndex()
        self.__max_threads = max_threads if max_threads and max_threads > 0 else DEFAULT_MAX_THREADS

    def fix_sin_against_art(self):
        """
        Fixes a programming error I made. Instead of loading each CDLC's art link, I loaded a constant...
        """
        self.load(self.__cf_source, ElasticAbsolution())

    def load_links(self, links=None):
        """
        Loads all missing links to ElasticIndex.

        This is NOT an efficient, but accurate process. It's relatively hard to make a query for missing
        or empty fields, and I'm not sure if it's possible to query whitespace only fields. This call
        loads all the data from the index & checks for missing links programmatically. If needed, it can
        be updated at any time, but with 8 years worth of CDLCs it finishes in seconds (not counting time
        spent retrieving links), so it should be fine.

        :param links: DirectLinkSource implementation or an object that can be resolved to one

        Resolution logic is the same as in TheLoaderer#load, with one exception: src is never used as
        stand-in for links, as it is assumed ElasticIndex does not have the ones we need.
        """
        self.load(ElasticIndex(continuous=False), ElasticIndexUpdateOnly(), links or self.__cf_source)

    def load(self, src=None, dest=None, links=None):
        """
        Loads CDLCs from a source to a destination.

        :param src: Source implementation or an object that can be resolved to one
        :param dest: Destination implementation or an object that can be resolved to one
        :param links: DirectLinkSource implementation or an object that can be resolved to one

        Resolution logic:
        1) If it's any falsy object, use default
        2) If it's CustomsForgeClient, use Customsforge
        3) If it's an Elasticsearch, use ElasticIndex
        4) If it's a case-insensitive 'cf' or 'customsforge', use Customsforge
        5) If it's a case-insensitive 'es', 'elastic', 'elasticsearch', 'index' or 'elasticindex', use ElasticIndex
        6) If it's any other string or path, use FileDump

        In all cases the resolved instance uses default settings (ElasticIndex in continuous mode, FileDump from 0).
        Defaults:
        src: Customsforge
        dest: ElasticIndex
        links: src if it implements DirectLinkSource, otherwise Customsforge
        """
        src = self.__coerce_source(src)
        dest = self.__coerce_destination(dest)
        links = self.__coerce_links(src, links)

        if src and dest and links:
            work_queue = []

            with src, dest, ThreadPoolExecutor(self.__max_threads) as p:
                for cdlc in src.read_all(dest.start_from()):
                    c = dest.try_write(cdlc)
                    if c is not None:
                        work = p.submit(self.__update, links, cdlc.get('id', None), dest, c)
                        work_queue.append(work)

                for item in work_queue:
                    item.result()

    def __update(self, links: DirectLinkSource, c_id, dest: Destination, c):
        direct_link = links.to_direct_link(c_id) if c_id else ''
        dest.update(c, direct_link)

    def __coerce_source(self, src) -> Source:
        src = self.__coerce(src, self.__cf_source)
        if isinstance(src, Source):
            return src

        return LOG.error('Could not be coerce Source: %s', src)

    def __coerce_destination(self, dest) -> Destination:
        dest = self.__coerce(dest, self.__es_index)
        if isinstance(dest, Destination):
            return dest

        return LOG.error('Could not be coerce Destination: %s', dest)

    def __coerce_links(self, src, links) -> DirectLinkSource:
        links = self.__coerce(links, src if isinstance(src, DirectLinkSource) else self.__cf_source)
        if isinstance(links, DirectLinkSource):
            return links

        return LOG.error('Could not be coerce DirectLinkSource: %s', links)

    def __coerce(self, o, fallback):
        if not o:
            return fallback

        if isinstance(o, CustomsForgeClient):
            return Customsforge(o)

        if isinstance(o, Elasticsearch):
            return self.__es_index

        if isinstance(o, str):
            if o.lower() in CUSTOMSFORGE_STR:
                return self.__cf_source

            if o.lower() in ELASTIC_STR:
                return self.__es_index

            return FileDump(o)

        if isinstance(o, Path):
            return FileDump(o)

        return o


def loading_from(start: int):
    return datetime.fromtimestamp(start, tz=timezone.utc) if start and start > 0 else 'beginning'
