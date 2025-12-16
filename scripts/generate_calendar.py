import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

# Configuration
TIMEZONE = pytz.timezone("Europe/Paris")
GITHUB_PAGES_ICS_PATH = "docs/tango_bourges.ics"  # fichier généré pour GitHub Pages
PRIMARY_URL = "https://www.tangobourgesbasket.com/pros/calendrier-resultats/"
FALLBACK_URLS = [
    "https://www.proballers.com/fr/basketball/equipe/2654/bourges/calendrier",
    "https://www.bebasket.fr/equipe/bourges/calendrier"
]

def fetch_html(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def parse_tango_calendar(html):
    """Parse la page Tango Bourges et retourne une liste de matchs"""
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    # Inspecté sur le site : les matchs sont dans <div class="calendar-row">
    for row in soup.select(".calendar-row"):
        date_str = row.select_one(".date")  # exemple : 14/12/2025
        if not date_str:
            continue
        date_str = date_str.get_text(strip=True)

        team_home = row.select_one(".team-home")
        team_away = row.select_one(".team-away")
        comp = row.select_one(".competition")  # LFB, EuroLeague, etc.
        time_tag = row.select_one(".time")  # heure si disponible

        # Parsing
        try:
            match_date = datetime.strptime(date_str, "%d/%m/%Y")
        except:
            continue

        # Heure
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            try:
                h, m = map(int, time_text.split(":"))
                match_date = match_date.replace(hour=h, minute=m)
            except:
                pass  # heure inconnue -> journée entière

        home = team_home.get_text(strip=True) if team_home else "Tango Bourges"
        away = team_away.get_text(strip=True) if team_away else "Adversaire inconnu"
        comp_name = comp.get_text(strip=True) if comp else "Match"

        matches.append({
            "summary": f"{home} vs {away} ({comp_name})",
            "dtstart": match_date,
            "dtend": match_date + timedelta(hours=2),  # durée par défaut 2h
            "all_day": time_tag is None
        })

    return matches

def fallback_parse(url):
    """Fallback parser pour les autres sites, à adapter selon le HTML"""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    # Simple fallback : chercher toutes les lignes de calendrier
    for row in soup.select("tr"):
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        date_str = cols[0].get_text(strip=True)
        try:
            match_date = datetime.strptime(date_str, "%d/%m/%Y")
        except:
            continue

        teams = cols[1].get_text(strip=True).split(" - ")
        home = teams[0] if len(teams) > 0 else "Tango Bourges"
        away = teams[1] if len(teams) > 1 else "Adversaire inconnu"
        comp_name = cols[2].get_text(strip=True) if len(cols) > 2 else "Match"

        matches.append({
            "summary": f"{home} vs {away} ({comp_name})",
            "dtstart": match_date,
            "dtend": match_date + timedelta(hours=2),
            "all_day": True
        })
    return matches

def generate_ics(matches, path):
    cal = Calendar()
    cal.add('prodid', '-//Tango Bourges Basket//maximeduc.github.io//')
    cal.add('version', '2.0')

    for m in matches:
        event = Event()
        event.add('summary', m["summary"])
        if m["all_day"]:
            event.add('dtstart', m["dtstart"].date())
            event.add('dtend', (m["dtend"]).date())
        else:
            event.add('dtstart', TIMEZONE.localize(m["dtstart"]))
            event.add('dtend', TIMEZONE.localize(m["dtend"]))
        cal.add_component(event)

    with open(path, 'wb') as f:
        f.write(cal.to_ical())

def main():
    # Essayer le site principal
    try:
        html = fetch_html(PRIMARY_URL)
        matches = parse_tango_calendar(html)
    except Exception as e:
        print("Erreur primary site:", e)
        matches = []

    # Fallbacks si aucun match récupéré
    if not matches:
        for url in FALLBACK_URLS:
            try:
                matches = fallback_parse(url)
                if matches:
                    break
            except Exception as e:
                print(f"Erreur fallback {url}: {e}")

    # Génération ICS
    if matches:
        generate_ics(matches, GITHUB_PAGES_ICS_PATH)
        print(f"{len(matches)} matchs ajoutés dans {GITHUB_PAGES_ICS_PATH}")
    else:
        print("Aucun match trouvé.")

if __name__ == "__main__":
    main()
