# server.py
from flask import Flask, request

SECRET_MESSAGE = "THE WHOLE HUMAN GENOME"
hashes = []
app = Flask(__name__)

@app.route("/", methods = ['GET', 'PUT'])
def hash_store():
    if request.method == 'PUT':
        hashes.append(request.get_data())
        return SECRET_MESSAGE
    else:
        if len(hashes) < 5:
            return "no way reference genome is loaded"
        else:
            key = request.args['key']
            return hashes[int(key)]


app.run('127.0.0.1', port=4567)