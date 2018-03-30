## Changelog

### 2.0
* Remove directory changing on bot load
* Remove old docs
* Add virtualenv folder to gitignore
* Move logging init to `__main__`
* Clean up logger init
* Update README with new information
* Remove outdated web interface support
* Clean up directory settings on bot object
* Refactor `Client` construction
* Restructure client modules
* Recreate the `SSLContext` on each reconnect
* Refactor permissions and add global reload methods
* Switch to using `Config` class in `setup_logger()`
* Add more client specific checks
* Refactor dynamic function launches
* Fix exit message on invalid version
* Remove the ability to save the config back to disk
* Rename logger setup function
* Add custom permissions manager for `IrcClient`
* Make all IRC specific hooks only run on IRC clients
* Fix stop and restart commands
* Refactor `admin_bot`
* Replace channel checks with client implementations
* Refactor `admin_channel`
* Use correct method to send nick on start
* Clean up IRC specific code
* Remove old `keep_alive` logic
* Clean up bucket logic
* Split up main sieve
* Add None check to `regex_chans`
* More core plugins to `core/` folder


### 1.0.9
TBA

### 1.0.8
This update is pretty big. Be warned.
 * Improved flip command.
 * Added new time command that gets time for location.
 * Added locate command that locates a place on Google Maps.
 * Change weather command to use new location API from the two above.
 * Added more kill messages.
 * Revamp lastfm with more commands and better memory.
 * Add new poll command. Still not perfect.
 * Replaced old dictionary plugin with new Wordnik plugin.
 * Revamped Soundcloud command.
 * Revamped chatbot command.
 * Switched back to google search.
 * Added new issafe plugin.
 * And a whole lot of minor tweaks and fixes.

### 1.0.7.1
 * Security fixes.

### 1.0.7
 * Added new "Would you rather" plugin.

### 1.0.6
 * Added pig latin translator, requires new *nltk* module
 * Added reminder command
 * Added new periodic hook (does not support reloading properly yet, so use with caution)
 * Added priority sorting to sieve hooks
 * Started work on new documentation for 1.1
 * Did some minor internal refactoring

**1.0.5** - Fix geoip for queries with no region, fix youtube bug, add flip command

**1.0.4** - Adjust ratelimiter cleanup task, add octopart API key, fix brainfuck, sort mcstatus output.

**1.0.3** - More minor changes to plugins, fixed rate-limiting properly, banished SCP to CloudBotIRC/Plugins, added wildcard support to permissions (note: don't use this yet, it's still not entirely finalized!)

**1.0.2** - Minor internal changes and fixes, banished minecraft_bukget and worldofwarcraft to CloudBotIRC/Plugins

**1.0.1** - Fix history.py tracking

**1.0.0** - Initial stable release
