from pdfrw import PdfReader #importing necessary modules
def get_id():
    return "com.satarora.pdf" #id for pdf
def get_handlers():
    return ["application\/pdf"] #MIME type for pdf files
def get_mappings():
    pdfMap = {
        "pdf" : "application/pdf" #dict of mappings, which holds the MIME type of the one type of pdf (which is .pdf)
    }
    return pdfMap
def get_default_settings():
    defaultSettings = {
        #no necessary default settings, this is just template code
    }
    return defaultSettings #returns the dict of default settings, which is empty
def plugin_main(self,path):
    x = PdfReader(path) #varaible with the pdf reader (holding properties) from the given path
    properties = { #dictionary of properties
        "pages" : len(x.pages), #number of pages
        "source" : x.Info #source of the pdf file
    
    }
    return properties #returns properties, as there is never a case where there is something wrong
