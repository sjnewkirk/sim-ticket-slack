import os
import logging
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# --- Setup ---
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)


# --- Event subscription handler (emoji triggers modal) ---
@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    logging.debug(f"Incoming event: {data}")

    # Handle Slack's URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # Handle actual events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        logging.debug(f"Event payload: {event}")

        # Reaction event trigger
        if event.get("type") == "reaction_added" and event.get("reaction") == "ticket":
            user_id = event.get("user")
            channel_id = event["item"]["channel"]

            try:
                # Open modal
                response = client.views_open(
                    trigger_id=event.get("item_user"),  # ⚠️ might need fixing, see note below
                    view={
                        "type": "modal",
                        "callback_id": "sim_ticket_modal",
                        "title": {"type": "plain_text", "text": "Create SIM Ticket"},
                        "submit": {"type": "plain_text", "text": "Submit"},
                        "blocks": [
                            {
                                "type": "input",
                                "block_id": "ticket_summary",
                                "label": {"type": "plain_text", "text": "Summary"},
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "summary_input"
                                }
                            },
                            {
                                "type": "input",
                                "block_id": "ticket_priority",
                                "label": {"type": "plain_text", "text": "Priority"},
                                "element": {
                                    "type": "static_select",
                                    "action_id": "priority_select",
                                    "options": [
                                        {"text": {"type": "plain_text", "text": "Low"}, "value": "low"},
                                        {"text": {"type": "plain_text", "text": "Medium"}, "value": "medium"},
                                        {"text": {"type": "plain_text", "text": "High"}, "value": "high"},
                                    ],
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "ticket_description",
                                "label": {"type": "plain_text", "text": "Description"},
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "description_input",
                                    "multiline": True
                                }
                            },
                            {
                                "type": "input",
                                "block_id": "ticket_owner",
                                "label": {"type": "plain_text", "text": "Owner"},
                                "element": {
                                    "type": "users_select",
                                    "action_id": "owner_select"
                                }
                            },
                            {
                                "type": "input",
                                "block_id": "ticket_due_date",
                                "label": {"type": "plain_text", "text": "Due Date"},
                                "element": {
                                    "type": "datepicker",
                                    "action_id": "due_date_input"
                                }
                            }
                        ]
                    }
                )
                logging.debug(f"Modal open response: {response}")

            except SlackApiError as e:
                logging.error(f"Error opening modal: {e.response['error']}")

    return "", 200


# --- Interaction handler (modal submit) ---
@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    payload = request.form.get("payload")
    logging.debug(f"Interaction payload raw: {payload}")

    if not payload:
        return "", 400

    import json
    data = json.loads(payload)
    logging.debug(f"Parsed interaction payload: {data}")

    # Handle modal submission
    if data.get("type") == "view_submission":
        values = data["view"]["state"]["values"]
        summary = values["ticket_summary"]["summary_input"]["value"]
        priority = values["ticket_priority"]["priority_select"]["selected_option"]["value"]
        description = values["ticket_description"]["description_input"]["value"]
        owner = values["ticket_owner"]["owner_select"]["selected_user"]
        due_date = values["ticket_due_date"]["due_date_input"]["selected_date"]

        logging.info(f"Ticket submission received: {summary}, {priority}, {description}, {owner}, {due_date}")

        # Example: post confirmation back to user
        try:
            client.chat_postMessage(
                channel=data["user"]["id"],
                text=f"✅ Ticket created!\n*Summary:* {summary}\n*Priority:* {priority}\n*Owner:* <@{owner}>\n*Due:* {due_date}\n*Description:* {description}"
            )
        except SlackApiError as e:
            logging.error(f"Error posting confirmation: {e.response['error']}")

        return jsonify({"response_action": "clear"})

    return "", 200


# --- Run server ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
