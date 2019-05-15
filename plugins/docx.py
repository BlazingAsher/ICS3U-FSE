from win32com.client import Dispatch #Used to show number of pages
from docx import Document,document #Used for all other properties

#open Word
word = Dispatch('Word.Application')
word.Visible = False
word = word.Documents.Open(doc_path)

#get number of sheets
word.Repaginate()
num_of_sheets = word.ComputeStatistics(2)

def get_id():
    return "com.satarora.docx"
def get_handlers():
    return ["application\/vnd.openxmlformats-officedocument.wordprocessingml.document"] ##GET HELP FOR HANDLER
def get_mappings():
    docxMap = {
        "docx" : "application\/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
def get_default_settngs():
    defaultSettings = {
        
    }
    return defaultSettings
def plugin_main(self,path):
    doc = Document(path,"rb")
    document = Document(doc)
    core_properties = document.core_properties
    properties = {
        "author" : core_properties.author,
        "last modified" : core_properties.last_modified_by,
        "title" : core_properties_title
        "pages" : num_of_sheets
        
    }
    return properties
    
