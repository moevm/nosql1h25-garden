from flask import Flask, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("MONGO_URI is not set in .env file")

client = MongoClient(mongo_uri)
db = client.testdb

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/test-mongo')
def test_mongo():
    db.mycollection.insert_one({"name": "test"})
    result = db.mycollection.find_one({"name": "test"}, {"_id": 0})
    return jsonify({"message": "Inserted and retrieved", "data": result})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")