from sahyun_bot.utils import read_config, NON_EXISTENT, nuke_from_orbit

DEFAULT_HOST = 'localhost'
DEFAULT_CUSTOMSFORGE_INDEX = 'cdlcs'

TEST_CUSTOMSFORGE_INDEX = DEFAULT_CUSTOMSFORGE_INDEX + '_test'
TEST_VALUES = frozenset([
    TEST_CUSTOMSFORGE_INDEX,
])

e_host = NON_EXISTENT
e_cf_index = NON_EXISTENT


def ready_or_die():
    """
    Immediately shuts down the application if the module is not properly configured.
    Make the call immediately after imports in every module that depends on this configuration to be loaded.
    """
    if NON_EXISTENT in [e_host, e_cf_index]:
        nuke_from_orbit('programming error - elastic module imported before elastic_settings is ready!')


def init():
    global e_host
    global e_cf_index

    e_host = read_config('elastic', 'Host', fallback=DEFAULT_HOST)
    e_cf_index = read_config('elastic', 'CustomsforgeIndex', fallback=DEFAULT_CUSTOMSFORGE_INDEX)

    for config in [e_host, e_cf_index]:
        if config in TEST_VALUES:
            nuke_from_orbit('configuration error - cannot use TEST values for REAL initialization')


def init_test():
    global e_host
    global e_cf_index

    e_host = DEFAULT_HOST
    e_cf_index = TEST_CUSTOMSFORGE_INDEX
