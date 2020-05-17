import pytest
from elasticsearch_dsl import connections

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import Parse
from sahyun_bot.utils import debug_ex
from tests.reusable import *

elastic_settings.init_test()


# in most cases the server is either up or down for all tests; if it's down at the start, let's just assume it's down
@pytest.fixture(scope='session')
def working_test_elastic_client():
    elastic_search = connections.create_connection(hosts=[elastic_settings.e_host])

    from sahyun_bot import elastic
    if elastic.purge_elastic():
        yield elastic_search
    else:
        pytest.skip('Cannot perform elastic tests! Please launch & configure an elasticsearch instance.')


# it is assumed that each test module will be fine with any changes from other tests; in future scope may become dynamic
@pytest.fixture(scope='module')
def es_client(working_test_elastic_client):
    from sahyun_bot import elastic
    try:
        # if test server crashes half way, but comes back up quick, the next test should clean up before moving forward
        if elastic.purge_elastic() and elastic.setup_elastic() and prepare_index():
            yield working_test_elastic_client
        else:
            pytest.skip('Elasticsearch test server is down or incorrectly configured.')
    finally:
        elastic.purge_elastic()


def prepare_index() -> bool:
    from sahyun_bot.elastic import CustomDLC
    try:
        CustomDLC(**Parse.cdlc(CDLC_JSON_1)).save()
        CustomDLC(**Parse.cdlc(CDLC_JSON_2)).save()
        CustomDLC(**Parse.cdlc(CDLC_JSON_3)).save()

        return True
    except Exception as e:
        return debug_ex(e, 'prepare elasticsearch index for testing')
