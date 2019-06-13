from flask import Flask,request,jsonify
from datetime import datetime,timedelta
import jwt
import FileIndexer as fi
from environs import Env
from bson.json_util import dumps
import json
from flask_cors import CORS
import pymongo
from passlib.hash import sha256_crypt

app = Flask(__name__)
CORS(app)
env = Env()
env.read_env()

SERVER_SECRET = "testing"

MONGO_STRING = env("MONGO_STRING")
DEFAULT_PAGE_SIZE = 25
JWT_SECRET = "a very long and complicated string"
heartbeat = {}
SHARE_HOURS = 100000

fileIndex = fi.Index(db=MONGO_STRING)
userdb = pymongo.MongoClient(MONGO_STRING).fileindexer.users

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
            heartbeat[authStat[1]["server"]] = [authStat[1]["url"], int(datetime.today().timestamp())]
            return jsonify({"code": 200, "message": "Heartbeat registered"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return authStat[1]

@app.route('/server/', methods=['GET'])
def r_listservers():
    authStat = isAuthenticated(request)
    if authStat[0]:
        return jsonify({"code": 200, "servers": heartbeat})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

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
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

@app.route('/share/', methods=['POST'])
def r_share():
    rbody = request.get_json()
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        try:
            path = rbody["path"]
            server = rbody["server"]
            token = jwt.encode({'scope': path, 'server': server, 'exp': datetime.utcnow() + timedelta(hours=SHARE_HOURS)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode("utf-8")})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

@app.route('/createuser/', methods=['POST'])
def r_createuser():
    rbody = request.get_json()
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        try:
            username = rbody["username"]
            password = rbody["password"]
            userdb.insert_one({"username": username, "password": sha256_crypt.encrypt(password)})
            return jsonify({"code": 200, "message": "OK"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

@app.route('/userauth/', methods=['POST'])
def r_userauth():
    rbody = request.get_json()
    try:
        username = rbody["username"].strip()
        password = rbody["password"].strip()
    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})
    user = userdb.find_one({"username": username})
    print(user)
    print(username)
    try:
        pwdhash = user["password"]
        if sha256_crypt.verify(password, pwdhash):
            token = jwt.encode({'scope': 'all', 'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode("utf-8")})
        else:
            return jsonify({"code": 401, "error": "Not authorized"})
    except TypeError:
        return jsonify({"code": 401, "error": "Not authorized"})

@app.route('/query/', methods=['POST'])
def r_query():
    authStat = isAuthenticated(request)
    if authStat[0]:
        rbody = request.get_json()
        try:
            operation = rbody["operation"]
            if operation == "getAll":
                try:
                    page = rbody["page"]
                except KeyError:
                    page = 1
                try:
                    page_size = rbody["page_size"]
                except KeyError:
                    page_size = DEFAULT_PAGE_SIZE
                return jsonify({"code": 200, "page": page, "page_size": page_size, "data": json.loads(dumps(fileIndex.getAll(page_size, page)))})

            if operation == "getOneByQuery":
                query = rbody["query"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getOneByQuery(query)))})

            if operation == "getById":
                oid = rbody["id"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getById(oid)))[0]})

            if operation == "getAllByQuery":
                query = rbody["query"]
                try:
                    page = rbody["page"]
                except KeyError:
                    page = 1
                try:
                    page_size = rbody["page_size"]
                except KeyError:
                    page_size = DEFAULT_PAGE_SIZE
                return jsonify({"code": 200, "page": page, "page_size": page_size, "data": json.loads(dumps(fileIndex.getAllByQuery(query, page_size, page)))})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})
    

