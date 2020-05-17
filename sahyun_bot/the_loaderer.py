from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta

from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic import last_auto_index_time, CustomDLC

MAIN_WORKER = ThreadPoolExecutor(1)
BACKGROUND_WORKERS = ThreadPoolExecutor(6)


def load(cf: CustomsForgeClient):
    return MAIN_WORKER.submit(lambda: _load(cf))


def _load(cf: CustomsForgeClient):
    work_queue = []

    load_from = last_auto_index_time() or 0
    load_from_date = datetime.fromtimestamp(load_from).date() - timedelta(days=1)
    for cdlc in cf.cdlcs(since=load_from_date, since_exact=load_from):
        c = CustomDLC(from_auto_index=True, **cdlc)
        c.save()
        work = BACKGROUND_WORKERS.submit(lambda: _load_direct_link(cf, c))
        work_queue.append(work)

    for work in work_queue:
        work.result()


def _load_direct_link(cf: CustomsForgeClient, cdlc: CustomDLC):
    cdlc.update(direct_download=cf.direct_link(cdlc.id))
