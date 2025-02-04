"""
Ce module contient les routes permettant de capturer des screenshots de la page d'accueil de GitLab.
"""

import base64

import cv2
import numpy as np
from playwright.async_api import async_playwright

from kpi_api.utils.config import GITLAB_KNOWN_SIGN_IN, GITLAB_SESSION


async def screenshot_issue_board():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # force dark mode
        await page.emulate_media(color_scheme="dark")

        # taille de la fenêtre
        await page.set_viewport_size({"width": 2670, "height": 1800})

        # Définir le cookie d'authentification
        await page.context.add_cookies(
            [
                {
                    "name": "_gitlab_session",  # Nom du cookie utilisé par GitLab
                    "value": GITLAB_SESSION,  # Valeur du cookie
                    "url": "https://gitlab.insa-rouen.fr/",
                },
                {
                    "name": "known_sign_in",  # Nom du cookie utilisé par GitLab
                    "value": GITLAB_KNOWN_SIGN_IN,
                    # Valeur du cookie
                    "url": "https://gitlab.insa-rouen.fr/",
                },
                {
                    "name": "super_sidebar_collapsed",  # Nom du cookie utilisé par GitLab
                    "value": "true",  # Valeur du cookie
                    "url": "https://gitlab.insa-rouen.fr/",
                },
            ]
        )

        await page.goto(
            "https://gitlab.insa-rouen.fr/groups/iti/pic/25/chb/-/boards?iteration_id=Current"
        )

        # text size
        await page.evaluate("document.body.style.zoom=2.0")

        # Attendre que le contenu soit chargé
        await page.wait_for_load_state("networkidle")

        # changer la couleur de fond (--gl-background-color-default : #111217)
        await page.add_style_tag(
            content="body { background-color: #111217 !important; }"
        )

        # Capturer le screenshot
        screenshot_buffer = await page.screenshot(type="png")
        await browser.close()

    # recadrer l'image: enlever 115px du haut de l'image (avec opencv) et 30px de la gauche
    screenshot = cv2.imdecode(np.frombuffer(screenshot_buffer, np.uint8), -1)
    screenshot = screenshot[230:, :]
    screenshot = screenshot[:, 30:]
    _, screenshot_buffer = cv2.imencode(".png", screenshot)

    # Convertir en base64 au lieu de StreamingResponse
    base64_image = base64.b64encode(screenshot_buffer).decode("utf-8")

    return {"screenshot": f"data:image/png;base64,{base64_image}"}
