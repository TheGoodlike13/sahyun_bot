"""
Loads CDLC data from one format to another while preserving continuity.

Continuity in this context simply means that CDLC data is read or written in an orderly fashion. This order
is defined by 'snapshot_timestamp', i.e. the last time the CDLC data was updated. As long as the data is
processed in this order, we can be sure we have all the data up to some timestamp, and resume from there.

This module provides implementations for the purposes of this application, but any implementation of Source or
Destination are OK, as long as they adhere to the requirements for continuity.
It is assumed that the CDLC data inside these is authentic.

Loading CDLC data manually or through implementations that do not adhere to the contract can ruin the integrity
of the underlying data by breaking assumptions. For that reason, avoid using bootleg implementations or forged files.
"""
import json
import os
import shutil
from abc import ABC
from datetime import datetime, timezone, date
from itertools import dropwhile
from pathlib import Path
from queue import Queue, Empty
from tempfile import NamedTemporaryFile
from threading import Thread, Event
from typing import Iterator, Any, IO, List

from elasticsearch import Elasticsearch
from tldextract import extract

from sahyun_bot.customsforge import CustomsforgeClient, EONS_AGO
from sahyun_bot.elastic import CustomDLC
from sahyun_bot.utils import debug_ex, Closeable, T
from sahyun_bot.utils_elastic import ElasticAware
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


class Source(Closeable, ABC):
    def read_all(self, since: date = EONS_AGO) -> Iterator[dict]:
        """
        Generates all CDLCs since given time of update (or beginning, if not given).
        Time is given in epoch seconds.

        If the generated CDLCs are continuous, they should be sorted by time of update, ascending.
        They should also include {'continuous_from': start_from} in the returned dict.
        """
        raise NotImplementedError


class Destination(Closeable, ABC):
    def start_from(self) -> date:
        """
        To avoid loading continuous sources from beginning, this value is used as optimization.
        :returns date which should be passed into Source#read_all; EONS_AGO means from beginning
        """
        return EONS_AGO

    def try_write(self, cdlc: dict):
        """
        Try to write the given CDLC data into the destination.
        The actual write can be deferred until the Destination object is closed if needed.
        However, if the write is NOT deferred, it should not destroy the integrity or continuity of this destination.
        """
        raise NotImplementedError


class Customsforge(Source):
    """
    The prime source for CDLC data. Always continuous.
    """
    def __init__(self, cf: CustomsforgeClient):
        self.__cf = cf

    def read_all(self, since: date = EONS_AGO) -> Iterator[dict]:
        LOG.warning('Loading Customsforge CDLCs from %s.', since)

        for cdlc in self.__cf.cdlcs(since=since):
            cdlc[CONTINUOUS_FROM] = since
            yield cdlc


class ElasticIndex(Source, Destination):
    """
    Represents CDLC data in the application.

    To preserve continuity, a flag is used during indexing.
    If all indexed documents have this flag, the entire index is continuous.
    If any documents do not have this flag, only documents which pre-date them can be considered continuous.

    In continuous mode, only continuous documents are provided by the Source API.
    Similarly, Destination API attempts to read documents from the last continuous document, even if more up-to-date
    documents exist that are not continuous (even if they have the flag set!)
    """
    def __init__(self, continuous: bool = True):
        self.__continuous = continuous

    def __enter__(self):
        self.__start_from = self.__latest_auto_date() if self.__continuous else None

    def read_all(self, since: date = EONS_AGO) -> Iterator[dict]:
        LOG.warning('Loading elastic index CDLCs from %s (%s).', date, self.__describe_mode())

        since_timestamp = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        timestamp_range = {'gte': since_timestamp} if since_timestamp else {}

        s = CustomDLC.search()
        if self.__continuous:
            s = s.filter('term', from_auto_index=True).sort('snapshot_timestamp').params(preserve_order=True)
            start_time = int(datetime.combine(self.start_from(), datetime.min.time(), tzinfo=timezone.utc).timestamp())
            timestamp_range['lte'] = start_time

        if timestamp_range:
            s = s.filter('range', snapshot_timestamp=timestamp_range)

        for hit in s.scan():
            cdlc = hit.to_dict()
            cdlc.pop('from_auto_index', None)
            if self.__continuous:
                cdlc[CONTINUOUS_FROM] = since

            yield cdlc

    def start_from(self) -> date:
        return self.__start_from or EONS_AGO

    def try_write(self, cdlc: dict):
        continuous_from = cdlc.pop(CONTINUOUS_FROM, None)
        is_continuous = self.__continuous and continuous_from is not None and continuous_from <= self.start_from()

        cdlc_id = cdlc.get('id', None)
        c = CustomDLC(_id=cdlc_id, from_auto_index=is_continuous, **cdlc)
        c.save()
        LOG.warning('Indexed CDLC #%s.', cdlc_id)

    def __latest_auto_date(self):
        timestamp = CustomDLC.latest_auto_time()
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).date() if timestamp else None

    def __describe_mode(self):
        return 'only continuous' if self.__continuous else 'both continuous and not'


