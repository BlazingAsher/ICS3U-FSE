from environs import Env
from MediaInfo import MediaInfo
env = Env()
env.read_env()
FFPROBE = env("FFPROBE")
def get_id():
    return "com.davidhui.media"

def get_handlers():
    return ["video\/.*", "audio\/.*"]

def get_mappings():
    return {}

def get_default_settings():
    defaultSettings = {
        "media": {
            "extended_data": False,
            "simple_media_tags": ["container", "duration","bitrate","haveVideo","haveAudio","videoCodec","videoWidth","videoHeight","audicCodec"]
        }
    }
    return defaultSettings

def plugin_main(self, path):
    info     = MediaInfo(filename = path, cmd=FFPROBE, mode='ffprobe')
    infoData = info.getInfo()

    if self._settings["media"]["extended_data"]:
        return infoData
    else:
        returnData = {}
        for dataKey in self._settings["media"]["simple_media_tags"]:
            try:
                returnData[dataKey] = infoData[dataKey]
            except KeyError:
                pass
        return returnData
