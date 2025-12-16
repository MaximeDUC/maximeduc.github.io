import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import os

# Configuration
TIMEZONE = pytz.timezone("Europe/Paris")
PRIMARY_URL = "https://www.tangobourgesbasket.com/pros/calendrier-resultats/"
FALLBACK_URL = "https://www.bebasket.fr/equipe/bourges/calendrier"
# Ajouter ceci au début
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICS_PATH = os.path.join(REPO_ROOT, "docs", "tango_bourges.ics")


def fetch_html(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text

def parse_tango_calendar(html):
    """Parse la page Tango Bourges et retourne une liste de matchs"""
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    for div in soup.select("div.match-details"):
        comp_tag = div.select_one("p.competitionname")
        comp_name = comp_tag.get_text(strip=True) if comp_tag else "Match"

        date_tag = div.select_one("div.match-info p:nth-of-type(2)")
        match_date = None
        all_day = True
        if date_tag:
            parts = date_tag.get_text(strip=True).split(" - ")
            try:
                match_date = datetime.strptime(parts[0], "%d.%m.%Y")
                if len(parts) > 1:
                    h, m = map(int, parts[1].split(":"))
                    match_date = match_date.replace(hour=h, minute=m)
                    all_day = False
            except:
                continue
        if not match_date:
            continue

        home_tag = div.select_one("div.match-home-team p.nomequipe")
        away_tag = div.select_one("div.match-away-team p.nomequipe")
        home = home_tag.get_text(strip=True) if home_tag else "Tango Bourges"
        away = away_tag.get_text(strip=True) if away_tag else "Adversaire"

        matches.append({
            "summary": f"{home} vs {away} ({comp_name})",
            "dtstart": match_date,
            "dtend": match_date + timedelta(hours=2),
            "all_day": all_day
        })

    return matches

def parse_bebasket_calendar(html):
    """Parse la page BeBasket et retourne une liste de matchs (fallback)"""
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    for item in soup.select("div.basketball_Item__90C9M"):
        date_tag = item.select_one("div.basketball_Date__w7LIU")
        if not date_tag:
            continue
        parts = date_tag.get_text(strip=True).split("-")
        try:
            match_date = datetime.strptime(parts[0].strip() + ".2025", "%d/%m.%Y")
            all_day = True
            if len(parts) > 1:
                h, m = map(int, parts[1].replace("h", ":").split(":"))
                match_date = match_date.replace(hour=h, minute=m)
                all_day = False
        except:
            continue

        comp_tag = item.select_one("div.basketball_Number__zNOQH")
        comp_name = comp_tag.get_text(strip=True) if comp_tag else "Match"

        teams = item.select("div.basketball_TeamItem__Dv82U a")
        if len(teams) >= 2:
            home = teams[0].get_text(strip=True)
            away = teams[1].get_text(strip=True)
        else:
            home, away = "Bourges", "Adversaire"

        matches.append({
            "summary": f"{home} vs {away} ({comp_name})",
            "dtstart": match_date,
            "dtend": match_date + timedelta(hours=2),
            "all_day": all_day
        })

    return matches

def generate_ics(matches, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    cal = Calendar()
    cal.add('prodid', '-//Tango Bourges Basket//maximeduc.github.io//')
    cal.add('version', '2.0')

    for m in matches:
        event = Event()
        event.add('summary', m["summary"])
        if m["all_day"]:
            event.add('dtstart', m["dtstart"].date())
            event.add('dtend', m["dtend"].date())
        else:
            event.add('dtstart', TIMEZONE.localize(m["dtstart"]))
            event.add('dtend', TIMEZONE.localize(m["dtend"]))
        cal.add_component(event)

    with open(path, 'wb') as f:
        f.write(cal.to_ical())

def main():
    matches = []
    try:
        html = fetch_html(PRIMARY_URL)
        matches = parse_tango_calendar(html)
        if matches:
            print(f"{len(matches)} matchs récupérés depuis Tango Bourges")
    except Exception as e:
        print("Erreur Tango Bourges:", e)

    if not matches:
        print("Fallback vers BeBasket")
        try:
            html = fetch_html(FALLBACK_URL)
            matches = parse_bebasket_calendar(html)
            print(f"{len(matches)} matchs récupérés depuis BeBasket")
        except Exception as e:
            print("Erreur fallback BeBasket:", e)

    if matches:
        generate_ics(matches, ICS_PATH)
        print(f"{len(matches)} matchs écrits dans {ICS_PATH}")
    else:
        print("Aucun match trouvé, ICS non généré")

if __name__ == "__main__":
    main()
