import requests
import re
from bs4 import BeautifulSoup
from functools import lru_cache

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OER-Agent/1.0)"}
BASE_URL = "https://catalog.ggc.edu/content.php"
PARAMS = {
    "catoid": "8",
    "navoid": "142",
    "filter[item_type]": "3",
    "filter[only_active]": "1",
    "filter[3]": "1",
}
TOTAL_PAGES = 8

@lru_cache(maxsize=1)
def fetch_all_courses():
    """Scrape all courses from GGC catalog across all pages. Returns dict keyed by dept prefix."""
    all_courses = {}

    for page in range(1, TOTAL_PAGES + 1):
        params = {**PARAMS, "filter[cpage]": str(page)}
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Course links look like: preview_course_nopop.php?catoid=8&coid=XXXX
        # Course text looks like: "ACCT 2101 - Introduction to Financial Accounting"
        links = soup.select("a[href*='preview_course_nopop.php']")
        for a in links:
            text = a.get_text(strip=True)
            # Match pattern: "PREFIX 1234 - Course Name" or "PREFIX 1234K - Course Name"
            match = re.match(r'^([A-Z]+)\s+(\w+)\s+-\s+(.+)$', text)
            if match:
                prefix = match.group(1)
                code   = match.group(2)
                name   = match.group(3)
                if prefix not in all_courses:
                    all_courses[prefix] = []
                all_courses[prefix].append({
                    "code": f"{prefix} {code}",
                    "name": f"{prefix} {code} - {name}"
                })

    return all_courses


def get_departments():
    """Return sorted list of department prefixes from the catalog."""
    all_courses = fetch_all_courses()
    return [{"code": dept, "name": dept} for dept in sorted(all_courses.keys())]


def get_courses(dept: str):
    """Return courses for a given department prefix."""
    all_courses = fetch_all_courses()
    return all_courses.get(dept.upper(), [])