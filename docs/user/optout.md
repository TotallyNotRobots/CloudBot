# Hook OptOuts

- The `core.optout` plugin allows channels to enable/disable specific hooks matching a pattern.
- Both the channel and hook parameters accept glob patterns.
- OptOut checks are done in order from the most specific patterns to the most broad.

### Disabling a hook
`optout plugin.command_func disable`

### Enabling a globally disabled hook
`optout plugin.command_func enable`

### Globally disabling a hook
`optout #* plugin.command_func disable`

## Examples
#### Disabling all attack commands in a channel
`optout attacks.* disable`

#### Allowing `attacks.compliment` while still not allowing other attacks
`optout attacks.* disable`

`optout attacks.compliment enable`

#### Globally disable the quote command
`optout #* quote.quote disable`
