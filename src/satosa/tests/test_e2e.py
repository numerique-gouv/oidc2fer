import json
import os

import pytest
from playwright.sync_api import Browser, Page, expect


@pytest.fixture(scope="session")
def browser_context_args():
    return {"locale": "fr-FR"}


def renater_test_idp(page, login):
    page.get_by_label("Nom d'utilisateur").fill(login)
    page.get_by_label("Mot de passe").fill(login)
    page.get_by_label("Afficher les informations qui vont être transférées").check()
    page.get_by_role("button", name="Connexion").click()
    page.get_by_role("button", name="Accepter").click()


def renater_wayf(page):
    page.get_by_text("Veuillez sélectionner").click()
    page.get_by_role("option", name="GIP RENATER - IdP de test", exact=True).click()
    page.get_by_role("button", name="Sélection").click()


def oidc_to_renater(
    page: Page,
    login="enseignant1",
    expected_email="georges.grospieds@formation.renater.fr",
    expected_given_name="Georges",
    expected_usual_name="Grospieds",
):
    page.goto("https://oidc-test-client.traefik.me")
    renater_wayf(page)
    renater_test_idp(page, login=login)

    expect(page.locator("pre")).to_contain_text('"usual_name":')
    text = page.inner_text("pre")
    result = json.loads(text)

    id_token = result["access_token_response"]["id_token"]
    assert {"acr": "eidas1"}.items() <= id_token.items()
    userinfo = result["userinfo"]
    assert {
        "sub": f"{login}@test-renater.fr",
        "uid": f"{login}@test-renater.fr",
        "email": expected_email,
        "given_name": expected_given_name,
        "usual_name": expected_usual_name,
    }.items() <= userinfo.items()
    return id_token


@pytest.mark.skipif(
    "TEST_E2E" not in os.environ, reason="Depends on app running locally"
)
def test_oidc_to_renater_keeps_sub(browser: Browser):
    with browser.new_context().new_page() as page:
        id_token1 = oidc_to_renater(page)
    with browser.new_context().new_page() as page:
        id_token2 = oidc_to_renater(page)

    assert id_token1["sub"] == id_token2["sub"]


@pytest.mark.skipif(
    "TEST_E2E" not in os.environ, reason="Depends on app running locally"
)
def test_oidc_to_renater_student_not_allowed(page: Page):
    page.goto("https://oidc-test-client.traefik.me")
    renater_wayf(page)
    renater_test_idp(page, login="etudiant1")

    expect(page.locator("pre")).to_contain_text('"error":"access_denied"')


def agent_connect_login(page: Page, email):
    page.goto("https://fsa1v2.integ01.dev-agentconnect.fr/")
    page.get_by_label("Connexion à AgentConnect").click()
    page.get_by_label("Email professionnel").fill(email)
    page.get_by_test_id("interaction-connection-button").click()


def agent_connect_to_renater(
    page: Page,
    login="enseignant1",
    expected_email="georges.grospieds@formation.renater.fr",
    expected_given_name="Georges",
    expected_usual_name="Grospieds",
):
    agent_connect_login(page, email=expected_email)
    renater_wayf(page)
    renater_test_idp(page, login=login)

    expect(page.locator("body")).to_contain_text(expected_email)
    text = page.inner_text("#json")
    result = json.loads(text)
    assert {
        "uid": f"{login}@test-renater.fr",
        "email": expected_email,
        "given_name": expected_given_name,
        "usual_name": expected_usual_name,
    }.items() <= result.items()
    return result


@pytest.mark.skipif(
    "TEST_E2E_AC" not in os.environ, reason="Depends on staging deployment"
)
def test_agent_connect_to_renater_keeps_sub(browser: Browser):
    with browser.new_context().new_page() as page:
        result1 = agent_connect_to_renater(page)
    with browser.new_context().new_page() as page:
        result2 = agent_connect_to_renater(page)

    assert result1["sub"] == result2["sub"]


@pytest.mark.skipif(
    "TEST_E2E_AC" not in os.environ, reason="Depends on staging deployment"
)
def test_agent_connect_to_renater_student_not_allowed(page: Page):
    agent_connect_login(page, email="jean.dupont@formation.renater.fr")
    renater_wayf(page)
    renater_test_idp(page, login="etudiant1")

    expect(page.locator("body")).to_contain_text("access_denied")
