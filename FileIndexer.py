import magic
import re
import os
from PIL import Image, ExifTags
from MediaInfo import MediaInfo
import pymongo

class Response:
    code = 500
    message = "Internal Server Error"
    def __init__(self, code, message):
        self.code = code
        self.message = message
        
class Processor:
    def __init__(self, **args):
        self.magic = args.get("magic")
        self.ffprobe = args.get("ffprobe")
        self.mime = magic.Magic(mime=True, magic_file=self.magic)
        
    EXTENDED_EXIF = False
    
    def _image(self, path):
        print("Image!")
        img = Image.open(path)
        if img._getexif():
            totalExif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS }
            if self.EXTENDED_EXIF:
                return totalExif
            else:
                returnExif = {}
                exifKeyList = ["DateTimeOriginal","Make","Model","Flash","UserComment","Software","DateTime","LensModel"]
                for exifKey in exifKeyList:
                    try:
                        returnExif[exifKey] = totalExif[exifKey]
                    except KeyError:
                        pass
                
                return returnExif
        else:
            return {}
        
    def _document(self, path):
        print("sellf!")

    EXTENDED_VIDEODATA = False
    def _video(self, path):
        info     = MediaInfo(filename = path, cmd=self.ffprobe, mode='ffprobe')
        infoData = info.getInfo()

        if self.EXTENDED_VIDEODATA:
            return infoData
        else:
            returnData = {}
            dataKeyList = ["container", "duration","bitrate","haveVideo","haveAudio","videoCodec","videoWidth","videoHeight","audicCodec"]
            for dataKey in dataKeyList:
                try:
                    returnData[dataKey] = infoData[dataKey]
                except KeyError:
                    pass
            return returnData

    USE_FILE_EXT = True
    
    formatMap = {
        "image\/.*": _image,
        "video\/.*": _video
    }

    extMap = {
        "jpg": "image/jpeg",
        "png": "image/png"
    }

    def extToMime(self, ext):
        ext = ext.lower()
        print(ext)
        try:
            return self.extMap[ext]
        except KeyError:
            return "none/none"

    def compileExpressions(expList):
        matchList = [[exp, re.compile(exp)] for exp in list(expList)]
        return matchList
    
    compiledMatches = compileExpressions(formatMap.keys())

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
        if len(ext) > 1 and self.USE_FILE_EXT:
            # Has a file extension
            # map it
            mime = self.extToMime(ext)
            
        if mime == "none/none":
            # try to get mime information
            print("thru mime")
            mime = self.mime.from_file(path)
        print(mime)
        additionalPlugin = self.dictKeyRegEx(self.formatMap, mime)
        if additionalPlugin:
            additional = additionalPlugin(self, path)
        else:
            additional = {}
        if not additional:
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
    def __init__(self, **addargs):
        self.client = pymongo.MongoClient(addargs.get("db"))
        self.db = self.client.fileindexer
        self.indexCollection = self.db.index
        self.settings = self.db.settings
    
    def deleteIndex(self):
        self.indexCollection.drop()

    def getAll(self):
        return self.indexCollection.find()

    def getOneByQuery(self, query):
        return self.indexCollection.find_one(query)

    def getAllByQuery(self, query):
        return self.indexCollection.find(query)

    def addToIndex(self, path, properties, server):
        toInsert = {"filename":os.path.basename(path), "path": path, "server": server, "properties": properties}
        self.indexCollection.insert_one(toInsert)

    def removeFromIndexByMongoQuery(self, query):
        self.indexCollection.delete_one(query)

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
        
