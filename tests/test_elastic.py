import warnings

import pytest
from assertpy import assert_that
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch_dsl import connections

from sahyun_bot import elastic_settings
from sahyun_bot.customsforge import Parse
from sahyun_bot.utils import debug_ex
from tests.test_values import *


@pytest.fixture(scope='module')
def elastic_mock():
    elastic_settings.init_test()
    elastic_mock = connections.create_connection(hosts=[elastic_settings.e_host])

    from sahyun_bot import elastic
    yield elastic_mock if elastic.setup_elastic() and prepare_index() else None
    elastic.purge_elastic()


def test_search_cdlc(elastic_mock):
    from sahyun_bot.elastic import CustomDLC
    if ensure_testable(elastic_mock):
        assert_that(CustomDLC.get('1', ignore=404)).is_none()

        all_cdlcs = list(CustomDLC.search())
        assert_that(all_cdlcs).is_length(3)

        assert_that([cdlc.full_title for cdlc in all_cdlcs]).contains(
            'Porno Graffiti - Hitori No Yoru(Great Teacher Onizuka)',
            'Blur - Song 2',
            'Yellowcard - Hang You Up',
        )

        assert_that([cdlc.link for cdlc in all_cdlcs]).contains(
            'https://customsforge.com/process.php?id=3492',
            'direct_link',
            'https://customsforge.com/process.php?id=49410',
        )


def test_update_link(elastic_mock):
    from sahyun_bot.elastic import CustomDLC
    if ensure_testable(elastic_mock):
        CustomDLC.get('3492').update(direct_link='direct_link_for_3492')
        ensure_changes_visible()

        same_cdlc = list(CustomDLC.search().query('match', artist='Porno Graffiti'))
        assert_that(same_cdlc).is_length(1)
        assert_that(same_cdlc[0].link).is_equal_to('direct_link_for_3492')


def test_last_auto_index_time(elastic_mock):
    from sahyun_bot.elastic import CustomDLC, last_auto_index_time
    if ensure_testable(elastic_mock):
        assert_that(last_auto_index_time()).is_none()

        CustomDLC.get('8623').update(from_auto_index=True)
        ensure_changes_visible()
        assert_that(last_auto_index_time()).is_equal_to(1318910400)


def test_request(elastic_mock):
    from sahyun_bot.elastic import request
    if ensure_testable(elastic_mock):
        assert_that(request('definitely not here')).is_empty()
        assert_that([cdlc.full_title for cdlc in request("you're")]).is_length(1).contains(
            'Yellowcard - Hang You Up',
        )


def ensure_testable(elastic_mock: Elasticsearch) -> bool:
    if elastic_mock:
        return True

    warnings.warn('Cannot perform elastic tests! Please launch & configure an elasticsearch instance.')
    return False


def prepare_index():
    from sahyun_bot.elastic import CustomDLC
    try:
        CustomDLC(**Parse.cdlc(CDLC_JSON_1)).save()
        CustomDLC(direct_link='direct_link', **Parse.cdlc(CDLC_JSON_2)).save()
        CustomDLC(**Parse.cdlc(CDLC_JSON_3)).save()

        ensure_changes_visible()
    except ElasticsearchException as e:
        return debug_ex(e, 'prepare elasticsearch index for testing')

    return True


def ensure_changes_visible():
    from sahyun_bot.elastic import CustomDLC
    # noinspection PyProtectedMember
    CustomDLC._index.refresh()
