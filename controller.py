#importing modules
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
from bson.objectid import ObjectId

#setting up FLASK and environment
app = Flask(__name__)
CORS(app)
env = Env()
env.read_env()

#server_secret, or the password
SERVER_SECRET = "testing"
#the mongo string environment variable
MONGO_STRING = env("MONGO_STRING")
#setting default page size
DEFAULT_PAGE_SIZE = 25
#backend 'complicated' string to avoid hacking or unauthorized access
JWT_SECRET = "a very long and complicated string"
heartbeat = {}
#share hour limit
SHARE_HOURS = 100000

#the fileIndex itself
fileIndex = fi.Index(db=MONGO_STRING)
#holds the users that have access to this project
userdb = pymongo.MongoClient(MONGO_STRING).fileindexer.users

def isAuthenticated(request):
    try:
        token = request.headers["Authorization"][7:] #attempting to get a token
        return [True, jwt.decode(token, JWT_SECRET, algorithms=['HS256'])] #returns True with the token, correct secret, and with an alg for if the authemication ws correct
    except:
        return [False, jsonify({"code": 401, "error": "Invalid token"})] #returns error 401, invalid token if the authentication has an error

@app.route('/') 
def r_default(): #if there is just a slash at the end of the website name, this means there is no command, and the jsonify returns this
    return jsonify({"error":"No command"})

@app.route('/authenticate/', methods=['POST']) #using POST, this is with the web extension of /authenticate/
def r_authenticate():
    rbody = request.get_json() #getting data from json
    try:
        secret = rbody["secret"] #the secret of the data
        server = rbody["server"] #the server that the user has access to
        url = rbody["url"] #the url of the data
        if secret == SERVER_SECRET: #checks if the secret and SERVER_SECRET are the same
            token = jwt.encode({'server': server, 'url': url, 'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET) #holds a token for logging in
            return jsonify({"code": 200, "token": token.decode('utf-8')}) #returns the token that will pass through
        else:
            return jsonify({"code": 401, "error": "Invalid secret"}) #this means the program did not allow for this account info to go thru

    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"}) #if there is some error (not filled in user data), then there holds an error

@app.route('/heartbeat/',methods=['POST']) #with /heartbeart/ extension, uses "POST"
def r_heartbeat():
    authStat = isAuthenticated(request) #getting authentication results
    if authStat[0]: #checks if the entered data is authenticated
        rbody = request.get_json() #getting json data
        try:
            heartbeat[authStat[1]["server"]] = [authStat[1]["url"], int(datetime.today().timestamp())] #setting heardboat to a speciffied value (with url and date)
            return jsonify({"code": 200, "message": "Heartbeat registered"}) #returns a jsonify that will pass through
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"}) #returns an error otherwise
    else:
        return authStat[1] #otherwise will returns an error (from the isAutenticated function)

@app.route('/server/', methods=['GET']) #using GET, and /server/ extension
def r_listservers():
    authStat = isAuthenticated(request) #using a previous function
    if authStat[0]:
        return jsonify({"code": 200, "servers": heartbeat}) #returns a jsonify that will pass through the next code
    else:
        return jsonify({"code": 401, "error": "Not authorized"}) #will return error otherwise

@app.route('/server/remove/', methods=['POST']) #using POST, with the specified extension
def r_removeserver():
    authStat = isAuthenticated(request) #using data from authentication
    if authStat[0]:
        rbody = request.get_json() #using json for data
        try:
            server = rbody["server"] #getting server data
            del heartbeat[server] #taking out the data from heartbeat
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"}) #returns error otherwise
        return jsonify({"code": 200, "message": "OK"}) #returns jsonify that will pass thru
    else:
        return jsonify({"code": 401, "error": "Not authorized"}) #will return error otherwise

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
            return jsonify({"code": 400, "error": "Invalid request"})#will return error otherwise
    else:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/user/create/', methods=['POST'])
def r_createuser():
    rbody = request.get_json()
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        try:
            username = rbody["username"]
            password = rbody["password"]
            if userdb.count_documents({"username": username}) < 1:
                userdb.insert_one({"username": username, "password": sha256_crypt.encrypt(password)})
                return jsonify({"code": 200, "message": "OK"})
            else:
                return jsonify({"code": 400, "error": "User already exists"})#will return error otherwise
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})#will return error otherwise
    else:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

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
            return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise
    except TypeError:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/user/', methods=['GET'])
def r_users():
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        users = userdb.find({}, {"username":1})
        return jsonify({"code": 200, "users": json.loads(dumps(users))})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/user/delete/', methods=['POST'])
def r_deluser():
    rbody =  request.get_json()
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        try:
            userid = rbody["userid"]
            userdb.remove({"_id": ObjectId(userid)})
            return jsonify({"code": 200, "message": "OK"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})#will return error otherwise
    else:
            return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/clearIndex/', methods=['POST'])
def r_clearIndex():
    authStat = isAuthenticated(request)
    if authStat[0] and authStat[1]["scope"] == "all":
        rbody = request.get_json()
        server = rbody["server"]
        try:
            fileIndex.removeFromIndexByMongoQuery({"server": server})
            return jsonify({"code": 200, "message": "Index removed"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})#will return error otherwise
    else:
            return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/query/', methods=['POST']) #using query extension, with POST method
def r_query():
    authStat = isAuthenticated(request) #getting authentication data
    if authStat[0]: #check if the user was authenticated
        rbody = request.get_json()
        try:
            operation = rbody["operation"]
            if operation == "getAll": #checking if the operation is getAll
                try:
                    page = rbody["page"]
                except KeyError:
                    page = 1
                try:
                    page_size = rbody["page_size"]
                except KeyError:
                    page_size = DEFAULT_PAGE_SIZE
                return jsonify({"code": 200, "page": page, "page_size": page_size, "data": json.loads(dumps(fileIndex.getAll(page_size, page)))})

            if operation == "getOneByQuery": #checking if op. is getOneByQuery
                query = rbody["query"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getOneByQuery(query)))})

            if operation == "getById": #checking if operation is getbyID
                oid = rbody["id"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getById(oid)))[0]})

            if operation == "getAllByQuery": #checks if the operation is getAllByQuery
                query = rbody["query"]
                try:
                    page = rbody["page"]
                except KeyError:
                    page = 1
                try:
                    page_size = rbody["page_size"]
                except KeyError:
                    page_size = DEFAULT_PAGE_SIZE
                return jsonify({"code": 200, "page": page, "page_size": page_size, "data": json.loads(dumps(fileIndex.getAllByQuery(query, page_size, page)))}) #returns data for pages
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})#will return error otherwise
    else:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise
    

