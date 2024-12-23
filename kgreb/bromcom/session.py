from __future__ import annotations

import dateparser
import requests
import mimetypes
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, SoupStrainer

from ..util import exceptions, commons

from dataclasses import dataclass


@dataclass(init=True, repr=True)
class WeekDate:
    term_i: int
    week_i: int
    date: datetime


class Session:
    def __init__(self, _sess: requests.Session):
        self._sess = _sess

        self._name = None

    def __repr__(self):
        return f"Session for {self.name}"

    @property
    def name(self):
        if self._name is None:
            text = self._sess.get("https://www.bromcomvle.com/Home/Dashboard").text
            soup = BeautifulSoup(text, "html.parser", parse_only=SoupStrainer("span"))

            message = soup.find("span", {"id": "WelcomeMessage"})
            if message is None:
                raise exceptions.NotFound(f"Could not find welcome message! Response: {text}")

            self._name = commons.webscrape_section(message.text, "Hi ", ". Welcome Back!")

        return self._name

    @property
    def pfp(self):
        return self._sess.get("https://www.bromcomvle.com/AccountSettings/GetPersonPhoto").content

    @property
    def pfp_ext(self):
        response = self._sess.get("https://www.bromcomvle.com/AccountSettings/GetPersonPhoto")
        return mimetypes.guess_extension(response.headers.get("Content-Type", "image/Jpeg"))

    # --- Timetable methods ---
    def get_timetable(self, start_date: datetime = None, end_date: datetime = None):
        if start_date is None:
            start_date = datetime.today()
        if end_date is None:
            end_date = start_date + timedelta(days=7)

        prms = {
            "WeekStartDate": commons.to_dformat(start_date),
            "weekEndDate": commons.to_dformat(end_date),
            "type": 1
        }
        print(prms)
        response = self._sess.get("https://www.bromcomvle.com/Timetable/GetTimeTable",
                                  params=prms)
        print(response.content)

    def get_weeks(self):
        weeks = []

        text = self._sess.get("https://www.bromcomvle.com/Timetable").text
        soup = BeautifulSoup(text, "html.parser")

        date_selector = soup.find("select", {"id": "WeekStartDate"})

        for option in date_selector.find_all("option"):
            value = dateparser.parse(option.attrs.get("value"))
            text = option.text

            term, week, _ = text.split(' - ')
            term = commons.webscrape_section(term, "Term ", '', cls=int)
            week = commons.webscrape_section(week, "Week ", '', cls=int)

            weeks.append(
                WeekDate(
                    term, week, value
                )
            )

        return weeks


def login(school_id: int, username: str, password: str, remember_me: bool = False) -> Session:
    _sess = requests.Session()
    _sess.headers = commons.headers.copy()

    text = _sess.get("https://www.bromcomvle.com/").text
    soup = BeautifulSoup(text, "html.parser", parse_only=SoupStrainer("input"))

    rvinp = soup.find("input", {"name": "__RequestVerificationToken"})
    if rvinp is None:
        ptfy = BeautifulSoup(text, "html.parser").prettify()
        raise exceptions.NotFound(f"Could not find rv token; response text: {ptfy}")

    rvtoken = rvinp.attrs.get("value")

    response = _sess.post("https://www.bromcomvle.com/",
                          data={
                              "SpaceID": '',

                              "schoolid": school_id,
                              "username": username,
                              "password": password,

                              "__RequestVerificationToken": rvtoken,
                              "rememberme": str(remember_me).lower()
                          })

    if response.status_code != 200:
        raise exceptions.Unauthorised(
            f"The provided details for {username} may be invalid. Status code: {response.status_code} "
            f"Response content: {response.content}")

    return Session(_sess)
