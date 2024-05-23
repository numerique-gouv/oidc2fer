import json
import os

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect


@pytest.fixture(scope="session")
def browser_context_args():
    return {"locale": "fr-FR"}


def renater_test_idp(page):
    page.get_by_label("Nom d'utilisateur").fill("etudiant1")
    page.get_by_label("Mot de passe").fill("etudiant1")
    page.get_by_label("Afficher les informations qui vont être transférées").check()
    page.get_by_role("button", name="Connexion").click()
    page.get_by_role("button", name="Accepter").click()


def renater_wayf(page):
    page.get_by_text("Veuillez sélectionner").click()
    page.get_by_role("option", name="GIP RENATER - IdP de test", exact=True).click()
    page.get_by_role("button", name="Sélection").click()


def oidc_to_renater(context: BrowserContext):
    with context.new_page() as page:
        page.goto("https://oidc-test-client.traefik.me")
        renater_wayf(page)
        renater_test_idp(page)

        expect(page.locator("pre")).to_contain_text('"usual_name":"Dupont"')
        text = page.inner_text("pre")
        result = json.loads(text)

    id_token = result["access_token_response"]["id_token"]
    assert {"acr": "eidas1"}.items() <= id_token.items()
    userinfo = result["userinfo"]
    assert {
        "email": "jean.dupont@formation.renater.fr",
        "given_name": "Jean",
        "uid": "etudiant1@test-renater.fr",
        "usual_name": "Dupont",
    }.items() <= userinfo.items()
    return id_token


@pytest.mark.skipif(
    "TEST_E2E" not in os.environ, reason="Depends on app running locally"
)
def test_oidc_to_renater(browser: Browser):
    id_token1 = oidc_to_renater(browser.new_context())
    id_token2 = oidc_to_renater(browser.new_context())

    assert id_token1["sub"] == id_token2["sub"]


def agent_connect_login(page: Page):
    page.goto("https://fsa1v2.integ01.dev-agentconnect.fr/")
    page.get_by_label("Connexion à AgentConnect").click()
    page.get_by_label("Email professionnel").fill("jean.dupont@formation.renater.fr")
    page.get_by_test_id("interaction-connection-button").click()


def agent_connect_to_renater(context: BrowserContext):
    with context.new_page() as page:
        agent_connect_login(page)
        renater_wayf(page)
        renater_test_idp(page)

        expect(page.locator("body")).to_contain_text("jean.dupont@formation.renater.fr")
        text = page.inner_text("#json")
        result = json.loads(text)
        assert {
            "email": "jean.dupont@formation.renater.fr",
            "given_name": "Jean",
            "uid": "etudiant1@test-renater.fr",
            "usual_name": "Dupont",
        }.items() <= result.items()
        return result


@pytest.mark.skipif(
    "TEST_E2E_AC" not in os.environ, reason="Depends on staging deployment"
)
def test_agent_connect_to_renater(browser: Browser):
    result1 = agent_connect_to_renater(browser.new_context())
    result2 = agent_connect_to_renater(browser.new_context())

    assert result1["sub"] == result2["sub"]
