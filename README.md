
# Sahyun bot

This is the implementation of the bot used in Sahyun's twitch channel:
https://www.twitch.tv/sahyun

## Usage examples

TODO

## Permissions

CustomsForge does not allow bots to access their API, unless given explicit permission.
This bot's use of CustomsForge API has been officially approved with the condition that the
source code is made public on Github.

If you want to access their API using this bot (or build your own), please contact them and ask:
http://customsforge.com/page/support.html

## Command reference

TODO

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

To launch the bot, use 'run.bat'. To play around with the library instead, use 'repl.bat'.
The latter should configure all relevant objects, but not actually launch the bot itself.
Both files assume 'install.bat' was already called before.

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

Explain = true if you want elasticsearch to explain itself, false otherwise; defaults to false;
explanations will only be visible in DEBUG level, in the JSON responses themselves

#### [system]

HttpDebugMode = true if you want to print http headers and stuff; defaults to false

LoggingConfigFilename = filename which contains logging configuration; defaults to 'config_log_default.ini';
if the defaults are not suitable for you, consider using 'config_log.ini' which is ignored by git
