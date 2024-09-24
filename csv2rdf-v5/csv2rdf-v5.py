#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           September 2024
# License:        GPL v3
#============================================
#!/usr/bin/env python3

import getopt, sys, csv, configparser, os.path, traceback, time, os
from os.path import exists

#Conditional import
try:
    import progressbar2 #Debian
except ImportError:
    import progressbar as progressbar2 #Windows

from rdflib import Graph, Literal, URIRef, RDF, RDFS, BNode, XSD
from datetime import date, timedelta

import sys
sys.path.append('.')
from tools import myprint, Timer, interrupt, countLinesInCSVFile

#ENCODING = "utf8"
ENCODING = "latin_1"

#----------------------------------------- Mandatory fields per csv file
FILE = 'file' #full path or relative path
DOMAIN = 'domain'
DELIMITER = 'delimiter'
SEMANTICS = 'semantics'
ACTIVE = 'active'

#------------------------------------------------- Grammar fields: keys
MULTITREATMENT = '$'
CELLROLE = 'cellrole'
CELLTYPE = 'celltype'
COLUMNTYPE = 'columntype'

#------------------------------------------------- Grammar fields: values
IGNORE = 'ignore'
PKEY = 'pkey'
SUBJECT = 'subject'
OBJECT = 'object'

# types
GRAMMAR_TYPES = {
    "string":  XSD.string, 
    "integer": XSD.integer,
    "float":   XSD.float,
    "date":    XSD.date
}


#--- Alteration modes
NONE = 0
MAP_ALL = 1
MAP_PART = 2
EXTRACT = 3
PREFIX = 4


#================================================= format_date: not used
DATE_PREDICATE = "date_created"
TODAY = str(date.today())
def date_stamp(store, domain, URI):
    store.add((URI,
               URIRef(domain + DATE_PREDICATE),
               URIRef(Literal(TODAY, datatype=XSD.date))))


#================================================= to-define-in-ontology
ONTO_REQ = "to-define-in-ontology.txt"
DEFINE = []

def to_define_in_ontology(*args):
    global DEFINE
    for str in args:
        if str not in DEFINE:
            DEFINE.append(str)

def dump_define():
    global DEFINE
    with open(ONTO_REQ, 'w', encoding=ENCODING, newline='\n') as output:
        for str in DEFINE:
            output.write(str + '\n')


#============================================ Source
class Source():
    def __init__(self, name, file, domain, delim, semantics, active):
        self.name = name
        self.file = file
        self.domain = domain
        self.delim = delim
        self.semanticfile = semantics
        self.active = active
    def print(self):
        myprint("-----------")
        myprint("Source: " +  self.name)
        myprint("File: " + self.file)
        myprint("Domain: " + self.domain)
        myprint("Delim: " + self.delim)
        myprint("Active: " + str(self.active))
        myprint("Semantics: " + self.semanticfile)


