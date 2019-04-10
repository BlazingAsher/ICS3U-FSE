from PIL import Image, ExifTags
def get_id():
    return "com.davidhui.image"

def get_handlers():
    return ["image\/.*"]

def plugin_main(self, path):
    print("Image!")
    # Open the image to get its attributes
    img = Image.open(path)
    try:
        if img._getexif():
            totalExif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS }
            if self._settings["image"]["extended_exif"]:
                return totalExif
            else:
                returnExif = {}
                for exifKey in self._settings["image"]["simple_exif_tags"]:
                    try:
                        returnExif[exifKey] = totalExif[exifKey]
                    except KeyError:
                        pass
                
                return returnExif
        else:
            return {}
    except AttributeError:
        return {}
