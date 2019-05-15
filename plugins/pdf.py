from pdfrw import PdfReader
def get_id():
    return "com.satarora.pdf"
def get_handlers():
    return ["application\/pdf"]
def get_mappings():
    pdfMap = {
        "pdf" : "application/pdf"
    }
    return pdfMap
def get_default_settings():
    defaultSettings = {
        
    }
    return defaultSettings
def plugin_main(self,path):
    x = PdfReader(path)
    properties = {
        "pages" : len(x.pages),
        "source" : x.Info
    
    }
    return properties
