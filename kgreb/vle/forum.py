from __future__ import annotations

from urllib.parse import urlparse, parse_qs
from datetime import datetime

import requests
import dateparser
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, NavigableString, PageElement

from . import session, user


@dataclass(init=True, repr=True)
class Post:
    creator: user.User = None


@dataclass(init=True, repr=True)
class Discussion:
    id: int = None

    name: str = None
    # author: user.User = None # It only shows a name & pfp - but not an actual link

    date_created: datetime = None
    # last_post: Post = None
    reply_count: int = None

    _session: session.Session = field(repr=False, default=None)
    _top_post: Post = field(repr=False, default=None)

    def update_from_forum_html(self, elem: PageElement):
        for i, item in enumerate(elem.find_all("td")):
            if i == 0:
                # Star this discussion
                ...

            elif i == 1:
                # Name
                anchor = item.find("a")
                self.name = anchor.text

                # You can also get id from the url
                parse = urlparse(anchor.attrs.get("href"))
                qparse = parse_qs(parse.query)
                self.id = int(qparse.get("d")[0])

            elif i == 2:
                # Started by
                ...

            elif i == 3:
                # Reply count
                self.reply_count = int(item.find("a").text.strip())

            elif i == 4:
                # Last post
                ...

            elif i == 5:
                # Date created
                text = item.text.strip()
                self.date_created = dateparser.parse(text)

            else:
                break

    @property
    def url(self):
        return f"https://vle.kegs.org.uk/mod/forum/discuss.php?d={self.id}"

    @property
    def top_post(self) -> Post:
        if not self._top_post:
            ...
        return self._top_post


@dataclass(init=True, repr=True)
class Forum:
    id: int

    name: str = None
    description: str = None
    contents: list[Discussion] = None

    _session: session.Session = None

    def update_by_id(self):
        response = requests.get("https://vle.kegs.org.uk/mod/forum/view.php",
                                params={"f": self.id}, headers=self._session.headers, cookies=self._session.cookies)
        soup = BeautifulSoup(response.text, "html.parser")

        container = soup.find("div", {"role": "main"})
        for i, element in enumerate(container.children):
            if element.name == "h2":
                self.name = element.text

            elif element.name == "div":
                div_id = element.attrs.get("id")

                if div_id == "intro":
                    self.description = element.text

                else:
                    element: PageElement
                    post_list = element.find("table", {"class": "table table-hover table-striped discussion-list"})

                    for tpart in post_list.children:
                        tpart: PageElement
                        if tpart.name == "tbody":
                            discussions = []

                            # List of discussions
                            for discuss_elem in tpart.children:
                                if not isinstance(discuss_elem, NavigableString):
                                    discussion = Discussion()
                                    discussion.update_from_forum_html(discuss_elem)
                                    discussions.append(discussion)
                            self.contents = discussions
