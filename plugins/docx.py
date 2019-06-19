from docx import Document,document #Used for all properties

def get_id():
    return "com.satarora.docx" #getting id for document

def get_handlers():
    return ["application\/vnd\.openxmlformats-officedocument\.wordprocessingml\.document"] ##support for MIME type

def get_mappings():
    docxMap = {
        "docx" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document" #types of document applications, which are only regular document
    }
    return docxMap

def get_default_settings():
    defaultSettings = {}
    return defaultSettings #no extra default settings needed besides the standard

def plugin_main(self,path):
    document = Document(path) #setting a variable to the document located at the document's path
    core_properties = document.core_properties #the core properties are stored in this variable
    properties = { #dict of properties
        "author" : core_properties.author, #authour of file
        "last_modified_by" : core_properties.last_modified_by, #last modified by
    }
    return properties #returns the properties given
    
