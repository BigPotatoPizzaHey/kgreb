from __future__ import annotations

import requests
from beautifulprint import bprint
from bs4 import BeautifulSoup

from . import file
from ..util import commons


class Session:
    def __init__(self, moodle: str):
        self.cookies = {"MoodleSession": moodle}
        self.headers = commons.headers.copy()
        self._sesskey = None
        self._file_client_id = None
        self._file_item_id = None
        self.assert_login()

    # --- Session/auth related methods ---
    @property
    def sesskey(self):
        """Get the sesskey query parameter used in various functions"""
        if self._sesskey is None:
            pfx = "var M = {}; M.yui = {};\nM.pageloadstarttime = new Date();\nM.cfg = "

            response = requests.get("https://vle.kegs.org.uk/", cookies=self.cookies, headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")

            self._sesskey = None
            for script in soup.find_all("script"):
                text = script.text
                if "\"sesskey\":" in text:
                    i = text.find(pfx)
                    if i > -1:
                        i += len(pfx) - 1
                        data = commons.consume_json(text, i)

                        if isinstance(data, dict):
                            self._sesskey = data.get("sesskey")

        return self._sesskey

    @property
    def file_client_id(self):
        if self._file_client_id is None:
            response = requests.get("https://vle.kegs.org.uk/user/files.php", cookies=self.cookies,
                                    headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")

            for div in soup.find_all("div", {"class": "filemanager w-100 fm-loading"}):
                self._file_client_id = div.attrs["id"].split("filemanager-")[1]

        return self._file_client_id

    @property
    def file_item_id(self):
        if self._file_item_id is None:
            response = requests.get("https://vle.kegs.org.uk/user/files.php", cookies=self.cookies,
                                    headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")
            self._file_item_id = soup.find("input", {"id": "id_files_filemanager"}).attrs.get("value")

        return self._file_item_id

    @property
    def username(self):
        response = requests.get("https://vle.kegs.org.uk/login/index.php", cookies=self.cookies, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        for alert_elem in soup.find_all(attrs={"role": "alert"}):
            alert = alert_elem.text

            username = commons.webscrape_value(alert, "You are already logged in as ",
                                               ", you need to log out before logging in as different user.")
            if username:
                return username
        return None

    def assert_login(self):
        assert self.username

    # --- Private Files ---
    def _file_data(self, fp: str) -> dict:
        # Believe or not, KegsNet does actually have some JSON endpoints!
        return requests.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                             params={"action": "list"},
                             data={
                                 "sesskey": self.sesskey,

                                 "clientid": self.file_client_id,
                                 "itemid": self.file_item_id,
                                 "filepath": fp
                             }, cookies=self.cookies, headers=self.headers).json()

    def files_in_dir(self, fp: str):
        data = self._file_data(fp)["list"]
        files = []
        for file_data in data:
            files.append(file.File.from_json(file_data, self))
        return files

    @property
    def files(self):
        """gggg
        ... test
        """
        """
        # Old bs4 powered file getter
        text = requests.get("https://vle.kegs.org.uk/user/files.php",
                            cookies=self.cookies, headers=self.headers).text
        soup = BeautifulSoup(text, "html.parser")

        data = []
        for script in soup.find_all("script"):
            # Unfortunately, we have to search JavaScript to find the file data
            script_text = script.text
            # We can do a preliminary search of the JavaScript
            if r"https:\/\/vle.kegs.org.uk\/draftfile.php\/" in script_text:
                i = script_text.find("[{\"filename\":\"")
                if i > -1:
                    # What's worse, is that we have to make a special function to read JSON until its natural end
                    data = commons.consume_json(script_text, i)

        files = []
        for file_dict in data:
            files.append(file.File(
                file_dict["filename"],
                file_dict["size"],
                file_dict["author"],
                file_dict["license"],
                file_dict["datemodified"],
                file_dict["datecreated"],
                file_dict["url"],
                file_dict["icon"],
                file_dict["thumbnail"],

                self
            ))
        return files"""
        return self.files_in_dir('/')

    def add_file(self, title: str, data: bytes, author: str = '', _license: str = "unknown", fp: str = '/'):
        # Perhaps this method should take in a File object instead of title/data/author etc

        requests.post("https://vle.kegs.org.uk/repository/repository_ajax.php",
                      params={"action": "upload"},
                      data={
                          "sesskey": self.sesskey,
                          "repo_id": 3,  # I'm not sure if it has to be 3

                          "title": title,
                          "author": author,
                          "license": _license,

                          "clientid": self.file_client_id,
                          "itemid": self.file_item_id,
                          "savepath": fp
                      },
                      files={"repo_upload_file": data},
                      cookies=self.cookies, headers=self.headers)

        # Save changes
        requests.post("https://vle.kegs.org.uk/user/files.php",
                      data={"returnurl": "https://vle.kegs.org.uk/user/files.php",

                            "sesskey": self.sesskey,
                            "files_filemanager": self.file_item_id,
                            "_qf__user_files_form": 1,
                            "submitbutton": "Save changes"},
                      cookies=self.cookies, headers=self.headers)

    @property
    def file_zip(self):
        """
        Returns bytes of your files as a zip archive
        """
        url = requests.post("https://vle.kegs.org.uk/repository/draftfiles_ajax.php",
                            params={"action": "downloaddir"},
                            data={
                                "sesskey": self.sesskey,
                                "client_id": self.file_client_id,
                                "filepath": '/',
                                "itemid": self.file_item_id
                            },

                            headers=self.headers, cookies=self.cookies).json()["fileurl"]
        return requests.get(url, headers=self.headers, cookies=self.cookies).content


# --- * ---

def login(username: str, password: str):
    session = requests.Session()
    response = session.get("https://vle.kegs.org.uk/login/index.php")

    soup = BeautifulSoup(response.text, "html.parser")
    login_token = soup.find("input", {"name": "logintoken"})["value"]

    session.post("https://vle.kegs.org.uk/login/index.php",
                 data={"logintoken": login_token,
                       "anchor": None,
                       "username": username,
                       "password": password
                       }, headers=commons.headers)

    moodle = session.cookies.get("MoodleSession")

    return Session(moodle)


def login_by_moodle(moodle_cookie: str):
    return Session(moodle_cookie)
