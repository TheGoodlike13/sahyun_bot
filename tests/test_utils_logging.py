import pytest
import requests
from assertpy import assert_that
from httmock import all_requests, HTTMock

from sahyun_bot.utils_logging import HttpDump


@pytest.fixture
def small():
    with HTTMock(simple):
        return requests.post('http://localhost/small',
                             params={'secret': 'value'},
                             data={'password': 'secret'},
                             headers={'request_header': 'out'})


@pytest.fixture
def big():
    with HTTMock(simple):
        return requests.post('http://localhost/big',
                             data={'password': 'secret'},
                             headers={'request_header': 'out'})


def test_basic_info(small, big):
    dump = HttpDump(max_dump=1)
    assert_that(dump.to_basic_info(small)).contains(
        'Basic HTTP call info:',
        '> POST http://localhost/small?secret=value',
        '< 200 OK (took ~0:00:00s)'
    )
    assert_that(dump.to_basic_info(big)).contains(
        'Basic HTTP call info:',
        '> POST http://localhost/big',
        '< 200 OK (took ~0:00:00s)'
    )


def test_detailed_info(small, big):
    dump = HttpDump(max_dump=1)
    assert_that(dump.to_detailed_info(small)).contains(
        'Detailed HTTP call info:',
        '> POST http://localhost/small?secret=value',
        '> request_header: out',
        '> Content-Length: 15',
        '> Content-Type: application/x-www-form-urlencoded',
        'password=secret',
        '~ 0:00:00s elapsed',
        '< 200 OK',
        '< response_header: in',
        '1',
    )
    assert_that(dump.to_detailed_info(big)).contains(
        'Detailed HTTP call info:',
        '> POST http://localhost/big',
        '> request_header: out',
        '> Content-Length: 15',
        '> Content-Type: application/x-www-form-urlencoded',
        'password=secret',
        '~ 0:00:00s elapsed',
        '< 200 OK',
        '< response_header: in',
        '< RESPONSE BODY TOO LARGE (11 bytes) >',
    )


def test_redacted(small):
    dump = HttpDump(unsafe=['password'])
    assert_that(dump.to_detailed_info(small))\
        .does_not_contain('password=secret')\
        .contains('password=REDACTED')


def test_redacted_query(small):
    dump = HttpDump(unsafe=['secret'])
    assert_that(dump.to_basic_info(small))\
        .does_not_contain('> POST http://localhost/small?secret=value')\
        .contains('> POST http://localhost/small?secret=REDACTED')
    assert_that(dump.to_detailed_info(small))\
        .does_not_contain('> POST http://localhost/small?secret=value')\
        .contains('> POST http://localhost/small?secret=REDACTED')


@all_requests
def simple(url, request):
    return {
        'status_code': 200,
        'reason': 'OK',
        'content': 'More than 1' if 'big' in url.path else '1',
        'headers': {
            'response_header': 'in',
        },
    }
