from flask import Flask,request,jsonify
from datetime import datetime,timedelta
import jwt

app = Flask(__name__)

SERVER_SECRET = "testing"
JWT_SECRET = "a very long and complicated string"
heartbeat = {}

def isAuthenticated(request):
    try:
        token = request.headers["Authorization"][7:]
        return [True, jwt.decode(token, JWT_SECRET, algorithms=['HS256'])]
    except:
        return [False, jsonify({"code": 401, "error": "Invalid token"})]

@app.route('/')
def r_default():
    return jsonify({"error":"No command"})

@app.route('/authenticate/', methods=['POST'])
def r_authenticate():
    rbody = request.get_json()
    try:
        secret = rbody["secret"]
        server = rbody["server"]
        url = rbody["url"]
        if secret == SERVER_SECRET:
            token = jwt.encode({'server': server, 'url': url, 'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode('utf-8')})
        else:
            return jsonify({"code": 401, "error": "Invalid secret"})

    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})

@app.route('/heartbeat/',methods=['POST'])
def r_heartbeat():
    authStat = isAuthenticated(request)
    if authStat[0]:
        rbody = request.get_json()
        try:
            heartbeat[authStat["server"]] = [authStat["url"], int(datetime.today().timestamp())]
            return jsonify({"code": 200, "message": "Heartbeat registered"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return authStat[1]

@app.route('/server/', methods=['POST'])
def r_listservers():
    authStat = isAuthenticated(request)
    if authStat[0]:
        return jsonify({"code": 200, "servers": heartbeat})
    else:
        return authStat[1]

@app.route('/server/remove/', methods=['POST'])
def r_removeserver():
    authStat = isAuthenticated(request)
    if authStat[0]:
        rbody = request.get_json()
        try:
            server = rbody["server"]
            if server == "global" or authStat["server"] == server:
                del heartbeat[server]
            else:
                return jsonify({"code": 403, "error": "Insufficient permissions"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
        return jsonify({"code": 200, "message": "OK"})

