from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client['webhook_db']
collection = db['webhook_data']

# Home route - renders UI
@app.route('/')
def index():
    return render_template('index.html')

# Webhook route - receives GitHub events
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event', '').lower()

    try:
        # Action type: "PUSH" or "PULL_REQUEST"
        action_type = data.get('action', 'PUSH').upper()
        author = data.get('pusher', {}).get('name') or data.get('sender', {}).get('login')
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Initialize branches
        from_branch = ""
        to_branch = ""

        # Pull Request event
        if event_type == "pull_request":
            from_branch = data.get('pull_request', {}).get('head', {}).get('ref', "")
            to_branch = data.get('pull_request', {}).get('base', {}).get('ref', "")
        
        # Push event
        elif event_type == "push":
            ref = data.get("ref", "")  # e.g. "refs/heads/main"
            to_branch = ref.replace("refs/heads/", "")
            from_branch = "(push)"  # Optional: label to indicate not available

        # Document to insert
        doc = {
            "request_id": data.get('after') or data.get('pull_request', {}).get('id'),
            "author": author,
            "action": action_type,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp
        }

        # Insert into MongoDB
        collection.insert_one(doc)

        return jsonify({"msg": "Webhook received", "status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to fetch latest data for UI
@app.route('/data', methods=['GET'])
def get_data():
    latest = collection.find().sort("timestamp", -1).limit(5)
    return jsonify([{
        "author": doc.get("author", ""),
        "action": doc.get("action", ""),
        "from": doc.get("from_branch", ""),
        "to": doc.get("to_branch", ""),
        "timestamp": doc.get("timestamp", "")
    } for doc in latest])

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5000)