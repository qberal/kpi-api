"""
Fonctions pour récupérer les événements du calendrier Nextcloud.
"""

from datetime import datetime, timedelta, date, time

import pytz
from caldav import DAVClient
from dateutil.rrule import rruleset, rrulestr

from kpi_api.utils.config import NEXTCLOUD_CALDAV_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD


def get_nextcloud_events():
    """
    Récupère les événements du calendrier Nextcloud et les retourne en JSON.

    :return: Liste d'événements sous forme de dictionnaires
    """

    client = DAVClient(NEXTCLOUD_CALDAV_URL, username=NEXTCLOUD_USERNAME, password=NEXTCLOUD_PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()

    if not calendars:
        return {"error": "Aucun calendrier trouvé."}

    events_list = []
    now = datetime.now(pytz.UTC)
    week_start = now - timedelta(days=now.weekday())  # Début de la semaine courante
    week_end = week_start + timedelta(weeks=2)  # Fin de la semaine suivante

    for calendar in calendars:
        calendar_name = calendar.name  # Récupère le nom du calendrier

        # Attribue une couleur en fonction du calendrier
        if calendar_name == "Cours":
            color = 10
        else:
            color = 20

        for event in calendar.events():
            vevent = event.vobject_instance.vevent
            event_start = vevent.dtstart.value
            event_end = vevent.dtend.value if hasattr(vevent, 'dtend') else None
            name = vevent.summary.value if hasattr(vevent, 'summary') else ""
            description = vevent.description.value if hasattr(vevent, 'description') else ""
            location = vevent.location.value if hasattr(vevent, 'location') else ""

            # Gestion des événements récurrents
            if hasattr(vevent, 'rrule'):
                rrule = rrulestr(vevent.rrule.value, dtstart=vevent.dtstart.value)
                rrule_set = rruleset()
                rrule_set.rrule(rrule)

                occurrences = rrule_set.between(week_start, week_end, inc=True)
                for occurrence in occurrences:
                    events_list.append({
                        "event_start": occurrence.isoformat(),
                        "event_end": (occurrence + (event_end - event_start)).isoformat() if event_end else None,
                        "name": name,
                        "description": description,
                        "location": location,
                        "color": color
                    })
            else:
                if isinstance(event_start, datetime) and week_start <= event_start < week_end:
                    events_list.append({
                        "event_start": event_start.isoformat(),
                        "event_end": event_end.isoformat() if event_end else None,
                        "name": name,
                        "description": description,
                        "location": location,
                        "color": color
                    })

    return events_list


def get_next_event(calendar_name):
    """
    Récupère le prochain événement à venir strictement après l'heure actuelle.
    """
    client = DAVClient(NEXTCLOUD_CALDAV_URL, username=NEXTCLOUD_USERNAME, password=NEXTCLOUD_PASSWORD)
    principal = client.principal()
    calendars = principal.calendars()

    if not calendars:
        return {"error": "Aucun calendrier trouvé."}

    events_list = []
    now = datetime.now(pytz.UTC)  # Heure actuelle en UTC

    for calendar in calendars:
        if calendar.name != calendar_name:
            continue

        for event in calendar.events():
            vevent = event.vobject_instance.vevent
            event_start = vevent.dtstart.value
            event_end = vevent.dtend.value if hasattr(vevent, 'dtend') else None
            name = vevent.summary.value if hasattr(vevent, 'summary') else ""
            description = vevent.description.value if hasattr(vevent, 'description') else ""
            location = vevent.location.value if hasattr(vevent, 'location') else ""

            # Conversion des dates all-day en datetime
            if isinstance(event_start, date) and not isinstance(event_start, datetime):
                event_start = datetime.combine(event_start, time.min, tzinfo=pytz.UTC)

            # Gestion des événements récurrents
            if hasattr(vevent, 'rrule'):
                rrule = rrulestr(vevent.rrule.value, dtstart=event_start)

                # Prochaine occurrence strictement après maintenant
                next_occurrence = rrule.after(now, inc=False)

                if next_occurrence:
                    # Conversion timezone si nécessaire
                    if next_occurrence.tzinfo is None:
                        next_occurrence = next_occurrence.replace(tzinfo=pytz.UTC)

                    # description = Aujourd'hui si l'événement est aujourd'hui, demain si l'événement est demain, sinon la date de l'événement
                    if next_occurrence.date() == now.date():
                        description = "Aujourd'hui"
                    elif next_occurrence.date() == now.date() + timedelta(days=1):
                        description = "Demain"
                    else:
                        description = next_occurrence.strftime("%d/%m/%Y")

                    # Calcul de la fin de l'événement
                    duration = event_end - event_start if event_end else None
                    event_end_occurrence = next_occurrence + duration if duration else None

                    events_list.append({
                        "event_start": next_occurrence.isoformat(),
                        "event_end": event_end_occurrence.isoformat() if event_end_occurrence else None,
                        "name": name,
                        "description": description,
                        "location": location
                    })

            # Événements non récurrents
            else:
                if isinstance(event_start, datetime) and event_start > now:
                    events_list.append({
                        "event_start": event_start.isoformat(),
                        "event_end": event_end.isoformat() if event_end else None,
                        "name": name,
                        "description": description,
                        "location": location
                    })

    if not events_list:
        return {}

    # Tri par date de début et sélection du premier
    events_list.sort(key=lambda x: x["event_start"])
    return events_list[0]


def get_next_cours():
    """
    Récupère les événements du calendrier 'Cours'.
    """
    return get_next_event("Cours")


def get_next_pic_event():
    """
    Récupère les événements du calendrier 'Pic'.
    """
    return get_next_event("Réunions (Alix ANNERAUD)")
