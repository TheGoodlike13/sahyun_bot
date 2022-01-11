import json
import os
from pathlib import Path

import pytest
from elasticsearch.helpers import bulk
from elasticsearch_dsl import connections

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import To, CustomsforgeClient
from sahyun_bot.twitchy import Twitchy
from sahyun_bot.users_settings import UserRank
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_queue import MemoryQueue
from sahyun_bot.utils_settings import read_config, config
from tests.mock_irc import ResponseMock
from tests.mock_settings import *

elastic_settings.init_test()

MANUAL_USERS = {
    '92152420': UserRank.BAN,  # sahyunbot
    '37103864': UserRank.ADMIN,  # thegoodlike13
}


@pytest.fixture(scope='session', autouse=True)
def prepare_cdlc_data():
    data_dir = Path(os.path.realpath(__file__)).parent / 'data'
    for p in data_dir.glob('cdlc_*.json'):
        with p.open() as f:
            MOCK_CDLC.append(json.load(f))


@pytest.fixture(scope='session')
def twitchy():
    # we use the real twitch API in our tests, which should give great guarantees for it working
    config.read('config.ini')
    client_id = read_config('twitch', 'ClientId')
    client_secret = read_config('twitch', 'Secret')
    if not client_id or not client_secret:
        pytest.skip('Cannot perform twitch tests! Please include twitch client id & secret in config.ini file.')

    api = Twitchy(client_id, client_secret)
    yield api
    api.close()


@pytest.fixture(scope='session')
def es():
    from sahyun_bot.utils_elastic import purge_elastic, setup_elastic

    elastic_search = connections.create_connection(hosts=[elastic_settings.e_host])
    if not purge_elastic() or not setup_elastic():
        pytest.skip('Cannot perform elastic tests! Please launch & configure an elasticsearch instance.')

    yield elastic_search
    purge_elastic()


@pytest.fixture
def es_cdlc(es):
    from sahyun_bot.elastic import CustomDLC
    prepare_doc(es, CustomDLC)
    return es


@pytest.fixture
def es_rank(es):
    from sahyun_bot.elastic import ManualUserRank
    prepare_doc(es, ManualUserRank)
    return es


def prepare_doc(es, doc):
    try:
        bulk(es, (d.to_dict(True) for d in prepare_index(doc)), refresh=True)
    except Exception as e:
        debug_ex(e, 'prepare elasticsearch index for testing')
        pytest.skip('Elasticsearch setup failed. See logs for exception.')


def prepare_index(doc):
    from sahyun_bot.elastic import CustomDLC, ManualUserRank

    if doc is CustomDLC:
        return prepare_cdlcs(doc)

    if doc is ManualUserRank:
        return prepare_users(doc)

    pytest.skip(f'Programming error - unknown document: {doc.__name__}')


def prepare_cdlcs(doc):
    for cdlc in MOCK_CDLC:
        c = To.cdlc(cdlc)
        c['from_auto_index'] = False
        yield doc(_id=cdlc['id'], **c)


def prepare_users(doc):
    for twitch_id, rank in MANUAL_USERS.items():
        yield doc(_id=twitch_id).set_rank_no_op(rank)


@pytest.fixture
def tl(cf, es_cdlc):
    from sahyun_bot.the_loaderer import TheLoaderer
    return TheLoaderer(cf, use_elastic=True)


@pytest.fixture
def users(twitchy, es_rank):
    from sahyun_bot.users import Users
    return Users(streamer='sahyun', tw=twitchy, use_elastic=True)


@pytest.fixture
def live_users(twitchy):
    from sahyun_bot.users import Users
    return Users(streamer='sahyun', tw=twitchy)


@pytest.fixture
def commander(users, twitchy):
    from sahyun_bot.commander import TheCommander
    from sahyun_bot.down import Downtime
    downtime = {
        'fail': '3600',
        'time': '30',
        'testfollow': '30:1',
    }
    return TheCommander(us=users, tw=twitchy, dt=Downtime(config=downtime))


@pytest.fixture
def cf():
    return CustomsforgeClient(batch_size=1,
                              email=MOCK_EMAIL,
                              password=MOCK_PASS,
                              cookie_jar_file=None,
                              get_today=lambda: TEST_DATE)


@pytest.fixture
def queue():
    return MemoryQueue()


@pytest.fixture
def rq(es_cdlc):
    return MemoryQueue()


@pytest.fixture
def hook():
    return ResponseMock()
