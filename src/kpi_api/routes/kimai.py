"""
Ce module contient les fonctions permettant de récupérer les heures de travail des utilisateurs
"""

import datetime

import requests

from kpi_api.utils.config import KIMAI_TOKEN, KIMAI_URL


def get_all_users_hours(start_date: str, end_date: str):
    """
    Récupère les heures de travail de tous les utilisateurs pour une période donnée
    :param start_date:
    :param end_date:
    :return:
    """
    headers = {'Authorization': f'Bearer {KIMAI_TOKEN}'}

    # 1. Récupération de tous les utilisateurs
    users_response = requests.get(f"{KIMAI_URL}/api/users", headers=headers)
    users = {u['id']: u['alias'] for u in users_response.json()}
    print(f"UTILISATEURS DISPONIBLES: {users}", flush=True)

    # 2. Initialisation du résultat avec 0h pour tous
    result = {uid: 0 for uid in users.keys()}

    # 3. Récupération des feuilles de temps
    page = 1
    while True:
        params = {
            'begin': start_date.replace('Z', '')[:19],
            'end': end_date.replace('Z', '')[:19],
            'page': str(page),
            'size': '100',
            'user': 'all'  # <-- Clé cruciale pour toutes les feuilles
        }

        response = requests.get(f"{KIMAI_URL}/api/timesheets", headers=headers, params=params)
        data = response.json()
        print(f"PAGE {page} - ENTRIES: {len(data)}", flush=True)

        # 4. Mise à jour des heures
        for entry in data:
            user_id = entry.get('user')
            if isinstance(user_id, dict):  # Cas où user est un objet
                user_id = user_id.get('id')

            if user_id in result:
                result[user_id] += entry.get('duration', 0)

        if len(data) < 100:
            break
        page += 1

    # supprimer l'user 11
    result.pop(11, None)

    # 5. Conversion et tri
    return sorted([
        {
            'username': users[uid],
            'hours': round(total / 3600, 2)
        } for uid, total in result.items()
    ], key=lambda x: x['hours'], reverse=True)


def get_all_current_week_hours():
    """
    Récupère les heures de travail de tous les utilisateurs pour la semaine courante
    :return:
    """
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=today.weekday())
    end_date = start_date + datetime.timedelta(days=6)
    return get_all_users_hours(f"{start_date}T00:00:00Z", f"{end_date}T23:59:59Z")


def get_all_last_week_hours():
    """
    Récupère les heures de travail de tous les utilisateurs pour la semaine précédente
    :return:
    """
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=today.weekday() + 7)
    end_date = start_date + datetime.timedelta(days=6)
    return get_all_users_hours(f"{start_date}T00:00:00Z", f"{end_date}T23:59:59Z")
