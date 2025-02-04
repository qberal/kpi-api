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
    headers = {"Authorization": f"Bearer {KIMAI_TOKEN}"}

    # 1. Récupération de tous les utilisateurs
    users_response = requests.get(f"{KIMAI_URL}/api/users", headers=headers)
    users = {u["id"]: u["alias"] for u in users_response.json()}
    # print(f"UTILISATEURS DISPONIBLES: {users}", flush=True)

    # 2. Initialisation du résultat avec 0h pour tous
    result = {uid: 0 for uid in users.keys()}

    # 3. Récupération des feuilles de temps
    page = 1
    while True:
        params = {
            "begin": start_date.replace("Z", "")[:19],
            "end": end_date.replace("Z", "")[:19],
            "page": str(page),
            "size": "100",
            "user": "all",  # <-- Clé cruciale pour toutes les feuilles
        }

        response = requests.get(
            f"{KIMAI_URL}/api/timesheets", headers=headers, params=params
        )
        data = response.json()
        print(f"PAGE {page} - ENTRIES: {len(data)}", flush=True)

        # 4. Mise à jour des heures
        for entry in data:
            user_id = entry.get("user")
            if isinstance(user_id, dict):  # Cas où user est un objet
                user_id = user_id.get("id")

            if user_id in result:
                result[user_id] += entry.get("duration", 0)

        if len(data) < 100:
            break
        page += 1

    # supprimer l'user 11
    result.pop(11, None)

    # 5. Conversion et tri
    return sorted(
        [
            {"username": users[uid], "hours": round(total / 3600, 2)}
            for uid, total in result.items()
        ],
        key=lambda x: x["hours"],
        reverse=True,
    )


def get_all_users_hours_by_activity(start_date: str, end_date: str):
    """
    Récupère pour chaque utilisateur la répartition des heures travaillées en fonction de l'activité (présentiel, télétravail)
    sur une période donnée.

    Pour chaque utilisateur, on renvoie :
      - temps en présentiel
      - temps en télétravail
      - temps total (la somme des deux)

    On suppose que dans Kimai, la case "activité" est renseignée avec la valeur "présentiel" ou "télétravail".

    :param start_date: Début de la période (exemple : "2025-01-01T00:00:00Z")
    :param end_date: Fin de la période (exemple : "2025-01-31T23:59:59Z")
    :return: Une liste de dictionnaires triée par temps total décroissant.
             Exemple d'élément : {'username': 'alice', 'presentiel': 10.5, 'télétravail': 5.0, 'total': 15.5}
    """
    headers = {"Authorization": f"Bearer {KIMAI_TOKEN}"}

    # 1. Récupération de tous les utilisateurs
    users_response = requests.get(f"{KIMAI_URL}/api/users", headers=headers)
    users = {u["id"]: u["alias"] for u in users_response.json()}

    # 2. Initialisation du résultat pour chaque utilisateur (en secondes)
    result = {
        uid: {"presentiel": 0, "télétravail": 0, "total": 0} for uid in users.keys()
    }

    # 3. Récupération des feuilles de temps (pagination)
    page = 1
    while True:
        params = {
            "begin": start_date.replace("Z", "")[:19],
            "end": end_date.replace("Z", "")[:19],
            "page": str(page),
            "size": "100",
            "user": "all",  # On récupère les feuilles pour tous les utilisateurs
            "full": "1",  # Demande à l'API de renvoyer les objets complets (pour avoir l'objet activité complet)
        }

        response = requests.get(
            f"{KIMAI_URL}/api/timesheets", headers=headers, params=params
        )
        data = response.json()
        print(f"PAGE {page} - ENTRIES: {len(data)}", flush=True)
        if not data:
            break

        # 4. Mise à jour des heures en fonction de l'activité
        for entry in data:
            # Récupérer l'identifiant de l'utilisateur
            user_field = entry.get("user")
            if isinstance(user_field, dict):
                user_id = user_field.get("id")
            else:
                user_id = user_field

            if user_id not in result:
                continue

            duration = entry.get("duration", 0)  # en secondes

            # Récupération de l'activité
            activity = entry.get("activity")
            activity_name = None
            if isinstance(activity, dict):
                activity_name = activity.get(
                    "name"
                )  # selon votre configuration, la clé peut être 'name' ou 'alias'
            elif isinstance(activity, str):
                activity_name = activity

            # Ajout d'un affichage de débogage pour vérifier la valeur de l'activité
            # (Décommentez la ligne suivante pour voir ce qui est renvoyé)
            # print(f"User {user_id} - Activity: {activity_name}")

            # Comparaison en prenant en compte d'éventuelles différences de casse et d'espaces
            if activity_name and activity_name.strip().lower() == "présentiel":
                result[user_id]["presentiel"] += duration
                result[user_id]["total"] += duration
            elif activity_name and activity_name.strip().lower() == "télétravail":
                result[user_id]["télétravail"] += duration
                result[user_id]["total"] += duration
            # Si l'activité n'est ni "présentiel" ni "télétravail", on l'ignore.

        if len(data) < 100:
            break
        page += 1

    # Suppression de l'utilisateur 11 si présent (comme dans la version originale)
    result.pop(11, None)

    # 5. Conversion des secondes en heures et préparation du tri
    result_list = []
    for uid, durations in result.items():
        result_list.append(
            {
                "username": users[uid],
                "presentiel": round(durations["presentiel"] / 3600, 2),
                "télétravail": round(durations["télétravail"] / 3600, 2),
                "total": round(durations["total"] / 3600, 2),
            }
        )

    return sorted(result_list, key=lambda x: x["total"], reverse=True)


