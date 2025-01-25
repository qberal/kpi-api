"""
Fonctions pour récupérer et traiter les données de l'API GitLab.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from kpi_api.utils.pagination import fetch_gitlab_paginated_data


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
