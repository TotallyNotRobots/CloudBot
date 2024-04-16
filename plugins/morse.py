import unidecode

from cloudbot import hook

# Stolen from https://www.geeksforgeeks.org/morse-code-translator-python/

# Dictionary representing the morse code chart
MORSE_CODE_DICT = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    ", ": "--..--",
    ".": ".-.-.-",
    "?": "..--..",
    "/": "-..-.",
    "-": "-....-",
    "(": "-.--.",
    ")": "-.--.-",
}


class CharacterNotFount(Exception):
    def __init__(self, char):
        self.char = char


# Function to encrypt the string
# according to the morse code chart


def text2morse(message):

    message = unidecode.unidecode(message.upper()).upper()
    cipher = ""
    for letter in message:
        if letter != " ":
            try:
                cipher += MORSE_CODE_DICT[letter] + " "
            except KeyError:
                raise CharacterNotFount(letter)
        else:
            cipher += " "

    return cipher


# Function to decrypt the string
# from morse to english


def morse2text(message):

    # extra space added at the end to access the
    # last morse code
    message += " "
    decipher = ""
    citext = ""
    for letter in message:
        if letter != " ":
            i = 0
            citext += letter
        else:
            i += 1
            if i == 2:
                decipher += " "
            else:
                try:
                    decipher += list(MORSE_CODE_DICT.keys())[
                        list(MORSE_CODE_DICT.values()).index(citext)
                    ]
                except (KeyError, ValueError):
                    raise CharacterNotFount(letter)
                citext = ""

    return decipher


@hook.command("morse", "morsecode")
def morse(text):
    """<text> - Converts text to morse code."""
    try:
        return text2morse(text)
    except CharacterNotFount as e:
        return f"Error: Character not decodable {e.char}"


@hook.command("morsetrans")
def morse2(text):
    """<text> - Converts morse code to text."""
    try:
        return morse2text(text)
    except CharacterNotFount as e:
        return f"Error: Character not decodable {e.char}"


if __name__ == "__main__":
    print(morse2text(".... . -.--   .--- ..- -.. ."))
    print(text2morse("HELLO WORLD"))
