import os
import FileIndexer as fi
from environs import Env
env = Env()
env.read_env()

MAX_RECURSION_DEPTH = 999999999
MONGO_STRING = env("MONGO_STRING")
SERVER_NAME = env("SERVER_NAME")
MAGIC_FILE = env("MAGIC_FILE")
FFPROBE = env("FFPROBE")
fp = fi.Processor(db=MONGO_STRING, magic=MAGIC_FILE, ffprobe=FFPROBE, server_name=SERVER_NAME)
fp.loadSettings()
fp.loadPlugins()

fileIndex = fi.Index(db=MONGO_STRING)
def populateProperties(path, options={}):
    try:
        fileIndex.addToIndex(path, fp.getAllProperties(path), SERVER_NAME)
    except OSError:
        return fi.Response(400, "The path specified is not a valid file")
    
def createIndex(path, options={}):
    allPaths = []
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            print(root,dirs,files)
            for file in files:
                allPaths.append(os.path.join(root, file))
        for file in allPaths:
            populateProperties(file)
    else:
        return fi.Response(400, "The path specified does not exist")

def loadSettings():
    fp.loadSettings()
