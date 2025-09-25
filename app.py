import os
from flask import Flask, request, make_response
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
import json

app = Flask(__name__)

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

@app.route("/slack/command", methods=["POST"])
def handle_command():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)
    return make_response("Command received!", 200)

@app.route("/slack/interactions", methods=["POST"])
def handle_interactions():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("invalid request", 403)
    return make_response("Interaction received!", 200)

if __name__ == "__main__":
    app.run(debug=True)
