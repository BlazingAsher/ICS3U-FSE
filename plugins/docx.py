from docx import Document,document #Used for all properties

def get_id():
    return "com.satarora.docx"

def get_handlers():
    return ["application\/vnd.openxmlformats-officedocument.wordprocessingml.document"] ##GET HELP FOR HANDLER

def get_mappings():
    docxMap = {
        "docx" : "application\/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    return docxMap

def get_default_settings():
    defaultSettings = {}
    return defaultSettings

def plugin_main(self,path):
    document = Document(path)
    core_properties = document.core_properties
    properties = {
        "author" : core_properties.author,
        "last_modified_by" : core_properties.last_modified_by,
        "title" : core_properties.title
    }
    return properties
    
