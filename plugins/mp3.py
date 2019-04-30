from mp3_tagger import MP3File, VERSION_1, VERSION_2, VERSION_BOTH
def get_id():
    return "com.davidhui.mp3"

def get_handlers():
    return ["audio\/mpeg"]

def get_mappings():
    mediaMap = {
        "mp3": "audio/mpeg"
    }
    return mediaMap

def get_default_settings():
    defaultSettings = {
        "mp3": {
            "extended_data": False,
            "simple_media_tags": ["artist", "album","track","year","genre"]
        }
    }
    return defaultSettings

def plugin_main(self, path):
    #TODO
    mp3_info = MP3File(path)

    try:
        infoData = mp3_info.get_tags().ID3TagV2
    except AttributeError:
        return {}

    if self._settings["mp3"]["extended_data"]:
        return infoData
    else:
        returnData = {}
        for dataKey in self._settings["mp3"]["simple_media_tags"]:
            try:
                returnData[dataKey] = eval("infoData."+dataKey)
            except AttributeError:
                pass
        return returnData
