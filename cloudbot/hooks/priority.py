from enum import unique, IntEnum


@unique
class Priority(IntEnum):
    # Reversed to maintain compatibility with sieve hooks numeric priority
    LOWEST = 127
    LOW = 63
    NORMAL = 0
    HIGH = -64
    HIGHEST = -128
