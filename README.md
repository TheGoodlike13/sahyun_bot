
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
directory. 

To make it easier to configure, 'empty_config.ini' file is provided which should have all possible
expected values as empty. Here are all expected values with corresponding sections & explanations:

#### [customsforge]

ApiKey = key used in login form of customsforge.com

Username = username for an account in customsforge.com

Password = password for an account in customsforge.com;
while unlikely, it is possible the password will be sent over plaintext, so change it to something
completely random or anything else you wouldn't mind exposed

BatchSize = amount of values returned per request; defaults to 100

#### [system]

HttpDebugMode = true if you want to print http headers and stuff; defaults to false