#============================================ Options: main conf file
class Options():
    '''
    self.sources = [ Source1, Source 2, ...]
    We keep only the active sources
    '''
    #--- __init__
    def __init__(self, filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        config = configparser.ConfigParser()
        config.read(filename)
        self.sources = []
        for elem in config.sections():
            if ACTIVE in config[elem]:
                if config[elem][ACTIVE] == "True":
                    source = Source(elem,
                                    config[elem][FILE],
                                    config[elem][DOMAIN],
                                    config[elem][DELIMITER],
                                    config[elem][SEMANTICS],
                                    config[elem][ACTIVE])
                    self.sources.append(source)
        myprint("Config file read: found "
              + str(len(config.sections()))
              + " source(s) and "
              + str(len(self.sources))
              + " active(s)")
    #--- print
    def print(self):
        for source in self.sources:
            source.print()

            
#================================================= RDFStore
class RDFStore():
    '''
    This class wraps the RDF store proposed by rdflib
    TODO Add more output formats in dump_store
    '''
    def __init__(self, name):
        # Expecting name to be something like "toto"
        self.name = name
        self.store = Graph()
    def get_store(self):
        return self.store
    def add(self, triple):
        self.store.add(triple)
    def dump(self):
        myprint("Dumping store")
        tim = Timer()
        self.store.serialize(self.name, format='turtle')
        tim.stop()
        myprint("Store dumped")



#================================================= format_predicate
def format_URI(pred):
    new = ''
    for i, c in enumerate(pred):
        if c in [' ', '-', '/', '\\', '(',')',',',
                 '"', "'", "<", ">", "|", "{", "}",
                 "^", "#", "$", "*", ".", "`", "+",
                 "=", "%"]:
            new += '_'
        else:
            new += pred[i]
    return new


#================================================================ Column, root class
class Column():
    def __init__(self, domain, columnname, lists, cellrole, celltype, columntype, ispkey = False):
        self.domain = domain
        #name of the column in CSV must begin by the same
        #(case of the $x en of sections)
        self.columnname = columnname 
        self.lists = lists
        self.cellrole = cellrole
        self.celltype = celltype
        self.columntype = columntype
        self.ispkey = ispkey
        self.csvindex = -1
    def generate_triples(self, store, cellvalue, pkeyvalue, pkeytype):
        pass


#================================================================ PKey
class PKey(Column):
    # for this class, cellvalue and pkvalue are identical, pkeyvalue is not used
    def generate_triples(self, store, cellvalue, pkeyvalue, pkeytype):
        # 1. format the predicate because the value can be dirty
        cellvalueURI  = URIRef(self.domain + format_URI(cellvalue))
        celltypeURI   = URIRef(self.domain + format_URI(self.celltype))
        
        # 2. associate original values as a label
        store.add(( cellvalueURI, RDFS.label, Literal(cellvalue)))
        store.add(( celltypeURI,  RDFS.label, Literal(self.celltype)))
        
        # 3. to keep track of the ontology definitions required
        to_define_in_ontology(celltypeURI.n3())

        # 4. Type the pkey
        store.add(( cellvalueURI, RDF.type, celltypeURI))


#================================================================ PKey
class URIColumn(Column):
    def __init__(self, domain, name, lists, cellrole, celltype, columntype, pkey = False):
        super().__init__(domain, name, lists, cellrole, celltype, columntype, False)
        self.altermode = NONE
        self.maptable = None
        self.myinfchar = -1
        self.mymaxchar = -1
        self.prefix = ""
        # management of alteration of cell value
        cellgrammar = self.cellrole.split(',')
        if len(cellgrammar) != 1:
            # ALTER 1: mapping the value of the cell
            # or the value of a part of the cell with a key/value list
            if cellgrammar[1].startswith("map("):
                args = (cellgrammar[1][4:-1]).split(';')
                # expecting 2 arguments 'all;*suppliers*' or '1:2;*configs*'
                self.maptable = lists[args[1]] #getting dict - dict object
                if args[0] == 'all':
                    self.altermode = MAP_ALL
                else:
                    [myinf,mymax] = args[0].split(":")
                    self.myinfchar = int(myinf) if (myinf != "") else 0
                    self.mymaxchar = int(mymax) if (mymax != "") else 0
                    self.altermode = MAP_PART
            # ALTER 2: extracting info from the cell value itself
            elif cellgrammar[1].startswith("extract("):
                args = cellgrammar[1][8:-1] #expecting one argument '-3:' or '1:2'
                [myinf,mymax] = args.split(":")
                self.myinfchar = int(myinf) if (myinf != "") else 0
                self.mymaxchar = int(mymax) if (mymax != "") else 0
                self.altermode = EXTRACT
            # ALTER 3: adding a prefix to the cell value
            elif cellgrammar[1].startswith("prefix("):
                self.prefix = cellgrammar[1][7:-1] #expecting one arg such as 'toto_' or 'gnu_'
                self.altermode = PREFIX
            else:
                myprint("Error: Unknown command: '" + cellgrammar[1]
                      + "' in grammar file. Exiting...")
                exit(0)            
    #--- Alter modes
    def alter_cell_value(self, cellvalue):
        if cellvalue.strip() == "":
            return "" #TODO: ne pas créer de triple si la cellule est vide
        if self.altermode == NONE:
            return cellvalue
        # ALTER 1: mapping the value of the cell
        if self.altermode == MAP_ALL:
            if cellvalue.lower() in self.maptable: #TODO: regarder la cohérence de "lower"
                return self.maptable[cellvalue.lower()]
            else:
                myprint("Warning: " + cellvalue + " not in maptable")
                return cellvalue #unmapped
        if self.altermode == MAP_PART:
            temp = cellvalue[self.myinfchar:self.mymaxchar].lower()
            if temp in self.maptable:
                return self.maptable[temp]
            else:
                myprint("Warning: " + cellvalue + " not in maptable")
                return cellvalue #unmapped
        # ALTER 2: extracting info from the cell value itself
        if self.altermode == EXTRACT:
            return cellvalue[self.myinfchar:self.mymaxchar]
        # ALTER 3: adding a prefix to the cell value
        if self.altermode == PREFIX:
            return cellvalue + self.prefix
        myprint("Error: we should never get here!")
            
    #--------------generate triples
    def generate_triples(self, store, cellvalue, pkeyvalue, pkeytype):
        # 0. managing the commands of alteration 
        newcellvalue = self.alter_cell_value(cellvalue)

        # 1. generate all URIs
        cellvalueURI  = URIRef(self.domain + format_URI(newcellvalue))
        celltypeURI   = URIRef(self.domain + format_URI(self.celltype))
        columntypeURI = URIRef(self.domain + format_URI(self.columntype))

        pkeyvalueURI = URIRef(self.domain + format_URI(pkeyvalue))
        pkeytypeURI  = URIRef(self.domain + format_URI(pkeytype))
        
        # 2. capture the rough string values in Literal
        store.add((cellvalueURI,  RDFS.label, Literal(newcellvalue)))
        store.add((celltypeURI,   RDFS.label, Literal(self.celltype)))
        store.add((columntypeURI, RDFS.label, Literal(self.columntype)))
        
        # 3. to keep track of the ontology definitions required
        to_define_in_ontology(celltypeURI.n3(), columntypeURI.n3())

        # 4. type the cell value
        store.add((cellvalueURI, RDF.type, celltypeURI))

        # 5. create the real triple + domain/range
        if self.cellrole == SUBJECT:
            store.add((cellvalueURI,  columntypeURI, pkeyvalueURI))
            store.add((columntypeURI, RDFS.domain,   celltypeURI))
            store.add((columntypeURI, RDFS.range,    pkeytypeURI))
        else:
            store.add((pkeyvalueURI,  columntypeURI, cellvalueURI))
            store.add((columntypeURI, RDFS.domain,   pkeytypeURI))
            store.add((columntypeURI, RDFS.range,    celltypeURI))


#====================================================== LiteralColumn
class LiteralColumn(Column):
    def generate_triples(self, store, cellvalue, pkeyvalue, pkeytype):
        # 1. create URIs
        columntypeURI = URIRef(self.domain + format_URI(self.columntype))
        pkeyvalueURI  = URIRef(self.domain + format_URI(pkeyvalue))
        pkeytypeURI   = URIRef(self.domain + format_URI(pkeytype))

        # 2. describe the columntype
        store.add(( columntypeURI, RDFS.label, Literal(self.columntype)))
        
        # 3. to define in ontology 
        to_define_in_ontology(columntypeURI.n3())
        
        # 4. create the real triple and domain/range
        store.add((pkeyvalueURI,
                   columntypeURI,
                   Literal(cellvalue, datatype = self.celltype)))
        store.add((columntypeURI, RDFS.domain, pkeytypeURI))
        store.add((columntypeURI, RDFS.range,  RDFS.Literal))


#================================================= Grammar
class Grammar():
    # The Grammar constructor is a factory of column objects and list objects
    def __init__(self, filename, domain, delim):
        self.filename = filename
        self.domain = domain
        self.delim = delim
        # self.columns = { name1 : Column1, name2: Column2, ... }
        self.columns = {}
        # when exploring the lines of the CSV, we need to have the columns ordered
        # the same way than the CSV
        self.orderedcols = []
        # self.lists = { name1 : dict1, name2 : dict2, ... }
        self.lists = {}
        # record pkey = PKey()
        self.pkey = None
        self.pkeyindex = -1

        #read sections
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        config = configparser.ConfigParser()
        config.read(filename)
        # 1. first we get mapping lists
        for elem in config.sections():
            if elem.startswith('*') and elem.endswith('*'):
                mydict = dict()
                 # get the key: values defined in grammar
                for key in config[elem]:
                    mydict[key] = config[elem][key]
                self.lists[elem] = mydict
        # 2. then we get other sections that could need mapping lists
        # we play the role of a factory
        for elem in config.sections():
            if elem.startswith('*'):
                continue
            #read all elements in grammar section
            mydict = dict()
            for key in config[elem]:
                mydict[key] = config[elem][key]
            #pkey
            if CELLROLE not in mydict:
                myprint("Error: '" + CELLROLE
                      + "' is mandatory in grammar section "
                      + elem + ". Exiting...")
                exit()
            # We do not record the Column and will not create a class
            if mydict[CELLROLE] == IGNORE:
                continue
            if mydict[CELLROLE] == PKEY:
                self.pkey = PKey(domain,
                                 elem,
                                 self.lists,
                                 PKEY,
                                 mydict[CELLTYPE],
                                 "",
                                 True)
                self.columns[elem] = self.pkey
                continue
            if not CELLTYPE in mydict:
                myprint("Error: '" + CELLTYPE
                      + "' is mandatory in grammar section. Exiting...")
                exit()
            if mydict[CELLTYPE] in GRAMMAR_TYPES:
                thetype = GRAMMAR_TYPES[mydict[CELLTYPE]]
                self.columns[elem] = LiteralColumn(domain,
                                                   elem,
                                                   self.lists,
                                                   mydict[CELLROLE],
                                                   thetype,
                                                   mydict[COLUMNTYPE])
            else:
                self.columns[elem] = URIColumn(domain,
                                               elem,
                                               self.lists,
                                               mydict[CELLROLE],
                                               mydict[CELLTYPE],
                                               mydict[COLUMNTYPE])
                
        # Error cases and reporting
        myprint("Found: "
              + str(len(config.sections()))
              + " sections and "
              + str(len(self.lists))
              + " lists")
        if self.pkey == None:
            myprint("Error: pkey not found in grammar file. Exiting...")
            exit()

    #----------------------------------------------------semantic_parser
    def semantic_parser(self, csvfile, store):
        count = 0
        try:
            reader = csv.reader(
                open(csvfile, "r", encoding='utf-8', errors='ignore'),
                delimiter=self.delim)
            #--- begin tech
            tim = Timer()
            nblines = countLinesInCSVFile(csvfile)
            bar = progressbar2.ProgressBar(max_value=nblines)
            #--- end tech
            header = None
            pkeyindex = -1
            for row in reader:
                bar.update(count)
                # 1. Management of header
                if count == 0:
                    header = row
                    # 1. the grammar file section names should be included into the headers
                    # note : it is not mandatory to take all the headers
                    for col in self.columns:
                        # management of the ending $1 $2 etc.
                        # We only support 9 diff.treatments on the same cell value
                        # $1, ..., $9
                        colobj = self.columns[col]
                        if colobj.columnname[-2] == MULTITREATMENT: 
                            temp = colobj.columnname.split(MULTITREATMENT)[0]
                        else:
                            temp = colobj.columnname
                        if temp not in header:
                            myprint("Error: grammar section name '"
                                  + colobj.columnname
                                  + "' not found in CSV file. Exiting...")
                            exit()
                        i = 0
                        for headerelem in header:
                            if headerelem == temp:
                                colobj.index = i
                                if colobj.ispkey:
                                    pkeyindex = i
                                break
                            i += 1
                    if pkeyindex == -1:
                        myprint("Error: could not find pkey in CSV header. Exiting...")
                        exit()
                    # increment CSV line number
                    count +=1
                else:
                    pkeyvalue = row[pkeyindex]
                    # general case: standard row
                    for col in self.columns:
                        colobj = self.columns[col]
                        cellvalue = row[colobj.index]
                        if cellvalue.strip() == "":
                            continue
                        else:
                            colobj.generate_triples(store,
                                                    cellvalue,
                                                    pkeyvalue,
                                                    self.pkey.celltype)
                    count +=1
            tim.stop()
        except csv.Error as e:
            myprint("Error caught in loading csv file: " + f)
            myprint(e)
            sys.exit(1)
        myprint("Information: " + str(count) + " csv row converted")


#================================================= usage
def usage():
    print("Utility to transform CSV files into RDF files")
    print("Usage: \n $ csv2rdf -c [CONFIG] -i")
    print("CONFIG must be an '.ini' file")
    print("'-i' starts the step by step processing")
    sys.exit(0)


def to_int(a, range):
    '''
    Returns always a proper integer in the expected range.
    Default value is 0.
    '''
    try:
        i = int(a)
        if i in range:
            return i
        else:
            return 0
    except ValueError:
        return 0


#================================================= main
def main():
    try:
        # Option 't' is a hidden option
        opts, args = getopt.getopt(sys.argv[1:], "c:h",
                                   ["conf=", "help"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    if len(opts) == 0:
        usage()
    options = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-c", "--conf"):
            options = a
            myprint("Configuration file: " + a)

    # default option file name if no options are provided
    if options == None:
        usage()
        sys.exit()
    opt = Options(options)
    opt.print()

    # main loop
    globaltimer = Timer()
    for source in opt.sources:
        # determine name of the triplestore
        output = source.name + ".ttl"
        store = RDFStore(output)

        # Parsing the grammar file
        gram = Grammar(source.semanticfile, source.domain, source.delim)

        # Generating triples
        gram.semantic_parser(source.file, store)

        # Dumping the triplestore
        store.dump()

    myprint("Dumping " + ONTO_REQ)
    dump_define()
    myprint("Done")
    globaltimer.stop()
    myprint("Goodbye")
    return


if __name__ == '__main__':
    main()

