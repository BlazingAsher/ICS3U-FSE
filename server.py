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

tp =  ThreadPool(16)
exclusions = ["node_modules", "\.git"]
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
        fqueue = queue.Queue()
        dqueue = queue.Queue()
        fqueue.put(path)
        dqueue.put(0)
        while not fqueue.empty():
            item = fqueue.get()
            cdepth = dqueue.get()
            if cdepth <= MAX_RECURSION_DEPTH:
                children = os.listdir(item)
                for child in children:
                    cfullpath = os.path.join(item,child)
                    if os.path.isdir(cfullpath):
                        excluded = False
                        for exclu in exclusionsCompiled:
                            if exclu.search(cfullpath):
                                excluded = True
                                break
                        if not excluded:
                            fqueue.put(os.path.join(item,child))
                            dqueue.put(cdepth+1)
                            allPaths.append(os.path.join(item,child))
            else:
                break
                    
        for path in allPaths:
            tp.apply_async(populateProperties, args=(path,))
        tp.close()
        tp.join()
    else:
        return fi.Response(400, "The path specified does not exist")

def loadSettings():
    fp.loadSettings()
