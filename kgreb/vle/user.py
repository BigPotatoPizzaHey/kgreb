from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from typing import Final
from dataclasses import dataclass

from . import session
from ..util import exceptions

DELETED_USER: Final[str] = "This user account has been deleted"
INVALID_USER: Final[str] = "Invalid user"
FORBIDDEN_USER: Final[str] = "The details of this user are not available to you"


@dataclass(init=True, repr=True)
class User:
    id: int

    name: str = None
    email: str = None
    image_url: str = None

    country: str = None
    city: str = None
    web_page: str = None

    interests: list = None
    courses: list = None

    first_access: str = None
    last_access: str = None

    description: str = None

    _session: session.Session = None

    @property
    def has_default_image(self):
        return self.image_url == "https://vle.kegs.org.uk/theme/image.php/trema/core/1585328846/u/f1"

    def update_from_id(self):
        response = requests.get("https://vle.kegs.org.uk/user/profile.php",
                                params={"id": self.id},
                                headers=self._session.headers, cookies=self._session.cookies)
        text = response.text
        soup = BeautifulSoup(text, "html.parser")

        if DELETED_USER in text:
            raise exceptions.DeletedUser(f"User id {self.id} is deleted!")

        elif INVALID_USER in text:
            raise exceptions.InvalidUser(f"User id {self.id} is invalid!")

        elif FORBIDDEN_USER in text:
            raise exceptions.ForbiddenUser(f"User id {self.id} is forbidden!")

        else:
            # Get user's name
            self.name = str(soup.find("div", {"class": "page-header-headings"}).contents[0].text)

            # Get user image
            self.image_url = soup.find_all("img", {"class": "userpicture"})[1].get("src")

            user_profile = soup.find("div", {"class": "userprofile"})
            self.description = user_profile.find("div", {"class": "description"})

            categories = user_profile.find_all("section", {"class", "node_category"})

            interests_node, interests, courses = None, [], []

            for category in categories:
                category_name = category.find("h3").contents[0]

                if category_name == "User details":
                    user_details = list(category.children)[1]

                    # This is an unordered list containing the Email, Country, City and Interest
                    content_nodes = user_details.find_all("li", {"class", "contentnode"})

                    for li in content_nodes:
                        dl = li.find("dl")

                        dd = dl.find("dd")
                        item_name = dl.find("dt").contents[0]

                        if item_name == "Email address":
                            self.email = dl.find("a").contents[0]

                        elif item_name == "City/town":
                            self.city = dd.contents[0]

                        elif item_name == "Country":
                            self.country = dd.contents[0]

                        elif item_name == "Web page":
                            self.web_page = dl.find("a").get("href")

                        elif item_name == "Interests":
                            interests_node = dl

                    if interests_node is not None:
                        try:
                            for anchor in interests_node.find_all("a"):
                                interests.append(anchor.contents[0][21:])
                        except IndexError:
                            ...

                        if interests:
                            self.interests = interests

                elif category_name == "Course details":
                    for anchor in category.find_all("a"):
                        courses.append((anchor.get("href").split('=')[-1],
                                        anchor.contents[0]))
                    if courses:
                        self.courses = courses

                elif category_name == "Miscellaneous":
                    ...

                elif category_name == "Reports":
                    ...

                elif category_name == "Login activity":
                    for i, activity in enumerate(category.find_all("dd")):
                        if i == 0:
                            self.first_access = activity.contents[0]
                        else:
                            self.last_access = activity.contents[0]
