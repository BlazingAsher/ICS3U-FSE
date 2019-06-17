from mp3_tagger import MP3File, VERSION_1, VERSION_2, VERSION_BOTH #importing necessary modules
def get_id():
    return "com.davidhui.mp3" #getting mp3 id

def get_handlers():
    return ["audio\/mpeg"] #MIME type for mp3

def get_mappings():
    mediaMap = {
        "mp3": "audio/mpeg" #only mp3 type used, stored in a dict
    }
    return mediaMap #returning the dict

def get_default_settings():
    defaultSettings = {
        "mp3": {
            "extended_data": False, #dict element extended_data set to False
            "simple_media_tags": ["artist", "album","track","year","genre"] #other general tags in a mp3 file
        }
    }
    return defaultSettings #returns the dict with all default settings

def plugin_main(self, path):
    #TODO
    mp3_info = MP3File(path) #info stored from the MP3 file

    try:
        infoData = mp3_info.get_tags().ID3TagV2 #storing the tags data
    except AttributeError: 
        return {}#returns an empty dict if there is an AttributeError (when there are no tags)

    if self._settings["mp3"]["extended_data"]:
        return infoData #returns infoData if the boolean in the settings of the object is set to true
    else:
        returnData = {} #empty dict of return data
        for dataKey in self._settings["mp3"]["simple_media_tags"]: #puts all data in the settings in teh returnData dict, unless there is an AttributeError (in which it passes)
            try:
                returnData[dataKey] = eval("infoData."+dataKey)
            except AttributeError:
                pass
        return returnData #returns the dict
