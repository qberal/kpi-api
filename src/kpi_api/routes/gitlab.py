"""
Fonctions pour récupérer et traiter les données de l'API GitLab.
"""

from collections import defaultdict
from datetime import datetime, timedelta

import pytz
import re
import aiohttp

from kpi_api.utils.pagination import fetch_gitlab_paginated_data
from kpi_api.utils.config import ACCESS_TOKEN


async def fetch_time_spent_by_user(group_path: str, created_after: str) -> dict:
    """
    Récupère et calcule le temps passé par utilisateur à partir de l'API GitLab.
    """
    query = """
    query timeSpentByUser($groupPath: ID!, $createdAfter: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, first: 100, after: $after) {
          nodes {
            timelogs(first: 100) {
              nodes {
                timeSpent
                user {
                  name
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {"groupPath": group_path, "createdAfter": created_after}
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Agréger le temps par utilisateur
    time_by_user = defaultdict(int)
    for issue in issues:
        for timelog in issue.get("timelogs", {}).get("nodes", []):
            username = timelog["user"]["name"]
            time_by_user[username] += timelog["timeSpent"]

    # format tableau : user | temps

    res = []
    for user in time_by_user:
        res.append({
            "user": user,
            "time": time_by_user[user] / 3600
        })
    return res


async def fetch_opened_closed_tasks(group_path, created_after, created_before) -> dict:
    """
    Récupère et calcule le nombre d'issues ouvertes et fermées par jour à partir de l'API GitLab.
    :param group_path:
    :param created_after:
    :param created_before:
    :return:
    """

    query = """
    query issuesByDate($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            createdAt
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before
    }

    # Récupération des données paginées
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Calculer le nombre d'issues ouvertes et fermées par jour
    opened_by_day = defaultdict(int)
    closed_by_day = defaultdict(int)

    for issue in issues:
        created_date = issue.get("createdAt")
        closed_date = issue.get("closedAt")

        if created_date:
            created_day = created_date[:10]  # Extraire la date (YYYY-MM-DD)
            opened_by_day[created_day] += 1

        if closed_date:
            closed_day = closed_date[:10]  # Extraire la date (YYYY-MM-DD)
            closed_by_day[closed_day] += 1

    # res en forme de tableau par jour | fermeture | ouverture

    res = []

    for day in opened_by_day:
        res.append({
            "day": day,
            "opened": opened_by_day[day],
            "closed": closed_by_day.get(day, 0)
        })
    return res

    # return {"opened_by_day": opened_by_day, "closed_by_day": closed_by_day}


