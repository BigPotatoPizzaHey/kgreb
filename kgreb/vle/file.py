from __future__ import annotations

import requests
from dataclasses import dataclass
from datetime import datetime

from . import session
from ..util.commons import headers


@dataclass(init=True)
class File:
    """
    Class representing both files and directories
    """
    filename: str
    filepath: str

    size: int
    author: str
    license: str

    mime: str
    type: str

    url: str
    icon_url: str

    datemodified: datetime
    datecreated: datetime

    _session: session.Session = None

    def __repr__(self):
        return f"<File: {self.filename}>"

    @property
    def content(self):
        return requests.get(self.url, headers=self._session.headers, cookies=self._session.cookies).content

    def delete(self):
        """
        Deletes the file from the session's file manager
        """
        ret = requests.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                            params={"action": "delete"},
                            data={
                                "sesskey": self._session.sesskey,

                                "clientid": self._session.file_client_id,
                                "itemid": self._session.file_item_id,
                                "filename": self.filename
                            }, cookies=self._session.cookies, headers=self._session.headers)
        print(ret.content)

    @staticmethod
    def from_json(data: dict, _session: session.Session = None) -> File:
        _fn = data.get("filename")
        _fp = data.get("filepath")

        _size = data.get("size")
        _author = data.get("author")
        _licence = data.get("license")

        _mime = data.get("mimetype")
        _type = data.get("type")

        _url = data.get("url")
        _icon_url = data.get("icon")
        # Thumbnail url is the same as icon url but different size - use urllib.parse

        # These are stored as timestamps
        _datemodified = datetime.fromtimestamp(data.get("datemodified"))
        _datecreated = datetime.fromtimestamp(data.get("datecreated"))

        return File(_fn, _fp, _size, _author, _licence, _mime, _type, _url, _icon_url, _datemodified, _datecreated,
                    _session)