from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client['webhook_db']
collection = db['webhook_data']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    try:
        # Detect action type (push, pull_request, etc.)
        action_type = data.get('action', 'PUSH').upper()

        # Get author from pusher or sender
        author = data.get('pusher', {}).get('name') or data.get('sender', {}).get('login')

        # Determine from_branch for push and pull_request events
        ref = data.get('ref', '')
        from_branch = ""
        if 'pull_request' in data:
            from_branch = data['pull_request'].get('head', {}).get('ref', '')
        elif ref:
            from_branch = ref.split('/')[-1]

        # Get destination branch
        to_branch = data.get('pull_request', {}).get('base', {}).get('ref') or "main"

        # UTC timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Unique request ID (for push: after commit SHA; for PR: pull request ID)
        request_id = data.get('after') or data.get('pull_request', {}).get('id')

        # Document to insert
        doc = {
            "request_id": request_id,
            "author": author,
            "action": action_type,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp
        }

        collection.insert_one(doc)
        return jsonify({"msg": "Webhook received", "status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/data', methods=['GET'])
def get_data():
    latest = collection.find().sort("timestamp", -1).limit(5)
    return jsonify([
        {
            "author": doc.get("author", "N/A"),
            "action": doc.get("action", "N/A"),
            "from": doc.get("from_branch", "N/A"),
            "to": doc.get("to_branch", "N/A"),
            "timestamp": doc.get("timestamp", "")
        }
        for doc in latest
    ])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
