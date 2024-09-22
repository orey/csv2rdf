#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           August 2024
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

from tools import myprint

#----------------------------------------- Mandatory fields per csv file
FILE = 'file' #full path or relative path
DOMAIN = 'domain'
DELIMITER = 'delimiter'
SEMANTICS = 'semantics'
ACTIVE = 'active'

#------------------------------------------------- Grammar fields: keys
CELLROLE = 'cellrole'
CELLTYPE = 'celltype'
COLUMNTYPE = 'columntype'

#------------------------------------------------- Grammar fields: values
IGNORE = 'ignore'
PKEY = 'pkey'
SUBJECT = 'subject'
OBJECT = 'object'

# types
STRING = 'string'
INTEGER = 'integer'
FLOAT = 'float'
DATE = 'date'





DATE_PREDICATE = "date_created"
TODAY = str(date.today())

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
        print("-----------")
        print("Source: " +  self.name)
        print("File: " + self.file)
        print("Domain: " + self.domain)
        print("Delim: " + self.delim)
        print("Active: " + str(self.active))
        print("Semantics: " + self.semanticfile)


#============================================ Options: main conf file
class Options():
    '''
    self.sources = [ Source1, Source 2, ...]
    We keep only the active sources
    '''
    #-----------------------------------------------__init__
    def __init__(self, filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        config = configparser.ConfigParser()
        config.read(filename)
        self.sources = []
        for elem in config.sections():
            if self.ACTIVE in config[elem]:
                if config[elem][self.ACTIVE] == "True":
                    source = Source(elem,
                                    config[elem][self.FILE],
                                    config[elem][self.DOMAIN],
                                    config[elem][self.DELIMITER],
                                    config[elem][self.SEMANTICS],
                                    active)
                    self.sources.append(source)
        print("Config file read: found "
              + str(len(config.sections()))
              + " source(s) and "
              + str(len(self.sources))
              + " active(s)")
    #-----------------------------------------------print
    def print(self):
        for source in self.sources:
            source.print()
    

#================================================= RDFStore
class RDFStoreChunks():
    '''
    This class wraps the RDF store proposed by rdflib
    TODO Add more output formats in dump_store
    '''
    def __init__(self, name, chunks=False):
        # Expecting name to be something like "toto"
        self.chunks = chunks
        # We have at leats one file
        self.fileindex = 0
        self.name = name
        # These variables are not useful in case we have no CPU problems
        self.counter = 0
        self.MAX = 20000
        # To check before writing
        self.interrupt = interrupt
        # We can have many stores
        self.stores = [Graph()]
    def get_nextname(self):
        self.fileindex += 1
        return self.name.split('.')[0] + '-' + str(self.fileindex)  + '.ttl'
    def get_store(self):
        return self.store

    def add(self, triple):
        if VERBOSE: print(triple)
        if INTERRUPT: interrupt()
        self.stores[self.fileindex].add(triple)
        if self.chunks:
            self.counter += 1
            if self.counter >= self.MAX:
                self.fileindex +=1
                self.stores.append(Graph())
                self.counter = 0
            
    def dump(self):
        print("Dumping stores")
        tim = Timer()
        for i in range(0, len(self.stores)):
            self.stores[i].serialize(self.name.split('.')[0] + '-' + str(i)  + '.ttl',
                            format='turtle')
        tim.stop()
        print("Stores dumped")


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
        if VERBOSE:
            (a, b, c) = triple
            print(a.n3() + " " + b.n3() + " " + c.n3() + " .")
        if INTERRUPT: interrupt()
        self.store.add(triple)
    def dump(self):
        print("Dumping store")
        tim = Timer()
        self.store.serialize(self.name, format='turtle')
        tim.stop()
        print("Store dumped")



#================================================= format_predicate
def format_predicate(pred):
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


#================================================= format_date
def date_stamp(store, domain, URI):
    store.add((URI,
               URIRef(domain + DATE_PREDICATE),
               URIRef(Literal(TODAY, datatype=XSD.date))))

#================================================= generate_type_triples
def generate_type_triples(lst, store, domain, isClass):
    # First, all types are instances of a super class
    for i in range(0, len(lst)):
        if isClass:
            store.add((URIRef(domain + lst[i]), RDF.type, RDFS.Class))
        else:
            store.add((URIRef(domain + lst[i]), RDF.type, RDF.Property))
    # generate the chain of types
    if len(lst) < 1:
        return
    for i in range(0, len(lst)-1):
        lower = lst[i]
        new = lst[i+1]
        previoustype = URIRef(domain + lst[i])
        nexttype     = URIRef(domain + lst[i+1])
        if isClass:
            store.add((previoustype, RDFS.subClassOf, nexttype))
        else:
            store.add((previoustype, RDFS.subPropertyOf, nexttype))


#================================================= Column
class ColumnOld():
    to_ignore = False
    is_pkey = False
    is_pkey_descr = False
    mydict = {}

    #------------------------------------------__init__
    def __init__(self,mydict):
        self.mydict = mydict
        if mydict['cell'] == 'ignore':
            self.to_ignore = True
        elif mydict['cell'] == 'pkey':
            self.is_pkey = True
            self.pkeytype = mydict['celltypes'].split(',')[0]
        elif mydict['celltypes'] == 'string':
            self.is_pkey_descr = True
            
    #------------------------------------------generate_triples
    def generate_triples(self,store,domain,cell,pkey,pkeytype,lists):
        #=== 3 particular cases===
        # A. Ignore the cell
        if self.to_ignore:
            #should not happen because ignorable sectons are intercepted before
            return
        # B. The cell is the description of the  pkey, so we generate a rdfs:comment
        if self.is_pkey_descr:
            store.add((URIRef(domain + pkey),
                       RDFS.comment,
                       Literal(cell)))
            return
        # C. This is the kpey cell, so it is simpler than the other cells
        if self.is_pkey:
            mytype = self.mydict['celltypes'].split(',')[0]
            cellpred = format_predicate(cell)
            store.add((URIRef(domain + cellpred), RDFS.label, Literal(cell)))
            mytypeobj = format_predicate(mytype)
            store.add((URIRef(domain + mytypeobj), RDFS.label, Literal(mytype)))
            store.add((URIRef(domain + cellpred),
                       RDF.type,
                       URIRef(domain + mytypeobj)))
            # removing date generation
            #date_stamp(store, domain, URIRef(domain + format_predicate(cell)))
            generate_type_triples(self.mydict['celltypes'].split(','), store, domain, True)
            # there are neither 'columns' nor column types
            return

        #=== General case ===
        cellgrammar = self.mydict['cell'].split(',')     # simple or with command
        celltypes = self.mydict['celltypes'].split(',')  # hierarchy of types, last one being rdf/rdfs
        coltypes = self.mydict['columntypes'].split(',') # hierarchy of types, last one being rdf/rdfs

        # init before treatments
        newcell = ""
        # There are 3 ways to alter the cell value (there could be much more!)
        if len(cellgrammar) != 1:
            newcell = ""
            # ALTER 1: mapping the value of the cell or the value of a part of the cell with a key/value list
            if cellgrammar[1].startswith("map("):
                args = (cellgrammar[1][4:-1]).split(';')
                # expecting 2 arguments 'all;*suppliers*' or '1:2;*configs*'
                if VERBOSE:
                    print("cellgrammar = ")
                    print(cellgrammar[1])
                    print("args = ")
                    print(args)
                maptable = lists[args[1]] #getting dict
                if args[0] == 'all':
                    if cell.lower() in maptable:
                        newcell = maptable[cell.lower()]
                    else:
                        #print("Strange: " + cell + " is not in maptable")
                        #print(maptable)
                        #interrupt()
                        if cell.strip() != "":
                            newcell = cell
                        else:
                            newcell = "STRANGE"
                else:
                    [myinf,mymax] = args[0].split(":")
                    myinfchar = int(myinf) if (myinf != "") else 0
                    mymaxchar = int(mymax) if (mymax != "") else 0
                    temp = cell[myinfchar:mymaxchar].lower()
                    if temp in maptable:
                        newcell = maptable[temp]
                    else:
                        #print("Strange: " + temp + " is not in maptable")
                        #print(maptable)
                        #interrupt()
                        if temp.strip() != "":
                            newcell = temp
                        else:
                            newcell = "STRANGE"
            # ALTER 2: extracting info from the cell value itself
            elif cellgrammar[1].startswith("extract("):
                args = cellgrammar[1][8:-1] #expecting one argument '-3:' or '1:2'
                [myinf,mymax] = args.split(":")
                myinfchar = int(myinf) if (myinf != "") else 0
                mymaxchar = int(mymax) if (mymax != "") else 0
                newcell = cell[myinfchar:mymaxchar]
            # ALTER 3: adding a prefix to the cell value
            elif cellgrammar[1].startswith("prefix("):
                args = cellgrammar[1][7:-1] #expecting one arg such as 'toto_' or 'gnu_'
                newcell = args + cell
            else:
                print("Unknown command: " + cellgrammar[1] + " Exiting...")
                exit(0)
        else:
            # ALTER 0: we keep the original value
            newcell = cell
        
        # Main generation algorithm
        # 0. Define readable variables
        prednewcell = format_predicate(newcell)
        store.add((URIRef(domain + prednewcell), RDFS.label, Literal(newcell)))
        rdfcell     = URIRef(domain + prednewcell)

        rdfcelltype = URIRef(domain + format_predicate(celltypes[0]))

        rdfcoltype  = URIRef(domain + format_predicate(coltypes[0]))

        predpkey = format_predicate(pkey)
        store.add((URIRef(domain + predpkey), RDFS.label, Literal(pkey)))
        rdfpkey     = URIRef(domain + predpkey)
        
        rdfpkeytype = URIRef(domain + format_predicate(pkeytype))
                         
        # 1. we have to type the cell
        store.add((rdfcell, RDF.type, rdfcelltype))
        
        # 2. we generate the standard triple + the domain and range of the relationship

        # The 2 first cases are standard and should be used 100% of the case
        if cellgrammar[0] == 'subject':
            # standard triple: cell is at the intersection of line and column
            store.add((rdfcell,    rdfcoltype,  rdfpkey))
            store.add((rdfcoltype, RDFS.domain, rdfcelltype))
            store.add((rdfcoltype, RDFS.range,  rdfpkeytype))
            generate_type_triples(celltypes, store, domain, True)
            generate_type_triples(coltypes,  store, domain, False)
        elif cellgrammar[0] == 'object':
            store.add((rdfpkey,    rdfcoltype,  rdfcell))
            store.add((rdfcoltype, RDFS.domain, rdfpkeytype))
            store.add((rdfcoltype, RDFS.range,  rdfcelltype))
            generate_type_triples(celltypes, store, domain, True)
            generate_type_triples(coltypes,  store, domain, False)
        else:
            # Maybe we'll need this case to be implemented one day but I have doubts about it
            if cellgrammar[0] == 'predicate':
                print("Not supported. Cell cannot be a predicate but only a subject or an object")
                exit(0)
        #date_stamp(store, domain, rdfcell)           
        if VERBOSE: print("Done for cell: " + cell)


class Column():
    def __init__(self, domain, name, cellrole,celltype, columntype, pkey = False):
        self.domain = domain
        self.columnname = name #name of the column in CSV must be the exact same as the name in the grammar section
        self.cellrole = cellrole
        self.celltype = celltype
        self.columntype = columntype
        self.pkey = pkey
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        pass

class PKey(Column):
    def get_IRI(self):
        
    # for this class, cellvalue and pkvalue are identical, pkeyvalue is not used
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        # 1. Type the pkey
        store.add((
            URIRef(domain+cellvalue),
            RDF.type,
            URIRef(domain+celltype)
        ))

class IRIColumn(Column):
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        # 1. generate a cell name that can be an IRI
        cell = format_predicate(cellvalue)
        # 2. capture the rought string value in a Literal
        store.add((
            URIRef(domain+cell),
            RDFS.label,
            Literal(row[j])
        ))
        # 3. type the cell value
        store.add((
            URIRef(domain+cell),
            RDF.type,
            URIRef(domain+celltype)
        ))
        # 4. generate the triple with the pkey
        if self.cellrole == SUBJECT:
            store.add((
                URIRef(domain+cell),
                URIRef(domain+columntype),
                URIRef(domain+pkeyvalue)
            ))
        else:
            store.add((
                URIRef(domain+pkeyvalue),
                URIRef(domain+columntype),
                URIRef(domain+cell)
            ))

class StringColumn(Column):
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        store.add((
            URIRef(domain+pkeyvalue),
            URIRef(domain+columntype),
            Literal(cellvalue)
        ))
        
class IntegerColumn(Column):
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        store.add((
            URIRef(domain+pkeyvalue),
            URIRef(domain+columntype),
            Literal(cellvalue, datatype=XSD.integer)
        ))
        
class FloatColumn(Column):
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        store.add((
            URIRef(domain+pkeyvalue),
            URIRef(domain+columntype),
            Literal(cellvalue, datatype=XSD.float)
        ))
            
class DateColumn(Column):
    def generate_triples(self, store, domain, cellvalue, pkeyvalue):
        store.add((
            URIRef(domain+pkeyvalue),
            URIRef(domain+columntype),
            Literal(cellvalue, datatype=XSD.date) #'2007-01-01'
        ))

        
        

        
        
class CodeSets():
    def __init__(self,name,dict):
        self.name = name
        self.dict = dict
    def getValue(self, key):
        if key in self.dict:
            return dict[key]
        else:
            raise KeyError("Key '" + key + "' not found in section '" + self.name + "' of the grammar file")
        


def findPkeyIndexInHeader(header, pkey):
    count = 0
    for elem in header:
        if elem == pkey:
            return count
        else:
            count += 1
    # We should never come here
    return -1
    


#================================================= Grammar
class Grammar():
    # The Grammar constructor is a factory of column objects and list objects
    def __init__(self,filename, domain, delim):
        self.filename = filename
        self.domain = domain
        self.delim = delim
        # self.columns = { name1 : Column1, name2: Column2, ... }
        self.columns = {}
        # when exploring the lines of the CSV, we need to have the columns ordered
        # the same way than the CSV
        self.orderedcols = []
        # self.lists = { name1 : CodeSets1, name2 : CodeSets2, ... }
        self.lists = {}
        # record pkey = PKey()
        self.pkey = None
        self.pkeyindex = -1

        #read sections
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        config = configparser.ConfigParser()
        config.read(filename)
        for elem in config.sections():
            # Getting code sets
            if elem.startswith('*') and elem.endswith('*'):
                if VERBOSE: print("List found: " + elem)
                mydict = dict()
                 # get the key: values defined in grammar
                for key in config[elem]:
                    mydict[key] = config[elem][key]
                self.lists[elem] = CodeSets(elem, mydict)
                continue
            #read all elements in grammar section
            mydict = dict()
            for key in config[elem]:
                mydict[key] = config[elem][key]
            #pkey
            if CELLROLE not in mydict:
                print("Error: '" + CELLROLE + "' is mandatory in grammar section. Exiting...")
                exit()
            if mydict[CELLROLE] == PKEY:
                self.pkey = PKey(domain,
                                 elem,
                                 PKEY,
                                 mydict[CELLTYPE],
                                 "",
                                 True)
                continue
            if not CELLTYPE in mydict:
                print("Error: '" + CELLTYPE + "' is mandatory in grammar section. Exiting...")
                exit()
            celltype = mydict[celltype]
            if celltype == STRING:
                self.columns[elem] = StringColumn(domain,
                                                  elem,
                                                  mydict[CELLROLE],
                                                  STRING,
                                                  mydict[COLUMNTYPE])
            elif celltype == INTEGER:
                self.columns[elem] = IntegerColumn(domain,
                                                   elem,
                                                   mydict[CELLROLE],
                                                   INTEGER,
                                                   mydict[COLUMNTYPE])
            elif celltype == FLOAT:
                self.columns[elem] = FloatColumn(domain,
                                                 elem,
                                                 mydict[CELLROLE],
                                                 FLOAT,
                                                 mydict[COLUMNTYPE])
            elif celltype == DATE:
                self.columns[elem] = DateColumn(domain,
                                                elem,
                                                mydict[CELLROLE],
                                                DATE,
                                                mydict[COLUMNTYPE])
            else:
                self.columns[elem] = IRIColumn(domain,
                                               elem,
                                               mydict[CELLROLE],
                                               mydict[CELLTYPE],
                                               mydict[COLUMNTYPE])
                
        # Error cases and reporting
        print("Found: "
              + str(nlen(config.sections()))
              + " sections and "
              + str(len(self.lists))
              + " lists")
        if self.pkey == None:
            print("Error: pkey not found in grammar file. Exiting...")
            exit()

    #----------------------------------------------------count_applicable_sections
    def get_applicable_sections(self,key):
        '''
        Sections applicable cannot be 'cell = ignore'.
        Most applicable sections will be unique.
        Several sections may be applicable of several start by the name of 
        the colum + '$1' or '$2' at the end.
        '''
        sections = []
        keys = self.columns.keys()
        for k in keys:
            if k.startswith(key):
                if self.columns[k].to_ignore:
                    # we have to ignore the sections flagged as ignorable 'cell = ignore'
                    return None
                else:
                    sections.append(self.columns[k])
        return sections

    #----------------------------------------------------semantic_parser
    def semantic_parser(self, csvfile, domain, delim, store):
        try:
            reader = csv.reader(open(source.file, "r", encoding='utf-8', errors='ignore'), delimiter=delim)
            #--- begin tech
            tim = Timer()
            nblines = countLinesInCSVFile(csvfile)
            bar = progressbar2.ProgressBar(max_value=nblines)
            #--- end tech
            header = None
            count = 0
            pkeyindex = -1
            for row in reader:
                bar.update(count)
                # header
                if count == 0:
                    header = row
                    # 1. the grammar file section names should be included into the headers
                    # note : it is not mandatory to take all the headers
                    for colname in self.columns:
                        if colname not in header:
                            print("Error: grammar section name '" + colname
                                  + "' not found in CSV file. Exiting...")
                            exit()
                    # 2. sort columns in the same order than the CSV and get index for primary key
                    i = 0
                    for elem in header:
                        if elem in self.columns[elem]:
                            temp = self.columns[elem]
                            if temp.pkey:
                                pkeyindex = i
                            self.orderedcols[i] = self.columns[elem]
                        else:
                            myprint("Information: '" + elem + "' column not in grammar file" )
                        i +=1
                    if pkeyindex == -1:
                        print("Error: could not find pkey in CSV header. Exiting...")
                        exit()
                    # increment CSV line number
                    count +=1
                else:
                    pkeyobj = row[pkeyindex]
                    # general case: standard row
                    for j in range(0,len(row)):
                        col = self.orderedcols[j]
                        col.generate_triple(store, domain, row[j], pkeyobj)

                        #------------------reprendre ici

                        
                        # 2. get pkeyvalue because it will be in the triple
                        pkeyvalue = format_predicate(row[pkeyindex])
                        # 3. get the standard column name
                        colname = format_predicate(predicates[j])
                        # 4. get the applicable Columns objects
                        #    there may be several if several treatments are associated to a
                        #    single column ('[VAPMOV$1]' and '[VAPMOV$1]'
                        # Checks for 'ignore' sections and for 'multiple actions' sections
                        if colname != "": # this happens in some source files
                            sections = self.get_applicable_sections(colname)
                            if sections == None:
                                if VERBOSE:
                                    print("------\nInfo: Section(s) starting by "
                                          + colname
                                          + " ignored due to grammar")
                            else:
                                for s in sections:
                                    if VERBOSE:
                                        print("------\nDomain: " + domain)
                                        print("Cell value: " + cell)
                                        print("pkeyvalue: " + pkeyvalue)
                                    s.generate_triples(store,domain,cell,pkeyvalue,self.pkeytype,self.lists)
            tim.stop()
        except csv.Error as e:
            print("Error caught in loading csv file: " + f)
            print(e)
            sys.exit(1)
'''
        except Exception as e:
            print('Unknown error')
            print(type(e))
            print(e.args)
            print(e)
'''


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
            print("Configuration file: " + a)

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

    globaltimer.stop()
    print("Goodbye")
    return


if __name__ == '__main__':
    main()

