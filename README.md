
# Sahyun bot

This is the implementation of the bot used in Sahyun's twitch channel:
https://www.twitch.tv/sahyun

## Usage examples

TODO

## Permissions

Customsforge does not allow bots to access their API, unless given explicit permission.
This bot's use of Customsforge API has been officially approved with the condition that the
source code is made public on Github.

If you want to access their API using this bot (or build your own), please contact them and ask:
http://customsforge.com/page/support.html

## Command reference

Every command requires a specific rank from the user to be executed. Furthermore, higher ranks
may grant additional functionality. This reference will be divided into sections of user rank
which is required for the command, and any additional privileges to higher ranks will be explicitly
enumerated within the description of this command.

No commands are available for users with rank BAN.

### VWR (any viewer that is not a follower)

#### !time

Responds with current time in UTC.

### FLWR (follower)

### ADMIN (streamer & his buddies)

#### !lock

Stops the bot from executing any further commands unless the user is ADMIN.

#### !index

Tries to index CDLCs from customsforge into elasticsearch.

#### !rank RANK NICK

Sets manual rank to the user.

Any rank can be used as alias: !ban NICK, !admin NICK, etc.

## Notes on development & running

The purpose of this bot is to manage the playlist of user requests while Sahyun is streaming.
It may also perform some other trivial tasks alongside.

For the sake of exercise, the bot is written using Python 3.8+. It uses poetry as build & dependency 
management tool.

install.bat should contain all the relevant commands & instructions which were used when setting up
the application for development & running. All instructions assume windows, as anyone using linux is
probably savvy enough to take care of such things on their own. Furthermore, most of the work is
described in guides & documentation of python or its tools. In some cases, information from a reddit
post was used:
https://www.reddit.com/r/pycharm/comments/elga2z/using_pycharm_for_poetrybased_projects/

To launch the bot, use 'run.bat'. To play around with the modules instead, use 'repl.bat'.
The latter should configure all relevant objects, but not actually launch the bot itself.
Both files assume 'install.bat' was already called before.

### Where to start looking at the code?

I suggest starting at 'modules.py' in 'sahyun_bot' package. It contains most if not all singletons
of the application, as well as imports to their configuration.

This module exists to make it easy to try things out with 'repl.bat'. It is only referenced by
'main' functions of the application, so it can be considered a kind of a bean factory.

### Elasticsearch

For data storage, Elasticsearch is used. This is because we require somewhat advanced search
functionality. Since we already need to use it, it seems meaningless to use another data
storage solution, in particular because no advanced relation-like logic is expected.

As long as Elasticsearch is running and reachable, the bot will configure the required
indexes and mappings. You can control the specifics via configuration.

### Logging

Messages that should appear to the user will be logged under WARNING. Messages that provide basic
information that the user may not need will be logged under INFO. Messages that provide detailed
information will be logged under DEBUG.

The logger names are derived by eliminating all '_' from the module name. Also, any 'utils_X' module
shares its logger name with 'X' module for simplicity. This is done to ensure a shortened logger
name is viably represented in console (see logging configuration).

### Configuration

All configuration should be put into 'config.ini' file. This file should be in the working
directory. Use 'empty_config.ini' as an example to quick-start your configuration.

If a specific configuration is missing from the file entirely, or is set to a value incompatible
with expected type (e.g. integer 'a'), default value is used. Same applies for values exceeding
constraints, like -1 or 500 when allowed values are in [1..100].
In most cases empty value is also replaced with the default, HOWEVER, there are some exceptions.

To be certain, please refer to the list of expected values & explanations below. If no default
is specified, assume it defaults to None. Generally speaking, if any values without defaults
are not provided, the related module will not function, or have limited functionality.

#### [customsforge]

ApiKey = key used in login form of customsforge.com

Username = username for an account in customsforge.com

Password = password for an account in customsforge.com;
while unlikely, it is possible the password will be sent over plaintext, so change it to something
completely random or anything else you wouldn't mind exposed

BatchSize = amount of values returned per request; defaults to 100; allowed range: [1..100]

Timeout = amount of seconds before HTTP gives up and fails the request; defaults to 100;
any positive value is allowed; due to retry policy, this value can be effectively 3 times
larger; the website can be pretty laggy sometimes :)

CookieFilename = filename for cookie storage; defaults to '.cookie_jar'; speeds up login
process for subsequent launches of the bot; IF EMPTY - cookies are only stored in memory only;
to avoid clashing with tests, '.cookie_jar_test' is automatically replaced with default value

#### [twitch]

ClientId = client id for accessing twitch API

Secret = client secret for accessing twitch API

#### [users]

CacheFollows = amount of seconds to cache a live follower rank, defaults to 300;
any positive value is allowed

CacheViewers = amount of seconds to cache a live follower rank, defaults to 5;
any positive value is allowed

#### [elastic]

Host = host used by elasticsearch client; defaults to localhost; localhost is also used for tests

CustomsforgeIndex = name of index which will contain information about cdlcs; defaults to 'cdlcs';
if you set it to 'cdlcs_test', which is used by tests, the application will crash immediately

RequestFields = comma separated list of fields used when making requests; it has a general purpose
default value, but since it may change a lot in the future, I won't write it out explicitly; for
examples of what is possible, refer to the elastic.CustomDLC class & elasticsearch documentation
about passing fields into multi-match queries

RequestMatchCeiling = max amount of matches from a request; defaults to 3; any positive integer
is allowed

Explain = true if you want elasticsearch to explain itself; defaults to false;
explanations will only be visible in the JSON responses, usually DEBUG level logs

#### [load]

MaxWorkers = amount of background threads that assist with loading CDLCs; defaults to 8;
any positive integer is allowed

#### [irc]

Nick = bot username, account on twitch

Token = oauth token for the bot account; equivalent to password for IRC

Channel = channel to join automatically; this channel will be considered the ADMIN for this bot;
do not use '#', i.e. 'sahyun', not '#sahyun'

MaxWorkers = amount of background threads that performs commands; defaults to 8;
any positive integer is allowed

#### [system]

HttpDebugMode = true if you want to print http headers and stuff to console; defaults to false;
the default logging config should make this obsolete, unless you really wanna see a lot of stuff
in the console for some reason

LoggingConfigFilename = filename which contains logging configuration; defaults to 'config_log_default.ini';
if the defaults are not suitable for you, consider making 'config_log.ini' which is ignored by git

#### [downtime]

Leniency = amount of seconds of downtime that should be ignored; defaults to 1; all values less
than 1 become 1

Unlike the previous sections, this section is dynamic. Each key matches an alias of a command,
and the value is a special string which represents downtime for that command. Downtime only
applies to user roles that are limited (generally, less than VIP).
 
If a command has multiple aliases, and a configuration for multiple of them is provided,
only one of them will be used.
There is no guarantee which one, although the result should be deterministic, i.e.
unless you change the configuration, it will continue to work the same.

The expected format is either an integer, or two integers separated by a colon. All negative
integers will be treated as 0. 0 is equivalent to not providing the configuration.
If the format of downtime is not followed, that setting is simply ignored. Here are a few examples:

###### time = 30

Now !time can only be executed once every 30 seconds. This applies globally - everyone has to wait.
There is no way to grant more than one execution on global level.

###### request = 900:2

Now !request can only be executed twice every 15 minutes. This applies per-user - each user gets
two requests.

###### joke = :5

This is ignored because it does not follow the format.
