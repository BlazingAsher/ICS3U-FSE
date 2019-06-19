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

# Secret to authenticate servers
SERVER_SECRET = "testing"
# Retrieves the mongo connection string
MONGO_STRING = env("MONGO_STRING")
# Sets default document count to return
DEFAULT_PAGE_SIZE = 25
# JWT secret to sign authentication tokens with
JWT_SECRET = "a very long and complicated string"
# Stores information about the servers in the system
heartbeat = {}
# How long share links should be valid for (in hours)
SHARE_HOURS = 100000

# Create the mongoDB cursor to query the database with
fileIndex = fi.Index(db=MONGO_STRING)
# Create the monogoDB curor the query the user database with
userdb = pymongo.MongoClient(MONGO_STRING).fileindexer.users

def isAuthenticated(request):
    try:
        token = request.headers["Authorization"][7:] # Gets token from the Authorization header in Bearer mode
        return [True, jwt.decode(token, JWT_SECRET, algorithms=['HS256'])] # Attempts to decode and validate the token and dump all the information in the token
    except:
        return [False, jsonify({"code": 401, "error": "Invalid token"})] # If there is no Authorization header or the token cannot be decoded, return Invalid Token

# The default route
@app.route('/') 
def r_default():
    return jsonify({"error":"No command"})

# Server authentication route
@app.route('/authenticate/', methods=['POST'])
def r_authenticate():
    rbody = request.get_json() # Gets JSON post body
    try:
        secret = rbody["secret"] # Server secret sent by the server trying to authenticate
        server = rbody["server"] # The name of the server trying to authenticate
        url = rbody["url"] # The access url of the server trying to authentiate
        if secret == SERVER_SECRET: # Checks if the secret sent by the server is the same as the one we have
            token = jwt.encode({'server': server, 'url': url, 'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET) # Issue a token to the authenticated server
            return jsonify({"code": 200, "token": token.decode('utf-8')})
        else:
            return jsonify({"code": 401, "error": "Invalid secret"}) # Secret did not match - do not authorize

    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"}) #if there is some error (not filled in user data), return code 400

# Route servers contact to send hearbeats
@app.route('/heartbeat/',methods=['POST'])
def r_heartbeat():
    authStat = isAuthenticated(request) # Get authenticaton data
    if authStat[0]: # Make sure the user is  authenticated
        rbody = request.get_json() # Get the post body JSON
        try:
            heartbeat[authStat[1]["server"]] = [authStat[1]["url"], int(datetime.today().timestamp())] # Update the server's heartbeat
            return jsonify({"code": 200, "message": "Heartbeat registered"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"}) # Values are missing from the request
    else:
        return authStat[1] #otherwise will returns an error (from the isAutenticated function)

# Gets a list of server
@app.route('/server/', methods=['GET'])
def r_listservers():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0]:
        return jsonify({"code": 200, "servers": heartbeat}) # Return all the servers registered
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

# Route to remove servers from hearbeat dict
@app.route('/server/remove/', methods=['POST'])
def r_removeserver():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0]:
        rbody = request.get_json() # Get post body JSON
        try:
            server = rbody["server"] # Get the server to remove
            del heartbeat[server] # Taking out the data from heartbeat dict
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
        return jsonify({"code": 200, "message": "OK"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

# Route to generate a share token
@app.route('/share/', methods=['POST'])
def r_share():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0] and authStat[1]["scope"] == "all": # Ensure that the user is NOT a share user and an actual system user!
        try:
            rbody = request.get_json()
            # Get the path and server in which the file to be shared is located
            path = rbody["path"]
            server = rbody["server"]
            # Create a authorization token that grants access to ONLY that path/server combination
            token = jwt.encode({'scope': path, 'server': server, 'exp': datetime.utcnow() + timedelta(hours=SHARE_HOURS)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode("utf-8")})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

# Route to create a new user
@app.route('/user/create/', methods=['POST'])
def r_createuser():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0] and authStat[1]["scope"] == "all": # Ensure that the user is NOT a share user and an actual system user!
        try:
            rbody = request.get_json()
            # Get the desired username and password of the user to be created
            username = rbody["username"]
            password = rbody["password"]
            # Make sure the user doesn't already exist
            if userdb.count_documents({"username": username}) < 1:
                # Store the user in the database and hash the password
                userdb.insert_one({"username": username, "password": sha256_crypt.encrypt(password)})
                return jsonify({"code": 200, "message": "OK"})
            else:
                return jsonify({"code": 400, "error": "User already exists"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

# Route to authenticate users
@app.route('/userauth/', methods=['POST'])
def r_userauth():
    try:
        rbody = request.get_json()
        # Get the username and password
        username = rbody["username"].strip()
        password = rbody["password"].strip()
    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})

    # Find a user with the requested username
    user = userdb.find_one({"username": username})

    try:
        # Gets the hash stored in the db
        pwdhash = user["password"]
        # Verify the hash
        if sha256_crypt.verify(password, pwdhash):
            # Issue a token that grants access to all server resources
            token = jwt.encode({'scope': 'all', 'exp': datetime.utcnow() + timedelta(hours=12)},JWT_SECRET)
            return jsonify({"code": 200, "token": token.decode("utf-8")})
        else:
            return jsonify({"code": 401, "error": "Not authorized"})
    except TypeError:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

# Route to list users
@app.route('/user/', methods=['GET'])
def r_users():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0] and authStat[1]["scope"] == "all": # Ensure the user is a system user
        # Get all the users in the db but ONLY RETURN usersnames!
        users = userdb.find({}, {"username":1})
        return jsonify({"code": 200, "users": json.loads(dumps(users))})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})#will return error otherwise

