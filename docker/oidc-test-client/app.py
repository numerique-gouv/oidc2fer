from flask import Flask, jsonify, request, session
from oic.oic import Client
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic import rndstr
from oic.oic.message import RegistrationResponse
from oic.utils.http_util import Redirect
from oic.oic.message import AuthorizationResponse
import secrets
import webbrowser
import threading
import time
import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)
app.config.update(
    {
        "SECRET_KEY": secrets.token_hex(
            10
        ),  # random key so that sessions don't survive restarts
    }
)

client = Client(client_authn_method=CLIENT_AUTHN_METHOD)

provider_info = client.provider_config(os.environ["OIDC_PROVIDER"])

info = {
    "client_id": os.environ["OIDC_CLIENT_ID"],
    "client_secret": os.environ["OIDC_CLIENT_SECRET"],
    "redirect_uris": [f"{os.environ['OIDC_ROOT_URL']}/redirect_uri"],
}
client_reg = RegistrationResponse(**info)
client.store_registration_info(client_reg)


@app.route("/")
def index():
    session["state"] = rndstr()
    session["nonce"] = rndstr()

    auth_req = client.construct_AuthorizationRequest(
        request_args={
            "client_id": client.client_id,
            "response_type": "code",
            "scope": os.environ["OIDC_SCOPES"].split(","),
            "nonce": session["nonce"],
            "redirect_uri": client.registration_response["redirect_uris"][0],
            "state": session["state"],
        }
    )
    login_url = auth_req.request(client.authorization_endpoint)

    return Redirect(login_url)


@app.route("/redirect_uri")
def oidc_callback():
    response = request.query_string.decode("utf-8")
    aresp = client.parse_response(
        AuthorizationResponse, info=response, sformat="urlencoded"
    )

    assert aresp["state"] == session["state"]

    if "error" in aresp:
        return jsonify(
            error_response=aresp.to_dict(),
        )


    code = aresp["code"]
    logging.info("got auth code=%s", code)

    access_token_response = client.do_access_token_request(
        state=aresp["state"],
        request_args={"code": aresp["code"]},
        authn_method="client_secret_post",
    )

    access_token = access_token_response["access_token"]
    logging.info("got access_token=%s", access_token)

    # userinfo = client.do_user_info_request(state=aresp["state"])
    userinfo = client.do_user_info_request(access_token=access_token)

    logging.info("got userinfo=%s", userinfo)

    return jsonify(
        access_token_response=access_token_response.to_dict(), userinfo=userinfo.to_dict()
    )


@app.route("/healthz")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0")

