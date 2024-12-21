"""
Anything to do with the main website: https://kegs.org.uk/

Should really only be about fetching data, not posting any
"""

from urllib.parse import urlparse

import requests
from dataclasses import dataclass, field
from datetime import datetime
import dateparser

@dataclass(init=True, repr=True)
class Asset:
    content: bytes = field(repr=False, default=None)
    name: str=None
    mime: str=None
    last_modified: datetime=None

def download_asset_by_id(_id: int):
    response = requests.get("https://www.kegs.org.uk/force_download.cfm",
                            params={"id": _id})
    fname = urlparse(response.url).path.split('/')[-1]

    return Asset(response.content,
                 fname,
                 response.headers["Content-Type"],
                 dateparser.parse(response.headers["Last-Modified"]))
