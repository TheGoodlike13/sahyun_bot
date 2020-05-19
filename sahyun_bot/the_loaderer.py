import json
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Iterator

from elasticsearch_dsl.connections import get_connection

from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic import CustomDLC
from sahyun_bot.utils_logging import get_logger

BACKGROUND_WORKERS = ThreadPoolExecutor(6)


LOG = get_logger(__name__)


def load(cf: CustomsForgeClient):
    work_queue = []

    load_from = CustomDLC.latest_auto_time() or 0
    load_from_date = datetime.fromtimestamp(load_from).date() - timedelta(days=1)
    for cdlc in cf.cdlcs(since=load_from_date, since_exact=load_from):
        c = CustomDLC(from_auto_index=True, **cdlc)
        c.save()
        work = BACKGROUND_WORKERS.submit(_load_direct_link, cf, c)
        work_queue.append(work)

    for work in work_queue:
        work.result()


def load_links(cf: CustomsForgeClient):
    work_queue = []

    for c in CustomDLC.search().exclude('exists', field='direct_download').scan():
        work = BACKGROUND_WORKERS.submit(_load_direct_link, cf, c)
        work_queue.append(work)

    for c in CustomDLC.search().params(q='direct_download.keyword:""').scan():
        work = BACKGROUND_WORKERS.submit(_load_direct_link, cf, c)
        work_queue.append(work)

    for work in work_queue:
        work.result()


def _load_direct_link(cf: CustomsForgeClient, c: CustomDLC):
    LOG.debug('Updating link for CDLC #%s', c.id)
    direct_link = cf.direct_link(c.id)
    if direct_link:
        c.update(direct_download=direct_link)


def dump_all():
    with open('dump.json', 'w') as f:
        f.write('[')
        first = True
        for hit in CustomDLC.search().scan():
            if not first:
                f.write(',')

            d = hit.to_dict()
            if 'snapshot_timestamp' in d and isinstance(d['snapshot_timestamp'], datetime):
                d['snapshot_timestamp'] = int(d['snapshot_timestamp'].timestamp())

            if '_snapshot_time' in d:
                del d['_snapshot_time']

            if 'snapshot_time' in d:
                del d['snapshot_time']

            del d['first_index']
            del d['last_index']
            d['_id'] = str(d['id'])
            f.write(json.dumps(d, indent=4))
            first = False

        f.write(']')


def load_all():
    from elasticsearch.helpers import bulk
    bulk(get_connection(), get_all())


def get_all() -> Iterator[dict]:
    with open('dump.json', 'rb') as f:
        for c in json.load(f):
            yield CustomDLC(**c).to_dict(True)
