from flask import Flask, request, jsonify

# 1️⃣ Create the app object FIRST
app = Flask(__name__)

# 2️⃣ Define routes after app exists
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.form  # Slash commands come in form-encoded
    user_id = data.get("user_id")
    text = data.get("text")
    response_url = data.get("response_url")

    return jsonify({
        "response_type": "in_channel",
        "text": f"Slash command received from <@{user_id}> with text: {text}"
    })

# 3️⃣ Optional local run
if __name__ == "__main__":
    app.run(debug=True)
