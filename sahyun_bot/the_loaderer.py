import logging
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta

from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic import last_auto_index_time, CustomDLC

BACKGROUND_WORKERS = ThreadPoolExecutor(6)


LOG = logging.getLogger(__name__.rpartition('.')[2].replace('_', ''))


def load(cf: CustomsForgeClient):
    work_queue = []

    load_from = last_auto_index_time() or 0
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
