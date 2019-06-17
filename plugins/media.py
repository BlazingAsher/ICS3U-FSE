from environs import Env
from MediaInfo import MediaInfo #importing necessary modules
env = Env() #setting the environment
env.read_env()
FFPROBE = env("FFPROBE")
def get_id():
    return "com.davidhui.media" #getting id

def get_handlers():
    return ["video\/.*", "audio\/.*"] #MIME types

def get_mappings():
    return {} #mappings are just an empty dict

def get_default_settings():
    defaultSettings = { #dictionary of the defaultSettings
        "media": {
            "extended_data": False,  #extended_data set to false
            "simple_media_tags": ["container", "duration","bitrate","haveVideo","haveAudio","videoCodec","videoWidth","videoHeight","audicCodec"] #media tags used 
        }
    }
    return defaultSettings #returns settings

def plugin_main(self, path):
    info     = MediaInfo(filename = path, cmd=FFPROBE, mode='ffprobe') #information stored
    infoData = info.getInfo() #all data in the info variable written in infoData

    if self._settings["media"]["extended_data"]:
        return infoData #just returns infoData if the variable in the element's settings (at that place) is true
    else:
        returnData = {} #empty dict
        for dataKey in self._settings["media"]["simple_media_tags"]: #loop thru each ke
            try:
                returnData[dataKey] = infoData[dataKey] #having returnData get the data from the infoData
            except KeyError: #passes in the case of a KeyError
                pass
        return returnData #returns the data
