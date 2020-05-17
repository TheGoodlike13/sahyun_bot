import pytest
from elasticsearch import ElasticsearchException
from elasticsearch_dsl import connections

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import Parse
from sahyun_bot.utils import debug_ex
from tests.reusable import *

elastic_settings.init_test()


@pytest.fixture(scope='session')
def init_elastic():
    elastic_mock = connections.create_connection(hosts=[elastic_settings.e_host])

    from sahyun_bot import elastic
    try:
        # in case the tests were interrupted before we could clean up, we do so now
        elastic.purge_elastic()

        if elastic.setup_elastic() and prepare_index():
            yield elastic_mock
        else:
            pytest.skip('Cannot perform elastic tests! Please launch & configure an elasticsearch instance.')
    finally:
        elastic.purge_elastic()


def prepare_index() -> bool:
    from sahyun_bot.elastic import CustomDLC
    try:
        CustomDLC(**Parse.cdlc(CDLC_JSON_1)).save()
        CustomDLC(**Parse.cdlc(CDLC_JSON_2)).save()
        CustomDLC(**Parse.cdlc(CDLC_JSON_3)).save()
    except ElasticsearchException as e:
        return debug_ex(e, 'prepare elasticsearch index for testing')

    return True
