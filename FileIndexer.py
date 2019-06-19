import magic
import re
import os
import pymongo
from bson.objectid import ObjectId

class Response:
    code = 500
    message = "Internal Server Error"
    def __init__(self, code, message):
        self.code = code
        self.message = message
        
class Processor:
    def __init__(self, **kwargs):
        # Initializes paths and settings
        self.magic = kwargs.get("magic")
        self.SERVER_NAME = kwargs.get("server_name")
        self.mime = magic.Magic(mime=True, magic_file=self.magic)
        
        self._client = pymongo.MongoClient(kwargs.get("db"))
        self._db = self._client.fileindexer
        self._settingscol = self._db.settings
        self._settings = self._settingscol.find_one({"name":"global"})

    # This will store loaded plugins
    _plugins = {}

    # Map mime types to plugins
    formatMap = {}

    # Map extensions with (most common) mime types
    extMap = {}

    # Stores complied re matches for speed
    compiledMatches = {}

    # Default settings for plugins and the server
    defaultSettings = {
        "name": "global",
        "crawler": {
            "identify_by_extension": True
        }
    }

    def loadSettings(self):
        self._settings = self._settingscol.find_one({"name":"global"})
        if self._settings is None:
            print("Generating default settings")
            #PUSH TO SERVER AND SET LOCAL
            self._settingscol.insert(self.defaultSettings)
            self._settings = self.defaultSettings

    def loadPlugins(self):
        # This will load plugins from the plugins directory
        pluginList = [x for x in os.listdir("plugins") if x[x.rfind(".")+1:].lower() == "py"]
        for pluginFile in pluginList:
            if pluginFile != "__init__.py":
                # Get all the plugin's information
                pluginBasename = pluginFile[:pluginFile.rfind(".")]
                plugin = __import__("plugins."+pluginBasename)
                plugID = eval("plugin.%s.get_id()"%pluginBasename)
                self._plugins[plugID] = eval("plugin."+pluginBasename+".plugin_main")
                handlers = eval("plugin.%s.get_handlers()"%pluginBasename)
                
                # Register the plugin as a handler for the file type
                for handler in handlers:
                    self.formatMap[handler] = plugID
                # Add any additional ext to format mappings to the central map
                self.extMap.update(eval("plugin.%s.get_mappings()"%pluginBasename))
                # Add any additional settings to the global settings
                self.defaultSettings.update(eval("plugin.%s.get_default_settings()"%pluginBasename))

        self.compiledMatches = self.compileExpressions(self.formatMap.keys())
        
    def getPlugins(self):
        return self.formatMap
    
    def extToMime(self, ext):
        ext = ext.lower()
        #print(ext)
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
        # Prefer an exact match
        matchedReg = ""
        for reg in self.compiledMatches:
            if reg[0].replace("\/","/").replace("\.",".") == strToMatch:
                return dic[reg[0]]
            elif reg[1].match(strToMatch):
                matchedReg = reg[0]

        return dic[matchedReg] if len(matchedReg) > 0 else None
            
    def getAllExtended(self, path):
        ext = path[path.rfind(".")+1:].lower()
        mime = "none/none"
        if len(ext) > 0 and self._settings["crawler"]["identify_by_extension"]:
            # Has a file extension
            # map it
            mime = self.extToMime(ext)
            
        if mime == "none/none":
            # try to get mime information

            mime = self.mime.from_file(path)

        # Get the plugin that is registered to handle the file type
        additionalPlugin = self.dictKeyRegEx(self.formatMap, mime)

        # If a plugin is returned, run it
        if additionalPlugin:
            additional = self._plugins[additionalPlugin](self, path)
        else:
            additional = {}

        return additional
    # Will assemble properties of the file
    def getAllProperties(self, path):
        if os.path.isfile(path):
            properties = {}
            properties["type"] = "file"
            properties["lastmod"] = os.path.getmtime(path)
            properties["size"] = os.path.getsize(path)
            properties["additional"] = self.getAllExtended(path)
            return properties
        elif os.path.isdir(path):
            properties = {}
            properties["type"] = "folder"
            return properties
        else:
            raise OSError
#class of Index operations
class Index:
    def __init__(self, **kwargs):
        self._client = pymongo.MongoClient(kwargs.get("db"))
        self._db = self._client.fileindexer
        self._indexCollection = self._db.index

    # Clear the WHOLE index
    def clearIndex(self):
        self._indexCollection.delete_many({})
        
    # Returns all documents in the database
    def getAll(self, page_size, page_num):
        skips = page_size * (page_num - 1)
        return self._indexCollection.find({}).skip(skips).limit(page_size)

    # Returns ONE document in the database that matches the query
    def getOneByQuery(self, query):
        return self._indexCollection.find_one(query)
    
    # Returns ALL documents in the database that matches the query
    def getAllByQuery(self, query, page_size, page_num):
        skips = page_size * (page_num - 1)
        return self._indexCollection.find(query).skip(skips).limit(page_size)

    # Returns ONE document in the database that matches ID
    def getById(self, oid):
        return self._indexCollection.find({"_id": ObjectId(oid)})

    # Get the size of the index
    def getIndexSize(self):
        return self._indexCollection.count()

    # Add a file to the index
    def addToIndex(self, path, properties, server):
        toInsert = {"subject":os.path.basename(path), "path": path, "server": server, "properties": properties}
        self._indexCollection.insert_one(toInsert)

    # Remove files from the db that matches the query
    def removeFromIndexByMongoQuery(self, query):
        self._indexCollection.delete_many(query)

    # Remove files from the db that matches the given path
    def removeFromIndexByPath(self, path):
        self.removeFromIndexByMongoQuery({"path":path})

    # Remove file from the db that matches the id
    def removeFromIndexById(self, docID):
        self.removeFromIndexByMongoQuery({"_id":docID})

    # Update an index entry by the id
    def updateIndexByMongoQuery(self, query, new):
        self._indexCollection.update_one(query, new)

    # Update an index entry by the path
    def updateIndexByPath(self, path, new):
        self.updateIndexByMongoQuery({"path": path}, new)

    # Update an index entry by the ID
    def updateIndexById(self, docID, new):
        self.updateIndexByMongoQuery({"_id":docID}, new)
