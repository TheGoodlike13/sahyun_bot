from httmock import all_requests

from sahyun_bot.customsforge import MAIN_PAGE, LOGIN_PAGE
from tests.mock_settings import *


@all_requests
def server_down(url, request):
    raise Exception('Failure as expected')


@all_requests
def customsforge(url, request):
    if 'index.php' in url.path:
        return login_mock(url, request)

    if not request.headers.get('Cookie', '') == MOCK_COOKIE:
        return to_login_page()

    if 'get_content' in url.path:
        return dates_mock(url, request)

    if 'get_group_content' in url.path:
        return cdlcs_mock(url, request)

    if 'process.php' in url.path:
        return direct_link_mock(url, request)

    return {
        'status_code': 404,
        'content': 'Unexpected URL',
    }


def login_mock(url, request):
    if all(param in request.body.split('&') for param in VALID_LOGIN_FORM):
        return to_main_page()

    return {
        'status_code': 200,
        'content': 'Sign-in error page',
    }


def dates_mock(url, request):
    before, skip, after = url.query.partition('skip=')
    if after:
        date_str = '2020-05-1' + after[:1]
        if date_str in MOCK_CDLC:
            return group(date_str)

    return values()


def group(date_str: str):
    return values([
        [{'grp': date_str}],
        [{'total': len(MOCK_CDLC)}]
    ])


def cdlcs_mock(url, request):
    if 'skip=0' in url.query:
        for date_str, cdlc in MOCK_CDLC.items():
            if date_str in url.query:
                return values([cdlc])

    return values('[]')


def direct_link_mock(url, request):
    for date_str, cdlc in MOCK_CDLC.items():
        id_param = 'id={}'.format(cdlc.get('id'))
        if id_param in url.query:
            return to_direct_link('magical_link')

    return to_direct_link()


def values(content=None):
    return {
        'status_code': 200,
        'content': content,
    }


def to_main_page():
    return {
        'status_code': 302,
        'content': 'Redirect to main page - login successful!',
        'headers': {
            'Set-Cookie': MOCK_SET_COOKIE,
            'Location': MAIN_PAGE,
        },
    }


def to_login_page():
    return {
        'status_code': 302,
        'content': 'Redirect to login page - login is required!',
        'headers': {
            'Location': LOGIN_PAGE,
        },
    }


def to_direct_link(link: str = ''):
    return {
        'status_code': 302,
        'content': 'Redirect to direct link - if one exists, that is!',
        'headers': {
            'Location': link,
        },
    }
