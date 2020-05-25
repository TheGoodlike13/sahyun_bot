import json
import os
from pathlib import Path

import pytest
from elasticsearch_dsl import connections

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import To, CustomsforgeClient
from sahyun_bot.utils import debug_ex
from tests.mock_irc import ResponseMock
from tests.mock_settings import *

elastic_settings.init_test()


@pytest.fixture(scope='session', autouse=True)
def prepare_cdlc_data():
    data_dir = Path(os.path.realpath(__file__)).parent / 'data'
    for p in data_dir.glob('cdlc_*.json'):
        date_str = p.name[5:-5]
        with p.open() as f:
            MOCK_CDLC[date_str] = json.load(f)


# in most cases the server is either up or down for all tests; if it's down at the start, let's just assume it's down
@pytest.fixture(scope='session')
def working_test_elastic_client():
    elastic_search = connections.create_connection(hosts=[elastic_settings.e_host])

    from sahyun_bot import utils_elastic
    if utils_elastic.purge_elastic():
        yield elastic_search
    else:
        pytest.skip('Cannot perform elastic tests! Please launch & configure an elasticsearch instance.')


# this fixture should be used in modules where changes are minimal and easy to track
@pytest.fixture(scope='module')
def es(working_test_elastic_client):
    yield from prepare_elastic(working_test_elastic_client)


# this fixture should be used when your test bricks values used by other tests
@pytest.fixture
def es_fresh(working_test_elastic_client):
    yield from prepare_elastic(working_test_elastic_client)


def prepare_elastic(working_test_elastic_client):
    from sahyun_bot import utils_elastic
    try:
        # if test server crashes half way, but comes back up quick, the next test should clean up before moving forward
        if utils_elastic.purge_elastic() and utils_elastic.setup_elastic() and prepare_index():
            yield working_test_elastic_client
        else:
            pytest.skip('Elasticsearch test server is down or incorrectly configured.')
    finally:
        utils_elastic.purge_elastic()


def prepare_index() -> bool:
    from sahyun_bot.elastic import CustomDLC
    try:
        for cdlc in MOCK_CDLC.values():
            cdlc_id = str(cdlc.get('id', None))
            CustomDLC(_id=cdlc_id, **To.cdlc(cdlc)).save(refresh=False)

        CustomDLC._index.refresh()
        return True
    except Exception as e:
        return debug_ex(e, 'prepare elasticsearch index for testing')


@pytest.fixture
def cf():
    return CustomsforgeClient(api_key=MOCK_API_KEY,
                              batch_size=1,
                              username=MOCK_USER,
                              password=MOCK_PASS,
                              cookie_jar_file=None,
                              get_today=lambda: TEST_DATE)


@pytest.fixture
def cf_off():
    return CustomsforgeClient(api_key=MOCK_API_KEY,
                              batch_size=1,
                              cookie_jar_file=None,
                              get_today=lambda: TEST_DATE)


@pytest.fixture
def hook():
    return ResponseMock()
