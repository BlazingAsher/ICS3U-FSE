import magic
import re
import os
import pymongo

class Response:
    code = 500
    message = "Internal Server Error"
    def __init__(self, code, message):
        self.code = code
        self.message = message
        
class Processor:
    def __init__(self, **kwargs):
        self.magic = kwargs.get("magic")
        self.ffprobe = kwargs.get("ffprobe")
        self.SERVER_NAME = kwargs.get("server_name")
        self.mime = magic.Magic(mime=True, magic_file=self.magic)
        
        self._client = pymongo.MongoClient(kwargs.get("db"))
        self._db = self._client.fileindexer
        self._settingscol = self._db.settings
        self._settings = self._settingscol.find_one({"name":"global"})
    
    _plugins = {}

    formatMap = {}

    extMap = {
        "jpg": "image/jpeg",
        "png": "image/png"
    }

    compiledMatches = {}

    def loadSettings(self):
        self._settings = self._settingscol.find_one({"name":"global"})
        if self._settings is None:
            print("Generating default settings")
            defaultSettings = {
                "name": "global",
                "crawler" : {
                        "identify_by_extension": True
                    },
                "image": {
                        "extended_exif": False,
                        "simple_exif_tags": ["DateTimeOriginal","Make","Model","Flash","UserComment","Software","DateTime","LensModel"]
                    },
                "video": {
                        "extended_videodata": False,
                        "simple_video_tags": ["container", "duration","bitrate","haveVideo","haveAudio","videoCodec","videoWidth","videoHeight","audicCodec"]
                    }
                }
            #PUSH TO SERVER AND SET LOCAL
            self._settingscol.insert(defaultSettings)
            self._settings = defaultSettings

    def loadPlugins(self):
        # This will inject a plugin's code into this class
        pluginList = [x for x in os.listdir("plugins") if x[x.rfind(".")+1:].lower() == "py"]
        for pluginFile in pluginList:
            if pluginFile != "__init__.py":
                pluginBasename = pluginFile[:pluginFile.rfind(".")]
                plugin = __import__("plugins."+pluginBasename)
                plugID = eval("plugin.%s.get_id()"%pluginBasename)
                self._plugins[plugID] = eval("plugin."+pluginBasename+".plugin_main")
                handlers = eval("plugin.%s.get_handlers()"%pluginBasename)
                for handler in handlers:
                    self.formatMap[handler] = plugID

        self.compiledMatches = self.compileExpressions(self.formatMap.keys())
        
    def getPlugins(self):
        return self.formatMap
    
    def extToMime(self, ext):
        ext = ext.lower()
        print(ext)
        try:
            return self.extMap[ext]
        except KeyError:
            return "none/none"

    def compileExpressions(self, expList):
        matchList = [[exp, re.compile(exp)] for exp in list(expList)]
        return matchList

    def getCompiled(self):
        return self.compiledMatches
    
    def dictKeyRegEx(self, dic, strToMatch):
        # THIS WILL ONLY RETURN THE FIRST OCCURANCE
        for reg in self.compiledMatches:
            if reg[1].match(strToMatch):
                return dic[reg[0]]
            
    def getAllExtended(self, path):
        ext = path[path.rfind(".")+1:].lower()
        mime = "none/none"
        if len(ext) > 0 and self._settings["crawler"]["identify_by_extension"]:
            # Has a file extension
            # map it
            mime = self.extToMime(ext)
            
        if mime == "none/none":
            # try to get mime information
            print("thru mime")
            mime = self.mime.from_file(path)
        print(mime)
        # Potential logic change needed here
        additionalPlugin = self.dictKeyRegEx(self.formatMap, mime)
        print("to plugin",additionalPlugin)
        if additionalPlugin:
            additional = self._plugins[additionalPlugin](self, path)
        else:
            additional = {}

        return additional

    def getAllProperties(self, path):
        if os.path.isfile(path):
            properties = {}
            properties["lastmod"] = os.path.getmtime(path)
            properties["size"] = os.path.getsize(path)
            properties["additional"] = self.getAllExtended(path)
            return properties
        else:
            raise OSError
class Index:
    def __init__(self, **kwargs):
        self._client = pymongo.MongoClient(kwargs.get("db"))
        self._db = self._client.fileindexer
        self._indexCollection = self._db.index
    
    def deleteIndex(self):
        self._indexCollection.drop()

    def getAll(self):
        return self._indexCollection.find()

    def getOneByQuery(self, query):
        return self._indexCollection.find_one(query)

    def getAllByQuery(self, query):
        return self._indexCollection.find(query)

    def addToIndex(self, path, properties, server):
        toInsert = {"filename":os.path.basename(path), "path": path, "server": server, "properties": properties}
        self._indexCollection.insert_one(toInsert)

    def removeFromIndexByMongoQuery(self, query):
        self._indexCollection.delete_one(query)

    def removeFromIndexByPath(self, path):
        self.removeFromIndexByMongoQuery({"path":path})

    def removeFromIndexById(self, docID):
        self.removeFromIndexByMongoQuery({"_id":docID})

    def updateIndexByMongoQuery(self, query, new):
        self.indexCollection.update_one(query, new)

    def updateIndexByPath(self, path, new):
        self.updateIndexByMongoQuery({"path": path}, new)

    def updateIndexById(self, docID, new):
        self.updateIndexByMongoQuery({"_id":docID}, new)
