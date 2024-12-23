from __future__ import annotations

import dateparser
import requests
import mimetypes
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, SoupStrainer

from ..util import exceptions, commons

import atexit

from .timetable import WeekDate, Lesson


class Session:
    def __init__(self, _sess: requests.Session):
        self._sess: requests.Session = _sess

        self._name: str | None = None

        self._timetable_weeks: list[WeekDate] | None = None

        atexit.register(self.logout)

    def __repr__(self):
        return f"Session for {self.name}"

    def logout(self):
        resp = self._sess.get("https://www.bromcomvle.com/Auth/Logout")
        print(f"Automatically logged out with status code: {resp.status_code}")
        self._sess = None

        return resp

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
    def get_timetable(self, start_date: datetime | WeekDate = None, end_date: datetime | WeekDate = None):
        if isinstance(start_date, WeekDate):
            start_date = start_date.date
        if isinstance(end_date, WeekDate):
            end_date = end_date.date

        if start_date is None:
            start_date = self.current_week.date
        if end_date is None:
            end_date = start_date + timedelta(days=7)

        response = self._sess.get("https://www.bromcomvle.com/Timetable/GetTimeTable",
                                  params={
                                      "WeekStartDate": commons.to_dformat(start_date),
                                      "weekEndDate": commons.to_dformat(end_date),
                                      "type": 1
                                  })
        data = response.json()["table"]

        lessons = []
        for lesson_data in data:
            lesson_data: dict[str, str | int]
            lessons.append(
                Lesson(
                    lesson_data.get("periods"),
                    lesson_data.get("subject"),
                    lesson_data.get("class"),
                    lesson_data.get("room"),
                    lesson_data.get("teacherName"),
                    datetime.fromisoformat(
                        lesson_data.get("startDate")
                    ),
                    datetime.fromisoformat(
                        lesson_data.get("endDate")
                    ),
                    color=lesson_data.get("subjectColour")
                ))
        return lessons

    @property
    def timetable_weeks(self):
        if self._timetable_weeks is None:
            self._timetable_weeks = []

            text = self._sess.get("https://www.bromcomvle.com/Timetable").text
            soup = BeautifulSoup(text, "html.parser")

            date_selector = soup.find("select", {"id": "WeekStartDate"})

            for option in date_selector.find_all("option"):
                value = dateparser.parse(option.attrs.get("value"))
                text = option.text

                term, week, _ = text.split(' - ')
                term = commons.webscrape_section(term, "Term ", '', cls=int)
                week = commons.webscrape_section(week, "Week ", '', cls=int)

                self._timetable_weeks.append(
                    WeekDate(term, week, value)
                )

        return self._timetable_weeks

    @property
    def current_week(self) -> WeekDate | None:
        """
        Gets the current existing timetable week (will go to last school week during holidays)
        """
        prev = None
        for wdate in self.timetable_weeks:
            if wdate.date > datetime.today():
                return prev
            prev = wdate


def login(school_id: int, username: str, password: str, remember_me: bool = True) -> Session:
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
        if response.status_code == 500:
            raise exceptions.ServerError(
                f"The bromcom server experienced some error when handling the login request (ERR 500). Response content: {response.content}")
        else:
            raise exceptions.Unauthorised(
                f"The provided details for {username} may be invalid. Status code: {response.status_code} "
                f"Response content: {response.content}")

    return Session(_sess)