import requests


def get_user_hours_by_activity(start_date: str, end_date: str, user: int):
    """
    Récupère pour un utilisateur donné la répartition des heures travaillées en fonction de l'activité (présentiel, télétravail)
    sur une période donnée.

    Pour l'utilisateur, on renvoie :
      - temps en présentiel
      - temps en télétravail
      - temps total (la somme des deux)

    :param start_date: Début de la période (exemple : "2025-01-01T00:00:00Z")
    :param end_date: Fin de la période (exemple : "2025-01-31T23:59:59Z")
    :param user: L'ID de l'utilisateur dont on souhaite récupérer les données.
    :return: Un dictionnaire du type :
             {
               'username': 'alice',
               'presentiel': 10.5,
               'télétravail': 5.0,
               'total': 15.5
             }
    """
    headers = {"Authorization": f"Bearer {KIMAI_TOKEN}"}

    # 1. Récupérer tous les utilisateurs pour retrouver les informations de l'utilisateur ciblé
    users_response = requests.get(f"{KIMAI_URL}/api/users", headers=headers)
    users_data = users_response.json()

    target_user = None
    for u in users_data:
        if u["id"] == user:
            target_user = u
            break

    if not target_user:
        raise ValueError(f"Utilisateur avec l'ID {user} non trouvé.")

    # 2. Initialisation des durées (en secondes)
    result = {"presentiel": 0, "télétravail": 0, "total": 0}

    # 3. Récupération des feuilles de temps pour l'utilisateur spécifié (pagination)
    page = 1
    while True:
        params = {
            "begin": start_date.replace("Z", "")[:19],
            "end": end_date.replace("Z", "")[:19],
            "page": str(page),
            "size": "100",
            "user": str(user),  # On filtre sur l'utilisateur passé en paramètre
            "full": "1",  # Pour récupérer l'objet complet (notamment l'activité)
        }

        response = requests.get(
            f"{KIMAI_URL}/api/timesheets", headers=headers, params=params
        )
        data = response.json()
        print(f"PAGE {page} - ENTRIES: {len(data)}", flush=True)
        if not data:
            break

        # 4. Traitement des feuilles de temps
        for entry in data:
            duration = entry.get("duration", 0)
            activity = entry.get("activity")
            activity_name = None
            if isinstance(activity, dict):
                # Selon votre configuration, l'activité peut être dans 'name' ou 'alias'
                activity_name = activity.get("name") or activity.get("alias")
            elif isinstance(activity, str):
                activity_name = activity

            if activity_name:
                act = activity_name.strip().lower()
                if act == "présentiel":
                    result["presentiel"] += duration
                    result["total"] += duration
                elif act == "télétravail":
                    result["télétravail"] += duration
                    result["total"] += duration

        if len(data) < 100:
            break
        page += 1

    # 5. Conversion des durées en heures (1 heure = 3600 secondes) et arrondi à 2 décimales
    return {
        "username": target_user["alias"],
        "presentiel": round(result["presentiel"] / 3600, 2),
        "télétravail": round(result["télétravail"] / 3600, 2),
        "total": round(result["total"] / 3600, 2),
    }


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
