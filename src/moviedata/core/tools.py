"""
Module providing handy utilities for general tasks.
"""
import io
import re
import zipfile
from unidecode import unidecode
import urllib.parse

def extract_file_from_zip_io(zip_buffer:io.BytesIO, filepath:str):
    """
    Receive BytesIO buffer of a zip-file and returns bytes buffer
    of unzipped file from specified path
    """
    with zipfile.ZipFile(zip_buffer) as z:
        # Reads raw bytes into memory
        file_bytes = z.read(filepath)
        # Remains open after context closes
        return io.BytesIO(file_bytes)


def hsl_to_rgb(hsl: tuple) -> tuple:
    """
    Receive tuple of HSL values in range in H [0, 255], S in [0, 100], L in [0, 100]
    Return tuple of RGB values in range [0, 255]
    """
    h = hsl[0]
    s = hsl[1]
    l = hsl[2]
    # Normalize inputs to standard ranges: H in [0, 360), S in [0, 1], L in [0, 1]
    h_norm = (h / 255.0) * 360.0 % 360.0
    s_norm = s / 100.0
    l_norm = l / 100.0

    # Calculate Chroma (c)
    c = (1.0 - abs(2.0 * l_norm - 1.0)) * s_norm

    # Intermediate value for second largest component
    x = c * (1.0 - abs((h_norm / 60.0) % 2 - 1.0))

    # Match lightness
    m = l_norm - c / 2.0

    # Determine RGB prime values based on hue sector
    if 0 <= h_norm < 60:
        r_p, g_p, b_p = c, x, 0.0
    elif 60 <= h_norm < 120:
        r_p, g_p, b_p = x, c, 0.0
    elif 120 <= h_norm < 180:
        r_p, g_p, b_p = 0.0, c, x
    elif 180 <= h_norm < 240:
        r_p, g_p, b_p = 0.0, x, c
    elif 240 <= h_norm < 300:
        r_p, g_p, b_p = x, 0.0, c
    else:
        r_p, g_p, b_p = c, 0.0, x

    # Scale back to 0-255 range
    r = round((r_p + m) * 255)
    g = round((g_p + m) * 255)
    b = round((b_p + m) * 255)

    return r, g, b

def parse_name_for_url(
        input_string:str,
        regular_url_parse=True,
        force_ascii_characters=False,
        replace_whitespace=False,
        remove_whitespace=False,
        replace_ampersand=False,
        replace_percent=False,
        remove_all_symbols=False):
    """
    Receives a "regular" input string (natural spelling).
    Then transforms it for usage in URLs.
    """
    # Initialize output
    parsed_string = input_string

    if force_ascii_characters:
        # Replace all accents or otherwise non-ASCII characters with regular characters
        # è -> e, ö -> o, ß -> ss
        parsed_string = unidecode(input_string)
    if replace_ampersand:
        # Replace "&" with written "and"
        parsed_string = parsed_string.replace("&","and")
    if replace_percent:
        # Replace "%" with written "percent"
        parsed_string = parsed_string.replace("%","percent")
    if remove_all_symbols:
        # Remove all symbols from the movie name
        parsed_string = re.sub(r'[^\w\s]', '', parsed_string)
    if replace_whitespace:
        # Replace empty space with underscores and make all lower chars
        parsed_string = (
            parsed_string
            .replace(" ","_")
            .lower()
        )
        # Find 2 or more consecutive underscores and replace with a single underscore
        # e.g. Louise__Thelma -> Louise_Thelma
        parsed_string = re.sub(r'_{2,}', '_', parsed_string)
    if remove_whitespace:
        parsed_string = parsed_string.replace(" ","")
    if regular_url_parse:
        # Perform regular URL-parsing, e.g. whitespace to %20
        parsed_string = urllib.parse.quote(parsed_string, safe=":/=?&")

    return parsed_string