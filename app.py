import os
import json
from flask import Flask, request, jsonify
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
from urllib.parse import quote_plus

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

# Slash command
@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    user_id = request.form.get("user_id")
    trigger_id = request.form.get("trigger_id")
    channel_id = request.form.get("channel_id")
    thread_ts = request.form.get("thread_ts")  # optional if command in thread

    # Pass channel + thread info via private_metadata
    private_metadata = json.dumps({"channel_id": channel_id, "thread_ts": thread_ts})

    # Open modal
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "sim_ticket_modal",
            "private_metadata": private_metadata,
            "title": {"type": "plain_text", "text": "Create SIM Ticket"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                # Title
                {"type": "input",
                 "block_id": "title_block",
                 "label": {"type": "plain_text", "text": "Title"},
                 "element": {"type": "plain_text_input", "action_id": "title_input"}},
                # Description
                {"type": "input",
                 "block_id": "desc_block",
                 "label": {"type": "plain_text", "text": "Description of Issue"},
                 "element": {"type": "plain_text_input", "action_id": "desc_input", "multiline": True}},
                # System Issue Observed On
                {"type": "input",
                 "block_id": "system_block",
                 "label": {"type": "plain_text", "text": "System Issue Observed On"},
                 "element": {
                     "type": "static_select",
                     "action_id": "system_input",
                     "options": [{"text": {"type": "plain_text", "text": x}, "value": x} for x in ["0202","0204","0301","0304"]]
                 }},
                # Workcell
                {"type": "input",
                 "block_id": "workcell_block",
                 "label": {"type": "plain_text", "text": "Workcell"},
                 "element": {
                     "type": "static_select",
                     "action_id": "workcell_input",
                     "options": [{"text": {"type": "plain_text", "text": x}, "value": x} for x in ["Induct","WC1","WC2","WC3","ALL"]]
                 }},
                # CTI
                {"type": "input",
                 "block_id": "cti_block",
                 "label": {"type": "plain_text", "text": "CTI"},
                 "element": {
                     "type": "static_select",
                     "action_id": "cti_input",
                     "options": [{"text": {"type": "plain_text", "text": x}, "value": x} for x in [
                         "Controls","Deployment","Hardware","Match","Motion","Network","Observability",
                         "Orchestrator","Perception","Software","UI","UWC"
                     ]]
                 }},
                # Ticket Severity
                {"type": "input",
                 "block_id": "severity_block",
                 "label": {"type": "plain_text", "text": "Ticket Severity Level"},
                 "element": {
                     "type": "static_select",
                     "action_id": "severity_input",
                     "options": [{"text": {"type": "plain_text", "text": x}, "value": x} for x in ["THREE","FOUR","FIVE"]]
                 }},
                # Test Case
                {"type": "input",
                 "block_id": "test_case_block",
                 "label": {"type": "plain_text", "text": "Test Case"},
                 "element": {
                     "type": "static_select",
                     "action_id": "test_case_input",
                     "options": [{"text": {"type": "plain_text", "text": x}, "value": x} for x in ["Daily_QA","KPI_Benchmark","Capability_Test"]]
                 }},
            ]
        }
    )

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

    return "", 200


if __name__ == "__main__":
    app.run(debug=True)
