# Compute common hashes and base64
# Author: Matheus Fillipe
# Date: 08/07/2022

import binascii
from base64 import (
    b16decode,
    b16encode,
    b32decode,
    b32encode,
    b64decode,
    b64encode,
    b85decode,
    b85encode,
)
from hashlib import blake2b, blake2s, md5, sha1, sha224, sha256, sha384, sha512

from cloudbot import hook


def compute_hash(text: str, hash_func) -> str:
    """Computes a hash of the text using the given hash function."""
    return hash_func(text.encode("utf-8")).hexdigest()


def base_encode(text: str, base_func) -> str:
    """Encodes the text using the given base."""
    try:
        return base_func(text.encode("utf-8")).decode("utf-8")
    except binascii.Error as e:
        return f"Error: {e}"


# TODO convert this to a loop over a map and eval call on hook decorator like in wikis.py. Copilot wrote this all and im too lazy to fix this now


@hook.command("sha384")
def sha384_hash(text: str) -> str:
    """<text> - Computes the SHA384 hash of <text>."""
    return compute_hash(text, sha384)


@hook.command("sha512")
def sha512_hash(text: str) -> str:
    """<text> - Computes the SHA512 hash of <text>."""
    return compute_hash(text, sha512)


@hook.command(
    "sha256",
    "sha256sum",
    "sha256s",
    "sha256sums",
    "sha256sumss",
    "sha256sums",
    "sha256sumss",
)
def sha256sum(text):
    """<text> - Computes the SHA256 hash of <text>."""
    return "SHA256: " + compute_hash(text, sha256)


@hook.command(
    "sha224",
    "sha224sum",
    "sha224s",
    "sha224sums",
    "sha224sumss",
    "sha224sums",
    "sha224sumss",
)
def sha224sum(text):
    """<text> - Computes the SHA224 hash of <text>."""
    return "SHA224: " + compute_hash(text, sha224)


@hook.command(
    "sha1", "sha1sum", "sha1s", "sha1sums", "sha1sumss", "sha1sums", "sha1sumss"
)
def sha1sum(text):
    """<text> - Computes the SHA1 hash of <text>."""
    return "SHA1: " + compute_hash(text, sha1)


@hook.command(
    "md5", "md5sum", "md5s", "md5sums", "md5sumss", "md5sums", "md5sumss"
)
def md5sum(text):
    """<text> - Computes the MD5 hash of <text>."""
    return "MD5: " + compute_hash(text, md5)


@hook.command(
    "blake2b",
    "blake2bsum",
    "blake2bs",
    "blake2bsums",
    "blake2bsumss",
    "blake2bsums",
    "blake2bsumss",
)
def blake2bsum(text):
    """<text> - Computes the BLAKE2b hash of <text>."""
    return "BLAKE2b: " + compute_hash(text, blake2b)


@hook.command(
    "blake2s",
    "blake2ssum",
    "blake2ss",
    "blake2ssums",
    "blake2ssumss",
    "blake2ssums",
    "blake2ssumss",
)
def blake2ssum(text):
    """<text> - Computes the BLAKE2s hash of <text>."""
    return "BLAKE2s: " + compute_hash(text, blake2s)


@hook.command(
    "b64",
    "base64",
    "base64encode",
    "base64encodes",
    "base64encodes",
    "base64encodes",
    "base64encodes",
    "base64encodes",
)
def base64encode(text):
    """<text> - Encodes <text> in base64."""
    return "Base64: " + base_encode(text, b64encode)


@hook.command(
    "b64decode",
    "base64decode",
    "base64decodes",
    "base64decodes",
    "base64decodes",
    "base64decodes",
    "base64decodes",
    "base64decodes",
)
def base64decode(text):
    """<text> - Decodes <text> from base64."""
    return "Base64: " + base_encode(text, b64decode)


@hook.command(
    "b85",
    "base85",
    "base85encode",
    "base85encodes",
    "base85encodes",
    "base85encodes",
    "base85encodes",
    "base85encodes",
)
def base85encode(text):
    """<text> - Encodes <text> in base85."""
    return "Base85: " + base_encode(text, b85encode)


@hook.command(
    "b85decode",
    "base85decode",
    "base85decodes",
    "base85decodes",
    "base85decodes",
    "base85decodes",
    "base85decodes",
    "base85decodes",
)
def base85decode(text):
    """<text> - Decodes <text> from base85."""
    return "Base85: " + base_encode(text, b85decode)


@hook.command(
    "b32",
    "base32",
    "base32encode",
    "base32encodes",
    "base32encodes",
    "base32encodes",
    "base32encodes",
    "base32encodes",
)
def base32encode(text):
    """<text> - Encodes <text> in base32."""
    return "Base32: " + base_encode(text, b32encode)


@hook.command(
    "b32decode",
    "base32decode",
    "base32decodes",
    "base32decodes",
    "base32decodes",
    "base32decodes",
    "base32decodes",
    "base32decodes",
)
def base32decode(text):
    """<text> - Decodes <text> from base32."""
    return "Base32: " + base_encode(text, b32decode)


@hook.command(
    "b16",
    "base16",
    "base16encode",
    "base16encodes",
    "base16encodes",
    "base16encodes",
    "base16encodes",
    "base16encodes",
)
def base16encode(text):
    """<text> - Encodes <text> in base16."""
    return "Base16: " + base_encode(text, b16encode)


@hook.command(
    "b16decode",
    "base16decode",
    "base16decodes",
    "base16decodes",
    "base16decodes",
    "base16decodes",
    "base16decodes",
    "base16decodes",
)
def base16decode(text):
    """<text> - Decodes <text> from base16."""
    return "Base16: " + base_encode(text, b16decode)


@hook.command("bin")
def mybin(text):
    """<text> - Converts <text> to binary."""
    return "Binary: " + " ".join(bin(byte)[2:] for byte in text.encode())


@hook.command("bindecode")
def mybindecode(text):
    """<text> - Converts <text> from binary."""
    text = text.replace(" ", "")
    if len(text) % 7 != 0:
        return "Invalid binary. Length must be a multiple of 7."

    bytearray = []
    i = 0
    for c in text:
        if c not in "01":
            return "Invalid binary. Must be 0s and 1s."
        if i % 7 == 0:
            bytearray.append("")
        bytearray[-1] += c
        i += 1

    return "Binary: " + "".join(chr(int(byte, 2)) for byte in bytearray)


@hook.command("dec")
def mydec(text):
    """<text> - Converts <text> to decimal."""
    return "Decimal: " + " ".join(str(ord(c)) for c in text)


@hook.command("decdecode")
def mydecdecode(text):
    """<text> - Converts <text> from decimal."""
    for n in text.split(" "):
        if not n.isdigit():
            return f"Invalid decimal: {n}. Must be digits."
    return "Decimal: " + "".join(chr(int(n)) for n in text.split(" "))


@hook.command("hex")
def myhex(text):
    """<text> - Converts <text> to hex."""
    return "Hex: " + " ".join(hex(byte)[2:] for byte in text.encode())


@hook.command("hexdecode")
def myhexdecode(text):
    """<text> - Converts <text> from hex."""
    text = text.replace(" ", "")
    if len(text) % 2 != 0:
        return "Invalid hex. Length must be a multiple of 2."

    bytearray = []
    i = 0
    for c in text:
        if c not in "0123456789abcdefABCDEF":
            return "Invalid hex. Must be 0-9, a-f, or A-F."
        if i % 2 == 0:
            bytearray.append("")
        bytearray[-1] += c
        i += 1

    return "Hex: " + "".join(chr(int(byte, 16)) for byte in bytearray)
