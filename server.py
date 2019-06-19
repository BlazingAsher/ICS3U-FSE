from flask import Flask, request, Response, jsonify, send_file
import os
import FileIndexer as fi
from environs import Env
from multiprocessing.pool import ThreadPool
import re
import queue
import threading
from threading import Event, Thread
import uuid
import json
import requests
import urllib.parse
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

env = Env()
env.read_env()

MAX_RECURSION_DEPTH = 999999999
# Load all the settings from the ENV file
MONGO_STRING = env("MONGO_STRING")
SERVER_NAME = env("SERVER_NAME")
SERVER_URL = env("SERVER_URL")
MAGIC_FILE = env("MAGIC_FILE")
CONTROLLER_URL = env("CONTROLLER_URL")
CONTROLLER_SECRET = env("CONTROLLER_SECRET")

# Initialize the file processing modules
fp = fi.Processor(db=MONGO_STRING, magic=MAGIC_FILE, server_name=SERVER_NAME)
fp.loadPlugins()
fp.loadSettings()

fileIndex = fi.Index(db=MONGO_STRING)

# Create a thread pool so that Python doesn't spawn thousands of threads during indexing
tp = None

exclusions = ["node_modules", "\.git"]

# Store async jobs
jobs = []

running = True

# Index build status (current,total)
job_status = {"build":{"completed": 0,"total": 0, "state": "OK", "additional": "Not initialized","cancelled": True}}
job_status_lock = threading.Lock()

# Compile all the user's expressions
# TODO: ERROR HANDLING
exclusionsCompiled = [re.compile(exp) for exp in exclusions]

def populateProperties(path, options={}):
    global job_status
    if not job_status["build"]["cancelled"]:
        try:
            #print("----------------------")
            # Acquire a lock to prevent race conditions
            job_status_lock.acquire()
            print("lock acquire")
            try:
                job_status["build"]["completed"] += 1
            finally:
                job_status_lock.release()
            print("lock release")
            # Request the file at the path to be indexed
            fileIndex.addToIndex(path, fp.getAllProperties(path), SERVER_NAME)
        except OSError:
            pass
        return
            #return fi.Response(400, "The path specified is not a valid file")
    else:
        print("cancelled")
        return
    
def createIndex(path, options={}):
    global job_status, tp
    
    allPaths = []
    if os.path.isdir(path):
        # Create a path queue and a depth queue to keep track of node depth
        fqueue = queue.Queue()
        dqueue = queue.Queue()

        # Add the root path and a depth of 0
        fqueue.put(path)
        dqueue.put(0)

        # Keep running until the queue has been emptied
        while not fqueue.empty():
            # Get the path of the item and its depth
            item = fqueue.get()
            cdepth = dqueue.get()
            # Check if maximum recursion depth has been reached
            if cdepth <= MAX_RECURSION_DEPTH:
                try:
                    children = os.listdir(item)
                    # Loop through children (make sure the file/directory still exists before performing action)
                    for child in children:
                        cfullpath = os.path.join(item,child)
                        if os.path.exists(cfullpath):
                            # Loop through the exclusions to check if we need to even process the file
                            excluded = False
                            for exclu in exclusionsCompiled:
                                if exclu.search(cfullpath):
                                    excluded = True
                                    break
                            if not excluded:
                                # If it is a directory, add it to the back of the queue
                                if os.path.isdir(cfullpath):
                                    fqueue.put(os.path.join(item,child))
                                    dqueue.put(cdepth+1)
                                # Add to the list of files/directories to be processed
                                allPaths.append(os.path.join(item,child))
                except PermissionError:
                    pass
            else:
                break

        print("list done")
        job_status["build"] = {"completed": 0,"total": len(allPaths),"state": "OK","additional": "File-tree built","cancelled": False}
        # Initialize the threadpool
        tp =  ThreadPool(16)
        for path in allPaths:
            # Assign a new task to populate properties of the file/directory to the thread pool
            tp.apply_async(populateProperties, args=(path,))
            
        # Cleanup thread pool
        tp.close()
        tp.join()
        print("done")
        job_status["build"]["state"] = "OK"
        job_status["build"]["additional"] = "Done"
        return
    else:
        job_status["build"]["state"] = "ERROR"
        job_status["build"]["additional"] = "The path given does not exist or is not a directory"
        return
              
def loadSettings():
    fp.loadSettings()

# Shuts down the server
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

# Send heartbeats to the controller
def send_heartbeat(key):
    requests.post(CONTROLLER_URL+"/heartbeat/",headers={"Authorization": "Bearer "+key})

# This thread will send heartbeats to the server every second
class HeartBeatThread(Thread):
    def __init__(self, event, key):
        Thread.__init__(self)
        self.stopped = event
        self.key = key

    def run(self):
        while not self.stopped.wait(1):
            send_heartbeat(self.key)

# Get an authorization token from the controller
key = requests.post(CONTROLLER_URL+"/authenticate/",json={"secret": CONTROLLER_SECRET, "server": SERVER_NAME, "url": SERVER_URL}).json()["token"]
print(key)

stopFlag = Event()

hb = HeartBeatThread(stopFlag, key)
hb.start()

@app.route("/")
def r_home():
    return jsonify({"code": 400, "error": "No command"})

# List all mulithreaded jobs
@app.route("/job/")
def r_listjob():
    return jsonify({"code": 200, "jobs": job_status})

# Get information about a job
@app.route("/job/<jobid>/")
def r_jobstat(jobid):
    try:
        job = job_status[jobid]
        return jsonify({"code": 200, "status": job})
    except KeyError:
        return jsonify({"code": 400, "error": "Job ID not found"})

# Cancel a job
@app.route("/job/<jobid>/cancel/")
def r_jobcancel(jobid):
    try:
        job_status_lock.acquire()
        job_status[jobid]["cancelled"] = True
        return jsonify({"code": 200, "message": "Job cancelled"})
    except KeyError:
        return jsonify({"code": 400, "error": "Job ID not found"})
    finally:
        job_status_lock.release()
    
# Request a new index to be made
@app.route("/index/", methods=['POST'])
def r_createIndex():
    global job_status
    req_data = request.get_json()
    # Ensure that an index is not currently being built
    if job_status["build"]["total"] - job_status["build"]["completed"] == 0:
        # Start createIndex on a seperate thread so that client does not need to wait before HTTP response is sent
        thread = threading.Thread(target = createIndex, args = (req_data["path"],))
        thread.start()
        return jsonify({"code": 200, "message": "Job created", "jobid": "build"})
    else:
        return jsonify({"code": 400, "error": "An index is currently being built"})

# Retrieves a file on the file system at the requested path
@app.route("/retrieve/<path>", methods=['GET'])
def r_retrieveFile(path):
    req_data = request.get_json()
    try:
        dpath = urllib.parse.unquote(path)
        return send_file(dpath, as_attachment=True)
    except KeyError:
        return jsonify({"code": 400, "error": "Invalid request"})

# Kill the server
@app.route("/kill/")
def kill_server():
    stopFlag.set()
    shutdown_server()
    return jsonify({"code": 200, "message": "Server killed"})
