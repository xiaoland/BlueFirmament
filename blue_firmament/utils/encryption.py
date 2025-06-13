"""Utils about encryption
"""

import hashlib


def md5(text):
    """Calculate MD5 hash of text
    """
    if isinstance(text, str):
        text = text.encode('utf-8')
    return hashlib.md5(text).hexdigest()