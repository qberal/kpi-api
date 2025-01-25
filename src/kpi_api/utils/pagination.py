"""
Ce module contient des fonctions utilitaires pour gérer la pagination des requêtes GraphQL.
"""

import requests

from kpi_api.utils.config import ACCESS_TOKEN, GITLAB_URL


async def fetch_gitlab_paginated_data(query: str, variables: dict, key_path: list) -> list:
    """
    Gère la pagination pour les requêtes GraphQL.

    Args:
        query (str): La requête GraphQL.
        variables (dict): Les variables associées à la requête.
        key_path (list): Chemin vers les données paginées dans la réponse (ex. ["data", "group", "issues"]).

    Returns:
        list: Liste des résultats agrégés.
    """
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    all_data = []
    end_cursor = None
    has_next_page = True

    while has_next_page:
        variables["after"] = end_cursor
        response = requests.post(GITLAB_URL, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()

        # Extraire les données selon le chemin spécifié
        data = response.json()
        current_data = data
        for key in key_path:
            current_data = current_data.get(key, {})

        if "nodes" in current_data:
            all_data.extend(current_data["nodes"])

        page_info = current_data.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor", None)

    return all_data
