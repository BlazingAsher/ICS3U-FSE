def get_id():
    return "com.davidhui.video"

def get_handlers():
    return ["video\/.*"]

def plugin_main(self, path):
    info     = MediaInfo(filename = path, cmd=self.ffprobe, mode='ffprobe')
    infoData = info.getInfo()

    if self._settings["video"]["extended_videodata"]:
        return infoData
    else:
        returnData = {}
        for dataKey in self._settings["video"]["simple_video_tags"]:
            try:
                returnData[dataKey] = infoData[dataKey]
            except KeyError:
                pass
        return returnData
