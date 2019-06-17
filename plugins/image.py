from PIL import Image, ExifTags #importing modules necessary for file proeprties
def get_id():
    return "com.davidhui.image" #getting the image id

def get_handlers():
    return ["image\/.*"] #MIME type for image file

def get_mappings():
    imageMap = { #this includes support for .png and .jpg image types
        "jpg": "image/jpeg", 
        "png": "image/png"
    }
    return imageMap

def get_default_settings():
    defaultSettings = {
        "image": {
            "extended_exif": False,
            "simple_exif_tags": ["DateTimeOriginal","Make","Model","Flash","UserComment","Software","DateTime","LensModel"] #default settings that are not automatically made with the os in the other program
        }
    }
    return defaultSettings

def plugin_main(self, path):
    #print("Image!")
    # Open the image to get its attributes
    img = Image.open(path) #olpening the image at that path
    try: 
        if img._getexif(): #tries to got exif tags of the image
            totalExif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS }  #a dict of all exif items that are in the exif tags
            if self._settings["image"]["extended_exif"]:
                return totalExif #checks if the settinga at that path is set equal to true, and returns totalExif if it is
            else:
                returnExif = {} #empty dict
                for exifKey in self._settings["image"]["simple_exif_tags"]: #for each key in the simple_exif_tags
                    try:
                        returnExif[exifKey] = totalExif[exifKey] #stores each value of totalExif[exifKey] in returnExif
                    except KeyError: #passes in the case of a key error
                        pass
                
                return returnExif
        else:
            return {} #returns an empty dict otherwise
    except AttributeError: #returns an empty dict in the case of an attribute error
        return {}
