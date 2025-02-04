"""Configuration file for the project."""

import os

from dotenv import load_dotenv

load_dotenv()

GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.example.com/api/graphql")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "votre_token_gitlab")

GITLAB_SESSION = os.getenv("GITLAB_SESSION", "votre_cookie_gitlab_session")
GITLAB_KNOWN_SIGN_IN = os.getenv("GITLAB_KNOWN_SIGN_IN", "votre_cookie_known_sign_in")

KIMAI_URL = os.getenv("KIMAI_URL", "https://kimai.example.com/api/")
KIMAI_TOKEN = os.getenv("KIMAI_TOKEN", "votre_token_kimai")

NEXTCLOUD_CALDAV_URL = os.getenv(
    "NEXTCLOUD_CALDAV_URL", "https://nextcloud.example.com/remote.php/dav"
)
NEXTCLOUD_USERNAME = os.getenv("NEXTCLOUD_USERNAME", "votre_nom_utilisateur")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD", "votre_mot_de_passe")