async def burndown_chart(group_path, created_after, created_before) -> dict:
    """
    Récupère et calcule le nombre d'issues ouvertes et fermées par jour à partir de l'API GitLab.
    :param group_path:
    :param created_after:
    :param created_before:
    :return:
    """

    query = """
    query issuesByDate($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            createdAt
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before
    }

    # Récupération des données paginées
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Calculer le nombre d'issues ouvertes et fermées par jour
    opened_by_day = defaultdict(int)
    closed_by_day = defaultdict(int)

    for issue in issues:
        created_date = issue.get("createdAt")
        closed_date = issue.get("closedAt")

        if created_date:
            created_day = created_date[:10]  # Extraire la date (YYYY-MM-DD)
            opened_by_day[created_day] += 1

        if closed_date:
            closed_day = closed_date[:10]  # Extraire la date (YYYY-MM-DD)
            closed_by_day[closed_day] += 1

    # created before - created after sont en ISO
    start_date = datetime.fromisoformat(created_after)
    end_date = datetime.fromisoformat(created_before)
    current_date = start_date
    remaining_issues = 0
    remaining_by_day = []
    days = []

    while current_date <= end_date:
        day_str = current_date.strftime("%Y-%m-%d")
        remaining_issues += opened_by_day.get(day_str, 0)
        remaining_issues -= closed_by_day.get(day_str, 0)
        remaining_by_day.append(remaining_issues)
        days.append(day_str)
        current_date += timedelta(days=1)

    # Ligne idéale de burndown (doit commencer à remaining_by_day[0], être linéaire et atteindre 0 à la fin)
    ideal_burndown = [remaining_by_day[0] - i * (remaining_by_day[0] / (len(days) - 1)) for i in range(len(days))]
    closed_by_day = [closed_by_day.get(day, 0) for day in days]

    res = []
    for i in range(len(days)):
        res.append({
            "day": days[i],
            "remaining": remaining_by_day[i],
            "ideal": ideal_burndown[i],
            "done": closed_by_day[i]
        })

    print(res)
    return res


async def resolve_time(group_path: str, created_after: str, created_before) -> dict:
    """
    Récupère et calcule le temps de résolution des issues à partir de l'API GitLab.
    :param group_path:
    :param created_after:
    :param created_before:
    :return:
    """
    # Requête GraphQL modifiée pour récupérer les dates de création et clôture
    resolution_query = """
    query resolutionTime($groupPath: ID!, $closedAfter: Time, $closedBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(
          closedAfter: $closedAfter
          closedBefore: $closedBefore
          first: 100
          after: $after
        ) {
          nodes {
            createdAt
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "closedAfter": created_after,
        "closedBefore": created_before
    }

    # Récupération des données
    closed_issues = await fetch_gitlab_paginated_data(resolution_query, variables, key_path=["data", "group", "issues"])

    # Calcul des délais de résolution
    resolution_times = []

    for issue in closed_issues:
        if not issue.get('closedAt') or not issue.get('createdAt'):
            continue

        # Conversion des dates en format datetime
        try:
            created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
            closed = datetime.fromisoformat(issue['closedAt'].replace('Z', '+00:00'))
        except ValueError:
            continue

        # Calcul du délai en jours
        delta = closed - created
        if delta.total_seconds() <= 0:
            continue  # Élimine les valeurs négatives ou nulles

        resolution_times.append(delta.days + delta.seconds / (3600 * 24))

    res = []
    for i in range(len(resolution_times)):
        res.append({
            "time": resolution_times[i]
        })

    return res


async def resolve_time_mean(group_path: str, created_after: str, created_before) -> dict:
    """
    Récupère et calcule le temps de résolution moyen des issues à partir de l'API GitLab.
    :param group_path:
    :param created_after:
    :param created_before:
    :return:
    """
    # Requête GraphQL modifiée pour récupérer les dates de création et clôture
    resolution_query = """
    query resolutionTime($groupPath: ID!, $closedAfter: Time, $closedBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(
          closedAfter: $closedAfter
          closedBefore: $closedBefore
          first: 100
          after: $after
        ) {
          nodes {
            createdAt
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "closedAfter": created_after,
        "closedBefore": created_before
    }

    # Récupération des données
    closed_issues = await fetch_gitlab_paginated_data(resolution_query, variables, key_path=["data", "group", "issues"])

    # Calcul des délais de résolution
    resolution_times = []

    for issue in closed_issues:
        if not issue.get('closedAt') or not issue.get('createdAt'):
            continue

        # Conversion des dates en format datetime
        try:
            created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
            closed = datetime.fromisoformat(issue['closedAt'].replace('Z', '+00:00'))
        except ValueError:
            continue

        # Calcul du délai en jours
        delta = closed - created
        if delta.total_seconds() <= 0:
            continue  # Élimine les valeurs négatives ou nulles

        resolution_times.append(delta.days + delta.seconds / (3600 * 24))

    # Calcul des statistiques
    mean = sum(resolution_times) / len(resolution_times) if resolution_times else 0

    return mean


async def temps_passe_par_wp(group_path: str, created_after: str) -> dict:
    """
    Récupère et calcule le temps passé par utilisateur à partir de l'API GitLab.
    """
    query = """
    query timeSpentByWP($groupPath: ID!, $createdAfter: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, first: 100, after: $after) {
          nodes {
            labels {
              nodes {
                title
              }
            }
            timelogs(first: 100) {
              nodes {
                timeSpent
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    # Variables pour la requête
    variables = {
        "groupPath": group_path,
        "createdAfter": created_after
    }

    # Récupération des données
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Calculer le temps par work package
    time_by_wp = defaultdict(int)

    for issue in issues:
        # Récupérer les labels de l'issue
        labels = issue.get("labels", {}).get("nodes", [])
        wp_labels = [label["title"] for label in labels if label["title"].startswith("WP")]

        # Ajouter le temps passé pour chaque WP
        for timelog in issue.get("timelogs", {}).get("nodes", []):
            time_spent = timelog["timeSpent"]
            for wp in wp_labels:
                time_by_wp[wp] += time_spent

    # Convertir les secondes en heures
    time_by_wp_hours = {wp: time / 3600 for wp, time in time_by_wp.items()}

    # enlever WP:: de chaque wp (oneliner)
    time_by_wp_hours = {wp.replace("WP::", ""): time for wp, time in time_by_wp_hours.items()}

    res = []
    for wp in time_by_wp_hours:
        res.append({
            "wp": wp,
            "time": time_by_wp_hours[wp]
        })

    return res


async def fetch_burnup_data(group_path: str, start_date: str, end_date: str) -> list:
    """
    Récupère les données pour le burnup chart : total issues et issues fermées par jour.
    """
    query = """
    query burnupData($groupPath: ID!, $createdAfter: Time, $createdBefore: Time) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100) {
          nodes {
            createdAt
            closedAt
          }
        }
      }
    }
    """

    # Variables pour l'API
    variables = {"groupPath": group_path, "createdAfter": start_date, "createdBefore": end_date}
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Organiser les issues par jour
    created_issues = defaultdict(int)
    closed_issues = defaultdict(int)

    for issue in issues:
        created_date = issue["createdAt"][:10]
        created_issues[created_date] += 1

        if issue["closedAt"]:
            closed_date = issue["closedAt"][:10]
            closed_issues[closed_date] += 1

    # Générer le tableau cumulé
    current_date = datetime.fromisoformat(start_date)
    end_date = datetime.fromisoformat(end_date)
    total_issues = 0
    issues_closed = 0
    burnup_data = []

    while current_date <= end_date:
        day_str = current_date.strftime("%Y-%m-%d")
        total_issues += created_issues[day_str]
        issues_closed += closed_issues[day_str]
        burnup_data.append({
            "day": day_str,
            "total_issues": total_issues,
            "issues_closed": issues_closed
        })
        current_date += timedelta(days=1)

    return burnup_data


async def fetch_issues_summary(group_path: str, created_after: str, created_before: str) -> dict:
    """
    Récupère un résumé des issues par statut : Completed, Incomplete, et Unstarted,
    basé sur les tags spécifiques et dans une plage de dates donnée.
    """
    query = """
    query issuesSummary($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            state
            labels(first: 10) {
              nodes {
                title
              }
            }
            createdAt
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before,
    }
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Compter les issues par statut
    completed = 0
    incomplete = 0
    unstarted = 0

    for issue in issues:
        labels = [label["title"] for label in issue.get("labels", {}).get("nodes", [])]

        if issue["state"] == "closed":
            completed += 1
        elif "Etat::En cours" in labels or "Etat::À vérifier" in labels:
            incomplete += 1
        elif "Etat::À faire" in labels or not labels:
            unstarted += 1

    total = completed + incomplete + unstarted

    return {
        "completed": completed / total * 100,
        "incomplete": incomplete / total * 100,
        "unstarted": unstarted / total * 100
    }


async def fetch_open_issues_count_by_user(group_path: str, created_after: str, created_before: str) -> dict:
    """
    Récupère le nombre total d'issues ouvertes par utilisateur.
    """
    query = """
    query openIssuesByUser($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after, state: opened) {
          nodes {
            assignees(first: 10) {
              nodes {
                name
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before,
    }
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Initialiser les données par utilisateur
    issues_by_user = defaultdict(int)

    for issue in issues:
        assignees = [assignee["name"] for assignee in issue.get("assignees", {}).get("nodes", [])]

        # Ajouter au compte des utilisateurs assignés
        for user in assignees:
            issues_by_user[user] += 1

    return [{"user": user, "count": count} for user, count in issues_by_user.items()]


async def fetch_late_issues_summary(group_path: str, created_after: str, created_before: str) -> dict:
    """
    Récupère le nombre total d'issues et celles en retard
    dans une plage de dates donnée.
    """
    query = """
    query issuesSummary($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            state
            dueDate
            closedAt
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before,
    }
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    total = len(issues)
    late = 0

    # Définir le fuseau horaire UTC
    utc = pytz.utc
    current_date = datetime.utcnow().replace(tzinfo=utc)  # Normaliser en UTC

    for issue in issues:
        due_date = issue.get("dueDate")
        closed_at = issue.get("closedAt")
        state = issue.get("state")

        if due_date:
            # Convertir dueDate en objet datetime avec fuseau horaire UTC
            due_date = datetime.fromisoformat(due_date)
            if due_date.tzinfo is None:  # Ajouter UTC si due_date est naïve
                due_date = due_date.replace(tzinfo=utc)

            # Critère 1 : Non fermée et dueDate < aujourd'hui
            if state != "closed" and due_date < current_date:
                late += 1

            # Critère 2 : Fermée mais dueDate < closedAt
            elif state == "closed" and closed_at:
                closed_at = datetime.fromisoformat(closed_at)
                if closed_at.tzinfo is None:  # Ajouter UTC si closed_at est naïve
                    closed_at = closed_at.replace(tzinfo=utc)
                if due_date < closed_at:
                    late += 1

    return {
        "late": late / total * 100,
        "not late": (total - late) / total * 100
    }


def format_duration(seconds: int) -> str:
    """
    Convertit un nombre de secondes en une chaîne au format 'xxhxxmin'.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h{minutes:02d}min"


async def weekly_activity_report(group_path: str, created_after: str, created_before: str) -> dict:
    """
    Génère un compte rendu d'activité hebdomadaire, regroupé par personne.

    Pour chaque issue créée entre 'created_after' et 'created_before', la fonction récupère :
      - l'iid de l'issue (identifiant visible)
      - le titre de l'issue (nom issue)
      - le tag WP : si un label commence par "WP::", la valeur après "WP::" est extraite, sinon vide.
      - pour chaque utilisateur, le temps passé total (la somme des timelogs de cet utilisateur)
      - le temps restant estimé (timeEstimate - somme de tous les timelogs de l'issue)

    Seules les entrées pour lesquelles le temps passé par l'utilisateur est > 0 sont incluses.
    Le temps est formaté au format 'xxhxxmin'.

    :param group_path: Chemin complet du groupe GitLab.
    :param created_after: Date de début (format ISO) de la période.
    :param created_before: Date de fin (format ISO) de la période.
    :return: Un dictionnaire dont les clés sont les noms d'utilisateurs et les valeurs sont
             des listes de dictionnaires correspondant aux issues.
    """
    query = """
    query weeklyActivityReport($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            iid
            title
            timeEstimate
            labels(first: 10) {
              nodes {
                title
              }
            }
            timelogs(first: 100) {
              nodes {
                timeSpent
                user {
                  name
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before
    }

    # Récupération paginée des issues via la fonction utilitaire
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Dictionnaire pour regrouper les informations par utilisateur
    report_by_user = defaultdict(list)

    for issue in issues:
        issue_iid = issue.get("iid")
        issue_title = issue.get("title")
        time_estimate = issue.get("timeEstimate") or 0

        # Extraction du tag WP
        wp = ""
        labels = issue.get("labels", {}).get("nodes", [])
        for label in labels:
            label_title = label.get("title", "")
            if label_title.startswith("WP::"):
                # Récupère ce qui suit "WP::" et supprime d'éventuels espaces
                wp = label_title.split("WP::", 1)[1].strip()
                break

        # Calcul du temps total passé sur l'issue (tous utilisateurs confondus)
        timelogs = issue.get("timelogs", {}).get("nodes", [])
        total_time_spent_issue = sum(tl.get("timeSpent", 0) for tl in timelogs)
        # Calcul du temps restant estimé (pour l'issue)
        remaining = time_estimate - total_time_spent_issue
        if remaining < 0:
            remaining = 0

        # Regroupement des timelogs par utilisateur pour cette issue
        user_time = defaultdict(int)
        for tl in timelogs:
            user = tl.get("user", {}).get("name")
            if user:
                user_time[user] += tl.get("timeSpent", 0)

        # Pour chaque utilisateur ayant logué du temps (> 0), on ajoute une entrée dans le rapport
        for user, user_time_spent in user_time.items():
            if user_time_spent > 0:
                report_by_user[user].append({
                    "iid": issue_iid,
                    "nom issue": issue_title,
                    "WP": wp,
                    "temps passé total": format_duration(user_time_spent),
                    "temps restant estimé": format_duration(remaining)
                })

    return dict(report_by_user)


async def weekly_activity_report_by_user_old(group_path: str, week_start: str, week_end: str,
                                             target_username: str) -> dict:
    """
    Génère un compte rendu d'activité hebdomadaire pour un utilisateur spécifique en se basant
    sur la date de log des timelogs (plutôt que sur la date de création des issues).

    Pour chaque issue, pour chaque timelog :
      - Si le timelog appartient à target_username et que sa date (spentAt) se situe dans la plage
        [week_start, week_end], on additionne le temps passé.
      - Pour l'issue, on calcule également le temps restant estimé (timeEstimate - somme de tous les timelogs).

    :param group_path: Chemin complet du groupe GitLab.
    :param week_start: Date de début de la semaine (format ISO).
    :param week_end: Date de fin de la semaine (format ISO).
    :param target_username: Nom d'utilisateur GitLab ciblé.
    :return: Un dictionnaire avec pour clé le nom de l'utilisateur et la valeur une liste de dictionnaires
             correspondant aux issues travaillées durant la semaine.
    """
    query = """
    query weeklyActivityReport($groupPath: ID!, $after: String) {
      group(fullPath: $groupPath) {
        issues(first: 100, after: $after) {
          nodes {
            iid
            title
            timeEstimate
            labels(first: 10) {
              nodes {
                title
              }
            }
            timelogs(first: 100) {
              nodes {
                timeSpent
                spentAt  # Champ à récupérer pour connaître la date du timelog
                user {
                  name
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    variables = {"groupPath": group_path}

    # Récupération paginée des issues
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    # Convertir les bornes de la semaine en objets datetime
    week_start_dt = datetime.fromisoformat(week_start)
    week_end_dt = datetime.fromisoformat(week_end)

    report_for_user = []

    for issue in issues:
        issue_iid = issue.get("iid")
        issue_title = issue.get("title")
        time_estimate = issue.get("timeEstimate") or 0

        # Extraction du tag WP (si présent)
        wp = ""
        labels = issue.get("labels", {}).get("nodes", [])
        for label in labels:
            label_title = label.get("title", "")
            if label_title.startswith("WP::"):
                wp = label_title.split("WP::", 1)[1].strip()
                break

        timelogs = issue.get("timelogs", {}).get("nodes", [])
        user_time_spent = 0
        total_time_spent_issue = 0

        for tl in timelogs:
            time_spent = tl.get("timeSpent", 0)
            total_time_spent_issue += time_spent
            tl_user = tl.get("user", {}).get("name", "")
            spent_at = tl.get("spentAt")
            if spent_at:
                try:
                    tl_date = datetime.fromisoformat(spent_at)
                except ValueError:
                    # Si le format de la date n'est pas conforme, on ignore ce timelog
                    continue

                # On vérifie si le timelog se situe dans la période de la semaine
                if week_start_dt <= tl_date <= week_end_dt:
                    # Comparaison insensible aux espaces et à la casse
                    if tl_user.strip().lower() == target_username.strip().lower():
                        user_time_spent += time_spent

        # On ajoute l'issue au rapport seulement si l'utilisateur a logué du temps pendant la semaine
        if user_time_spent > 0:
            remaining = time_estimate - total_time_spent_issue
            if remaining < 0:
                remaining = 0

            report_for_user.append({
                "iid": issue_iid,
                "nom issue": issue_title,
                "WP": wp,
                "temps passé total": format_duration(user_time_spent),
                "temps restant estimé": format_duration(remaining)
            })

    return {target_username: report_for_user}




GITLAB_BASE_URL = "https://gitlab.insa-rouen.fr/api/v4"


async def get_parent_issue(project_id: int, parent_iid: int) -> dict:
    """
    Récupère l'issue parente en utilisant l'API REST de GitLab.

    :param project_id: ID du projet GitLab contenant l'issue parente.
    :param parent_iid: IID de l'issue parente.
    :return: Un dictionnaire contenant l'IID, le titre et le WP de l'issue parente.
    """
    url = f"{GITLAB_BASE_URL}/projects/{project_id}/issues/{parent_iid}"
    headers = {"PRIVATE-TOKEN": ACCESS_TOKEN}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                parent_issue = await response.json()

                # Récupérer le WP du parent si présent
                parent_wp = ""
                parent_labels = parent_issue.get("labels", [])
                for label in parent_labels:
                    if label.startswith("WP::"):
                        parent_wp = label.split("WP::", 1)[1].strip()
                        break

                return {
                    "iid": parent_issue.get("iid"),
                    "title": parent_issue.get("title"),
                    "wp": parent_wp
                }

    return {}


async def weekly_activity_report_by_user(group_path: str, created_after: str, created_before: str, target_username: str) -> dict:
    """
    Génère un rapport d'activité hebdomadaire pour un utilisateur.

    - Récupère les discussions pour identifier le parent d'une tâche (`TASK`).
    - Utilise une requête GraphQL auxiliaire pour récupérer l'issue parente avec `project_id` et `iid`.
    - Récupère le label WP du parent si l'issue est une tâche.
    - Formatage correct :
        - ID : "parent_iid#task_iid"
        - Titre : "parent_title : task_title"

    :param group_path: Chemin GitLab (ex: 'iti/pic/25/chb').
    :param created_after: Date de début (format ISO).
    :param created_before: Date de fin (format ISO).
    :param target_username: Nom d'utilisateur GitLab.
    :return: Un dictionnaire structuré par utilisateur.
    """
    query = """
    query weeklyActivityReport($groupPath: ID!, $createdAfter: Time, $createdBefore: Time, $after: String) {
      group(fullPath: $groupPath) {
        issues(createdAfter: $createdAfter, createdBefore: $createdBefore, first: 100, after: $after) {
          nodes {
            iid
            title
            type
            timeEstimate
            projectId
            labels(first: 10) {
              nodes {
                title
              }
            }
            timelogs(first: 100) {
              nodes {
                timeSpent
                spentAt
                user {
                  name
                }
              }
            }
            discussions(first: 1) {
              nodes {
                notes(first: 1) {
                  nodes {
                    body
                  }
                }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    variables = {
        "groupPath": group_path,
        "createdAfter": created_after,
        "createdBefore": created_before
    }

    # 🔹 Étape 1 : Récupération des issues et des tâches
    issues = await fetch_gitlab_paginated_data(query, variables, key_path=["data", "group", "issues"])

    report_for_user = []

    for issue in issues:
        issue_iid = issue.get("iid")
        issue_title = issue.get("title")
        issue_type = issue.get("type")  # Vérifier si c'est une TASK
        project_id = issue.get("projectId")  # Identifier le projet
        time_estimate = issue.get("timeEstimate") or 0

        # Extraction du tag WP
        wp = ""
        labels = issue.get("labels", {}).get("nodes", [])
        for label in labels:
            label_title = label.get("title", "")
            if label_title.startswith("WP::"):
                wp = label_title.split("WP::", 1)[1].strip()
                break

        timelogs = issue.get("timelogs", {}).get("nodes", [])
        user_time_spent = 0
        total_time_spent_issue = 0

        for tl in timelogs:
            time_spent = tl.get("timeSpent", 0)
            total_time_spent_issue += time_spent
            tl_user = tl.get("user", {}).get("name", "")
            if tl_user.strip().lower() == target_username.strip().lower():
                user_time_spent += time_spent

        if user_time_spent > 0:
            parent_iid = None
            parent_title = None
            parent_wp = None

            # 🔹 Étape 2 : Vérifier si l’issue est une tâche avec un parent
            if issue_type == "TASK":
                discussions = issue.get("discussions", {}).get("nodes", [])
                if discussions:
                    notes = discussions[0].get("notes", {}).get("nodes", [])
                    if notes:
                        first_note = notes[0].get("body", "")
                        match = re.search(r"added #(\d+) as parent issue", first_note)
                        if match:
                            parent_iid = match.group(1)

                            # 🔹 Étape 3 : Récupérer l'issue parente via GraphQL
                            parent_issue = await get_parent_issue(project_id, parent_iid)
                            if parent_issue:
                                parent_title = parent_issue.get("title")
                                parent_wp = parent_issue.get("wp")

            # 🔹 Étape 4 : Formater l'affichage
            if parent_iid and parent_title:
                display_iid = f"{parent_iid}#{issue_iid}"
                display_title = f"{parent_title} : {issue_title}"
                wp = parent_wp if parent_wp else wp  # Prendre le WP du parent si disponible
            else:
                display_iid = issue_iid
                display_title = issue_title

            remaining = time_estimate - total_time_spent_issue
            if remaining < 0:
                remaining = 0

            report_for_user.append({
                "iid": display_iid,
                "nom issue": display_title,
                "WP": wp,
                "temps passé total": format_duration(user_time_spent),
                "temps restant estimé": format_duration(remaining)
            })

    return {target_username: report_for_user}

