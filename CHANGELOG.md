# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Add Python 3.8 to testing matrix
- Add support for channel keys (#95)
### Changed
- Refactor tests to remove dependency on mock library
- Change link_announcer.py to only warn on connection errors
- Change user lookup logic in last.fm plugin
- Refactor minecraft_ping plugin for updated mcstatus library
### Fixed
- Fix matching exception in horoscope test
- Fix youtube.py ISO time parse
- Fix grammatical error in food sentence (beer)
- Update youtube plugin to use proper contentRating API
- Update mylife.py for website changes

## [1.3.0] 2020-03-17
### Added
- Added `do_sieve` keyword to hooks
- Add the factoid character in the listfacts output
### Changed
- Cleaned up the timeformat API and implementation (#32)
- Updated cryptocurrency to new CoinMarketCap API
### Fixed
- Disconnect active vs configured channel lists (#11)
- Fix reminder tests time based errors
- Handle empty results in YouTube API responses
- Fix .urban handling numbers in the query
- Fix the possible `-0` in weather data
- Fix random truncations of search result URLs
- Fix listfacts not listing some facts
- Fix wikipedia summary fetching
- Fix loading modules with dynamic objects at the module scope (#102)
### Removed
- Removed rottentomatoes plugin as the API has been removed
- Removed dig plugin as jsondns is gone

## [1.2.0] 2019-11-27
- Many undocumented changes

## [1.1.0]
- Undocumented changes

## [1.0.9]
- Remove webUI

## [1.0.8]
This update is pretty big. Be warned.
- Improved flip command.
- Added new time command that gets time for location.
- Added locate command that locates a place on Google Maps.
- Change weather command to use new location API from the two above.
- Added more kill messages.
- Revamp lastfm with more commands and better memory.
- Add new poll command. Still not perfect.
- Replaced old dictionary plugin with new Wordnik plugin.
- Revamped Soundcloud command.
- Revamped chatbot command.
- Switched back to google search.
- Added new issafe plugin.
- And a whole lot of minor tweaks and fixes.

## [1.0.7.1]
- Security fixes.

## [1.0.7]
- Added new "Would you rather" plugin.

## [1.0.6]
- Added pig latin translator, requires new *nltk* module
- Added reminder command
- Added new periodic hook (does not support reloading properly yet, so use with caution)
- Added priority sorting to sieve hooks
- Started work on new documentation for 1.1
- Did some minor internal refactoring

## [1.0.5]
- Fix geoip for queries with no region, fix youtube bug, add flip command

## [1.0.4]
- Adjust ratelimiter cleanup task, add octopart API key, fix brainfuck, sort mcstatus output.

## [1.0.3]
- More minor changes to plugins, fixed rate-limiting properly, banished SCP to CloudBotIRC/Plugins, added wildcard support to permissions (note: don't use this yet, it's still not entirely finalized!)

## [1.0.2]
- Minor internal changes and fixes, banished minecraft_bukget and worldofwarcraft to CloudBotIRC/Plugins

## [1.0.1]
- Fix history.py tracking

## [1.0.0]
- Initial stable release

[Unreleased]: https://github.com/TotallyNotRobots/CloudBot/compare/v1.3.0...HEAD
[1.2.0]: https://github.com/TotallyNotRobots/CloudBot/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/TotallyNotRobots/CloudBot/compare/1.1.0...v1.2.0
[1.1.0]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.9...1.1.0
[1.0.9]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.8...1.0.9
[1.0.8]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.7.1...1.0.8
[1.0.7.1]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.7...1.0.7.1
[1.0.7]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.6...1.0.7
[1.0.6]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.5...1.0.6
[1.0.5]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.4...1.0.5
[1.0.4]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.3...1.0.4
[1.0.3]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/TotallyNotRobots/CloudBot/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/TotallyNotRobots/CloudBot/releases/tag/1.0.0
