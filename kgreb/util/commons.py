import json
from typing import Any, Final

from . import exceptions

DIGITS: Final = tuple("0123456789")

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36",
    "referer": "https://kegs.org.uk/",
}


def webscrape_value(raw, text_before, text_after, cls: type = str, i1: int = 1, i2: int = 0) -> int | Any:
    return cls(raw.split(text_before)[i1].split(text_after)[i2])


def _read_json_number(string: str) -> float | int:
    ret = ''

    minus = string[0] == '-'
    if minus:
        ret += '-'
        string = string[1:]

    def read_fraction(sub: str):
        sub_ret = ''
        if sub[0] == '.':
            sub_ret += '.'
            sub = sub[1:]
            while sub[0] in DIGITS:
                sub_ret += sub[0]
                sub = sub[1:]

        return sub_ret, sub

    def read_exponent(sub: str):
        sub_ret = ''
        if sub[0].lower() == 'e':
            sub_ret += sub[0]
            sub = sub[1:]

            if sub[0] in "-+":
                sub_ret += sub[0]
                sub = sub[1:]

            if sub[0] not in DIGITS:
                raise exceptions.UnclosedJSONError(f"Invalid exponent {sub}")

            while sub[0] in DIGITS:
                sub_ret += sub[0]
                sub = sub[1:]

        return sub_ret

    if string[0] == '0':
        ret += '0'
        string = string[1:]

    elif string[0] in DIGITS[1:9]:
        while string[0] in DIGITS:
            ret += string[0]
            string = string[1:]

    frac, string = read_fraction(string)
    ret += frac

    ret += read_exponent(string)

    return json.loads(ret)


def consume_json(string: str, i: int = 0) -> str | float | int | dict | list | bool | None:
    """
    Reads a JSON string and stops at the natural end (i.e. when brackets close, or when quotes end, etc.)
    """
    # Named by ChatGPT
    section = ''.join(string[i:])
    if section.startswith("true"):
        return True
    elif section.startswith("false"):
        return False
    elif section.startswith("null"):
        return None
    elif section[0] in "0123456789.-":
        return _read_json_number(section)

    depth = 0
    json_text = ''
    out_string = True

    for char in section:
        json_text += char

        if char == '"':
            if len(json_text) > 1:
                unescaped = json_text[-2] != '\\'
            else:
                unescaped = True
            if unescaped:
                out_string ^= True
                if out_string:
                    depth -= 1
                else:
                    depth += 1

        if out_string:
            if char in "[{":
                depth += 1
            elif char in "}]":
                depth -= 1

        if depth == 0 and json_text.strip():
            return json.loads(json_text.strip())

    raise exceptions.UnclosedJSONError(f"Unclosed JSON string, read {json_text}")
