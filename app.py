from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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
        action_type = data.get('action', 'PUSH').upper()
        author = data.get('pusher', {}).get('name') or data.get('sender', {}).get('login')

        # from_branch logic: prioritize pull request head → fallback to ref
        from_branch = ""
        if "pull_request" in data:
            from_branch = data.get('pull_request', {}).get('head', {}).get('ref')
        elif "ref" in data:
            from_branch = data.get('ref', '').split('/')[-1]

        to_branch = data.get('pull_request', {}).get('base', {}).get('ref') or "main"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        doc = {
            "request_id": data.get('after') or data.get('pull_request', {}).get('id'),
            "author": author or "Unknown",
            "action": action_type,
            "from_branch": from_branch or "unknown",
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
    return jsonify([{
        "author": doc.get("author", "N/A"),
        "action": doc.get("action", "N/A"),
        "from": doc.get("from_branch", "N/A"),
        "to": doc.get("to_branch", "N/A"),
        "timestamp": doc.get("timestamp", "N/A")
    } for doc in latest])

# ⚠️ TEMPORARY ROUTE TO CLEAR DB (remove after use)
@app.route('/clear', methods=['GET'])
def clear_data():
    collection.delete_many({})
    return "✅ All data cleared from MongoDB!"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