class ElasticWeirdness(Destination):
    """
    Special Destination which prints CDLCs which have weird links to the user. Lookup is not performed, as it is
    intended as a review.
    """
    def try_write(self, cdlc: dict):
        direct_link = cdlc.get('direct_download', None)
        if direct_link and not direct_link.isspace():
            domain = extract(direct_link).registered_domain
            if not domain:
                cdlc_id = cdlc.get('id', None)
                LOG.warning('Could not determine the domain for CDLC #%s: <%s>', cdlc_id, direct_link)


class FileDump(Source, Destination):
    """
    File for CDLC dumping (or reading) as JSON.

    While it supports reading from arbitrary time, it is intended for dumping the state of a different source
    so that it can be used as a source itself, e.g. on another system.

    Preserves the continuity from the source as dumped.

    The file is overwritten during dumping, so be careful to not delete existing dumps, etc.
    """
    def __init__(self, file, start_from: date = EONS_AGO):
        self.__file = file
        self.__start_from = start_from
        self.__contents: List[dict] = []

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

    def close(self):
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

    def read_all(self, since: date = EONS_AGO) -> Iterator[dict]:
        LOG.warning('Loading JSON file CDLCs from %s.', since)
        since_timestamp = int(datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        yield from dropwhile(lambda c: c.get('snapshot_timestamp', 0) < since_timestamp, self.__contents)

    def start_from(self) -> date:
        return self.__start_from

    def try_write(self, cdlc: dict):
        direct_link = cdlc.get('direct_download', '')
        if direct_link and not direct_link.isspace():
            self.__write_queue.put(cdlc)

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


class TheLoaderer(ElasticAware):
    def __init__(self,
                 cf: CustomsforgeClient = None,
                 use_elastic: bool = False):
        super().__init__(use_elastic)

        self.__cf_source = Customsforge(cf) if cf else None

    def log_weird_links(self):
        """
        Logs all weird links in the elastic index to the user.
        """
        self.load(ElasticIndex(continuous=False), ElasticWeirdness())

    def load(self, src=None, dest=None) -> bool:
        """
        Loads CDLCs from a source to a destination.

        :param src: Source implementation or an object that can be resolved to one
        :param dest: Destination implementation or an object that can be resolved to one
        :returns true if loading was attempted, false if it failed before even starting

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

        In all cases, if src, dest or links is a known implementation that relies on elastic, they will not be used
        when elastic is disabled.
        """
        src = self.__coerce_source(src)
        dest = self.__coerce_destination(dest)

        if not src or not dest:
            return False

        with src, dest:
            for cdlc in src.read_all(dest.start_from()):
                dest.try_write(cdlc)

        return True

    def __coerce_source(self, src) -> Source:
        src = self.__coerce_and_check_elastic(src, self.__cf_source)
        if isinstance(src, Source):
            return src

        return LOG.error('Could not be coerce Source: %s', src)

    def __coerce_destination(self, dest) -> Destination:
        dest = self.__coerce_and_check_elastic(dest, ElasticIndex())
        if isinstance(dest, Destination):
            return dest

        return LOG.error('Could not be coerce Destination: %s', dest)

    def __coerce_and_check_elastic(self, o, fallback):
        o = self.__coerce(o, fallback)
        coerced_name = type(o).__name__
        if self.use_elastic or coerced_name[:7] != 'Elastic':
            return o

        return LOG.warning('Cannot use <%s> because elastic is disabled.', coerced_name)

    def __coerce(self, o, fallback: T) -> T:
        if not o:
            return fallback

        if isinstance(o, CustomsforgeClient):
            return Customsforge(o)

        if isinstance(o, Elasticsearch):
            return ElasticIndex()

        if isinstance(o, str):
            if o.lower() in CUSTOMSFORGE_STR:
                return self.__cf_source

            if o.lower() in ELASTIC_STR:
                return ElasticIndex()

            return FileDump(o)

        if isinstance(o, Path):
            return FileDump(o)

        return o
