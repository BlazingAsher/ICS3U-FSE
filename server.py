import os
import FileIndexer as fi
from environs import Env
from multiprocessing.pool import ThreadPool
import re

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
exclusions = [".*node_modules.*"]
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
        for root, dirs, files in os.walk(path):
            #print(root,dirs,files)
            # Check if the root matches any exclusions, if so, skip it
            for exclu in exclusionsCompiled:
                if exclu.match(root):
                    print("out",root)
                    continue
            for subject in files+dirs:
                excluded = False
                for exclu in exclusionsCompiled:
                    #print(os.path.join(root,subject))
                    if exclu.match(os.path.join(root, subject)):
                        #print("skip",os.path.join(root, subject))
                        excluded = True
                        break
                if not excluded:
                    #print("go")
                    allPaths.append(os.path.join(root, subject))
                    
        for path in allPaths:
            tp.apply_async(populateProperties, args=(path,))
        tp.close()
        tp.join()
    else:
        return fi.Response(400, "The path specified does not exist")

def loadSettings():
    fp.loadSettings()
