import os
import json
from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from urllib.parse import quote_plus
from flask import jsonify

app = Flask(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

#Slack URL reroute
@app.route("/slack/oauth_redirect", methods=["GET"])
def slack_oauth_redirect():
    return "Slack redirect OK", 200

# Health check
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

from flask import Flask, request, jsonify

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # This handles Slack's URL verification during setup
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # Handle actual events after verification
    if data.get("type") == "event_callback":
        event = data.get("event", {})

        # Example: handle :ticket: emoji reaction
        if event.get("type") == "reaction_added" and event.get("reaction") == "ticket":
            trigger_id = event["user"]
            channel_id = event["item"]["channel"]
            message_ts = event["item"]["ts"]

            # Call a function to open your modal
            open_sim_ticket_modal(trigger_id, channel_id, message_ts)

    return "", 200


# Modal submission
@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    payload = json.loads(request.form.get("payload"))

    if payload.get("type") == "view_submission" and payload["view"]["callback_id"] == "sim_ticket_modal":
        values = payload["view"]["state"]["values"]
        user = payload["user"]["username"]

        # Extract channel + thread from metadata
        metadata = json.loads(payload["view"]["private_metadata"])
        channel_id = metadata["channel_id"]
        thread_ts = metadata.get("thread_ts")

        # Extract form values
        title = values["title_block"]["title_input"]["value"]
        description = values["desc_block"]["desc_input"]["value"]
        system = values["system_block"]["system_input"]["value"]
        workcell = values["workcell_block"]["workcell_input"]["value"]
        cti = values["cti_block"]["cti_input"]["value"]
        severity = values["severity_block"]["severity_input"]["value"]
        test_case = values["test_case_block"]["test_case_input"]["value"]

        # Construct Slack message link
        slack_link = f"https://amazon.enterprise.slack.com/archives/{channel_id}/p{thread_ts.replace('.', '')}" if thread_ts else "unknown"

        # Build SIM ticket URL
        url_title = quote_plus(f"[Atlas>{system}>{workcell} - {test_case}] {title}")
        url_desc = quote_plus(f"{description}\nSlack Message Link: {slack_link}")
        sim_url = (
            f"https://t.corp.amazon.com/create/options?"
            f"category=Amazon%20Robotics&type=Vulcan%20Stow&item={cti}&severity={severity}"
            f"&title={url_title}&description={url_desc}&tags={test_case},{system}&watchers={user}@amazon.com"
        )

        # Post in original channel / thread
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,  # None if not a thread
            text=f"<@{user}> submitted a SIM Ticket: <{sim_url}|SIM Ticket>"
        )

    return jsonify({"response_action": "clear"})



if __name__ == "__main__":
    app.run(debug=True)
