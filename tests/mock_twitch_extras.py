from httmock import urlmatch


@urlmatch(netloc=r'tmi\.twitch\.tv$')
def twitch_hosts(url, request):
    whatever, param, value = url.query.partition('target=')
    if '13144519' in value:
        return host('thegoodlike13')

    if '37103864' in value:
        return host()

    return {
        'status_code': 404,
        'reason': 'Not Found',
        'content': 'Unexpected URL',
    }


def host(*names):
    return {
        'status_code': 200,
        'reason': 'OK',
        'content': {
            'hosts': [{'host_login': name} for name in names]
        },
    }
