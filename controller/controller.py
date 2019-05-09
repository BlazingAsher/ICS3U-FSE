from flask import Flask,request,jsonify
from datetime import datetime,timedelta
import jwt

app = Flask(__name__)

SERVER_SECRET = "testing"
JWT_SECRET = "a very long and complicated string"
heartbeat = {}

@app.before_request
def isAuthenticated():
    print(request.endpoint)
    if request.endpoint != "r_authenticate":
        try:
            token = request.headers["Authorization"][7:]
            information = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except:
            return jsonify({"code": 401, "error": "Invalid token"})
        return

@app.route('/')
def r_default():
    return jsonify({"error":"No command"})

@app.route('/authenticate/', methods=['POST'])
def r_authenticate():
    rbody = request.get_json()
    try:
        secret = rbody["secret"]
        if secret == SERVER_SECRET:
            token = jwt.encode({'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode('utf-8')})
        else:
            return jsonify({"code": 401, "error": "Invalid secret"})

    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})

@app.route('/heartbeat/',methods=['POST'])
def r_heartbeat():
    rbody = request.get_json()
    try:
        server = rbody["server"]
        heartbeat[server] = int(datetime.today().timestamp())
        return jsonify({"code": 200, "message": "Heartbeat registered"})
    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})

@app.route('/server/', methods=['POST'])
def r_listservers():
    return jsonify({"code": 200, "servers": heartbeat})

@app.route('/server/remove/', methods=['POST'])
def r_removeserver():
    rbody = request.get_json()
    try:
        server = rbody["server"]
        del heartbeat[server]
    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})
    return jsonify({"code": 200, "message": "OK"})