@app.route('/user/delete/', methods=['POST'])
def r_deluser():
    rbody =  request.get_json()
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0] and authStat[1]["scope"] == "all": # Ensure the user is a system user
        try:
            userid = rbody["userid"] # Get the user id to remove
            userdb.remove({"_id": ObjectId(userid)}) # Remove the user from the db
            return jsonify({"code": 200, "message": "OK"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
            return jsonify({"code": 401, "error": "Not authorized"})

# Route to clear indexes
@app.route('/clearIndex/', methods=['POST'])
def r_clearIndex():
    authStat = isAuthenticated(request) # Get authentication data
    if authStat[0] and authStat[1]["scope"] == "all": # Ensure the user is a system user
        try:
            # Get the server index that the user wishes to remove
            rbody = request.get_json()
            server = rbody["server"]
            # Remove all entries from the db from that server
            fileIndex.removeFromIndexByMongoQuery({"server": server})
            return jsonify({"code": 200, "message": "Index removed"})
        except KeyError:
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})

# Route to query the database
@app.route('/query/', methods=['POST'])
def r_query():
    authStat = isAuthenticated(request) #getting authentication data
    if authStat[0]: #check if the user was authenticated
        rbody = request.get_json()
        try:
            operation = rbody["operation"]
            if operation == "getAll": #checking if the operation is getAll, which will return all documents in the db
                try:
                    page = rbody["page"]
                except KeyError:
                    page = 1
                try:
                    page_size = rbody["page_size"]
                except KeyError:
                    page_size = DEFAULT_PAGE_SIZE
                return jsonify({"code": 200, "page": page, "page_size": page_size, "data": json.loads(dumps(fileIndex.getAll(page_size, page)))})

            if operation == "getOneByQuery": #checking if op. is getOneByQuery, which will return ONE document that matches the query
                query = rbody["query"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getOneByQuery(query)))})

            if operation == "getById": #checking if operation is getbyID, whcih will return ONE document with the specified ID
                oid = rbody["id"]
                return jsonify({"code": 200, "data": json.loads(dumps(fileIndex.getById(oid)))[0]})

            if operation == "getAllByQuery": #checks if the operation is getAllByQuery, which will return ALL documents that matches the query
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
            return jsonify({"code": 400, "error": "Invalid request"})
    else:
        return jsonify({"code": 401, "error": "Not authorized"})
    

