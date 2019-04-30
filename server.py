import os
import FileIndexer as fi
from environs import Env
from multiprocessing.pool import ThreadPool
import re
import queue

env = Env()
env.read_env()

MAX_RECURSION_DEPTH = 999999999
MONGO_STRING = env("MONGO_STRING")
SERVER_NAME = env("SERVER_NAME")
MAGIC_FILE = env("MAGIC_FILE")

fp = fi.Processor(db=MONGO_STRING, magic=MAGIC_FILE, server_name=SERVER_NAME)
fp.loadPlugins()
fp.loadSettings()

fileIndex = fi.Index(db=MONGO_STRING)

# Create a thread pool so that Python doesn't spawn thousands of threads during indexing
tp =  ThreadPool(16)

exclusions = ["node_modules", "\.git"]

# Compile all the user's expressions
# TODO: ERROR HANDLING
exclusionsCompiled = [re.compile(exp) for exp in exclusions]

def populateProperties(path, options={}):
    try:
        #print("----------------------")
        fileIndex.addToIndex(path, fp.getAllProperties(path), SERVER_NAME)
    except OSError:
        return fi.Response(400, "The path specified is not a valid file")
    
def createIndex(path, options={}):
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
            else:
                break
                    
        for path in allPaths:
            # Assign a new task to populate properties of the file/directory to the thread pool
            tp.apply_async(populateProperties, args=(path,))
            
        # Cleanup thread pool
        tp.close()
        tp.join()
    else:
        return fi.Response(400, "The path specified does not exist or is not a directory")

def loadSettings():
    fp.loadSettings()
