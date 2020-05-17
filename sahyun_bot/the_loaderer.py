import logging
from datetime import datetime, timedelta

from sahyun_bot.customsforge import CustomsForgeClient
from sahyun_bot.elastic import last_auto_index_time, CustomDLC

LOG = logging.getLogger('theload')


def load(cf: CustomsForgeClient):
    load_from = last_auto_index_time() or 0
    load_from_date = datetime.fromtimestamp(load_from).date() - timedelta(days=1)
    for cdlc in cf.cdlcs(since=load_from_date, since_exact=load_from):
        c = CustomDLC(**cdlc)
        LOG.info('Loading CDLC #%s: %s (by %s)', c.id, c.full_title, c.author)

        c.from_auto_index = True
        c.direct_download = cf.direct_link(c.id)
        c.save()
