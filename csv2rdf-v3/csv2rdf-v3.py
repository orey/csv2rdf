#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           August 2024
# License:        GPL v3
#============================================
#!/usr/bin/env python3

import getopt, sys, csv, configparser, os.path, traceback, time, datetime
import progressbar2 # pip install progressbar2

from rdflib import Graph, Literal, URIRef, RDF, RDFS, BNode

MY_RDF_STORE = "rdf_store.rdf"

VERBOSE = False
INTERRUPT = False


#============================================ interrupt
def interrupt():
    '''
    Manual breakpoint
    '''
    resp = input("Continue? ")
    if resp.upper() in ["N","NO"]:
        print("Goodbye!")
        exit(0)

        
#============================================ Timer
class Timer():
    def __init__(self):
        self.start = time.time()
    def stop(self):
        self.stop = time.time()
        print("\nTreatment duration: "
              + str((round(self.stop-self.start))//60)
              + " minutes and "
              + str((round(self.stop-self.start))%60)
              + " seconds\n")
        

#============================================ Source
class Source():
    def __init__(self, name, file, domain, type, prefix, delim, active):
        self.name = name
        self.file = file
        self.domain = domain
        self.type = type
        self.prefix = prefix
        self.delim = delim
        self.semantic = False
        self.active = active
    def setSemantic(self, semanticfile):
        self.semantic = True
        self.semanticfile = semanticfile
    def print(self):
        print("-----------")
        print("Source: " +  self.name)
        print("File: " + self.file)
        print("Domain: " + self.domain)
        print("Type: " + self.type)
        print("Prefix: " + self.prefix)
        print("Delim: " + self.delim)
        print("Active: " + str(self.active))
        if self.semantic:
            print("Semantics: " + self.semanticfile)


#============================================ Options: main conf file
class Options():
    '''
    This class reads the option file that is acting as a command file.
    It is managing several files or several times the same file.
    Containes the various Source instances
    '''
    # Mandatory fields per csv file
    FILE = 'file'
    DOMAIN = 'domain'
    TYPE = 'type'
    PREFIX = 'predicate_prefix'
    DELIMITER = 'delimiter'
    ACTIVE = 'active'

    # Optional fields
    SEMANTICS = 'semantics'

    #-----------------------------------------------__init__
    def __init__(self, filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        config = configparser.ConfigParser()
        config.read(filename)
        self.sources = []
        nbactive = 0
        for elem in config.sections():
            active = False
            if self.ACTIVE in config[elem]:
                if config[elem][self.ACTIVE] == "True":
                    active = True
                    nbactive += 1
            source = Source(elem,
                            config[elem][self.FILE],
                            config[elem][self.DOMAIN],
                            config[elem][self.TYPE],
                            config[elem][self.PREFIX],
                            config[elem][self.DELIMITER],
                            active)
            if self.SEMANTICS in config[elem]:
                source.setSemantic(config[elem][self.SEMANTICS])
            self.sources.append(source)
        print("Config file read: found " + str(len(self.sources)) + " source(s) and "
              + str(nbactive) + " active(s)")

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
        self.interrupt = interrupt
        self.store = Graph()
    def get_store(self):
        return self.store
    def add(self, triple):
        if VERBOSE: print(triple)
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
        if c in [' ', '-', '/', '(',')',',', '"', "'"]:
            new += '_'
        else:
            new += pred[i]
    return new


#================================================= default_csv_parser    
def default_csv_parser(source, store):
    '''
    In case no semantics are provided, this is the default parsing procedure
    This function reads the CSV file line by line and generates default triples:
    -> domain:predicate_prefix+index RDF.type type .
    And for each cell in the line:
    -> domain:predicate_prefix+index COLUMN_TITLE Literal(value) .
    '''
    delim = source.delim
    try:
        # CSV files may contain non UTF8 chars
        reader = csv.reader(open(source.file, "r", encoding='utf-8', errors='ignore'), delimiter=delim)

        # predicates is used to store all headers of the first row but in a RDF manner
        # because they will be the predicate
        predicates = []
        domain = source.domain
        prefix = source.prefix
        mytype = source.type
        start = time.time()
        for i, row in enumerate(reader):
            print(str(i), end='|')
            if i == 0:
                for elem in row:
                    predicates.append(URIRef(domain + format_predicate(elem)))
                if VERBOSE:
                    print(predicates)
            else:
                subject = URIRef(domain + prefix + str(i))
                store.add((subject, RDF.type, URIRef(domain + mytype)))
                for n, elem in enumerate(row):
                    if not elem == '':
                        e = Literal(elem)
                        store.add((subject, predicates[n], e))
        end = time.time()
        print("\nTreatment duration: " + str((round(end-start))//60) + " minutes and " + str((round(end-start))%60) + " seconds\n")
        if VERBOSE:            
            print("%d lines loaded" % (i-1))
    except csv.Error as e:
        print("Error caught in loading csv file: " + f)
        print(e)
        sys.exit(1)
    except Exception as e:
        print('Unknown error')
        print(type(e))
        print(e.args)
        print(e)


def format_date(mydate):
    '''
    mydate is supposed to be a standard Python date object from 'datetime'
    '''
    return Literal(str(mydate), datatype=XSD.date)

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
class Column():
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
        # 3 particular cases
        if self.to_ignore:
            #should not happen because ignorable sectons are intercepted before
            return
        if self.is_pkey_descr:
            store.add((URIRef(domain + pkey),
                       RDFS.comment,
                       Literal(cell)))
            return
        if self.is_pkey:
            mytype = self.mydict['celltypes'].split(',')[0]
            store.add((URIRef(domain + format_predicate(cell)),
                       RDF.type,
                       URIRef(domain + format_predicate(mytype))))
            generate_type_triples(self.mydict['celltypes'].split(','), store, domain, True)
            # there are neither 'columns' nor column types
            return

        # general case
        cellgrammar = self.mydict['cell'].split(',')     # simple or with command
        celltypes = self.mydict['celltypes'].split(',')  # hierarchy of types, last one being rdf/rdfs
        colgrammar = self.mydict['column'].split(',')    # should have only one element
        coltypes = self.mydict['columntypes'].split(',') # hierarchy of types, last one being rdf/rdfs

        # init before treatments
        newcell = ""
        # we must alter the cell value in some sort
        if len(cellgrammar) != 1:
            newcell = ""
            # map
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
                        print("Strange: " + cell + " is not in maptable")
                        print(maptable)
                        interrupt()
                else:
                    [myinf,mymax] = args[0].split(":")
                    myinfchar = int(myinf) if (myinf != "") else 0
                    mymaxchar = int(mymax) if (mymax != "") else 0
                    temp = cell[myinfchar:mymaxchar].lower()
                    if temp in maptable:
                        newcell = maptable[temp]
                    else:
                        print("Strange: " + temp + " is not in maptable")
                        print(maptable)
                        interrupt()
            # extract
            elif cellgrammar[1].startswith("extract("):
                args = cellgrammar[1][8:-1] #expecting one argument '-3:' or '1:2'
                [myinf,mymax] = args.split(":")
                myinfchar = int(myinf) if (myinf != "") else 0
                mymaxchar = int(mymax) if (mymax != "") else 0
                newcell = cell[myinfchar:mymaxchar]
            # prefix
            elif cellgrammar[1].startswith("prefix("):
                args = cellgrammar[1][7:-1] #expecting one arg such as 'toto_' or 'gnu_'
                newcell = args + cell
            else:
                print("Unknown command: " + cellgrammar[1] + " Exiting...")
                exit(0)
        else:
            # we keep the original value
            newcell = cell
        
        # 0. Define readable variables     
        rdfcell     = URIRef(domain + format_predicate(newcell))
        rdfcelltype = URIRef(domain + format_predicate(celltypes[0]))
        rdfcoltype  = URIRef(domain + format_predicate(coltypes[0]))
        rdfpkey     = URIRef(domain + format_predicate(pkey))
        rdfpkeytype = URIRef(domain + format_predicate(pkeytype))
                         
        # 1. we have to type the cell
        store.add((rdfcell, RDF.type, rdfcelltype))
        
        # 2. we generate the standard triple + the domain and range of the relationship

        # The 2 first cases are standard and should be used 99% of the case
        if cellgrammar[0] == 'subject' and colgrammar[0] == 'predicate':
            # standard triple: cell is at the intersection of line and column
            store.add((rdfcell,    rdfcoltype,  rdfpkey))
            store.add((rdfcoltype, RDFS.domain, rdfcelltype))
            store.add((rdfcoltype, RDFS.range,  rdfpkeytype))
            generate_type_triples(celltypes, store, domain, True)
            generate_type_triples(coltypes,  store, domain, False)
            
        elif cellgrammar[0] == 'object' and colgrammar[0] == 'predicate':
            store.add((rdfpkey,    rdfcoltype,  rdfcell))
            store.add((rdfcoltype, RDFS.domain, rdfpkeytype))
            store.add((rdfcoltype, RDFS.range,  rdfcelltype))
            generate_type_triples(celltypes, store, domain, True)
            generate_type_triples(coltypes,  store, domain, False)
        else:
            if cellgrammar[0] == 'predicate' and colgrammar[0] == 'subject':
                print("This case is strange because column name is suppose to be the predicate")
                exit(0)
        if VERBOSE: print("Done for cell: " + cell)


#================================================= Grammar
class Grammar():
    '''
    Constructor parses the configuration file
    Semantic parser generates triples accordingly
    '''
    pkeycolumnname = "" # we need to record the name of the column storing the pkey
    pkeytype = ""
    filename = ""
    columns = None #dictionary of dictionaries: 'name : Column object'
    lists = None #dictionary of dictionaries: 'name : dictionary of key/values'
    # Note: we don't keep the configparser instance once the file is parsed

    #----------------------------------------------------_init_
    def __init__(self,filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        config = configparser.ConfigParser()
        config.read(filename)
        self.columns = dict() 
        self.lists = dict()
        #read sections
        nbsec = 0
        nblist = 0
        for elem in config.sections():
            if elem.startswith('*') and elem.endswith('*'):
                if VERBOSE: print("List found: " + elem)
                mydict = dict()
                for key in config[elem]:
                    mydict[key] = config[elem][key]
                self.lists[elem] = mydict
                nblist += 1
            else:
                mydict = dict()
                for key in config[elem]:
                    mydict[key] = config[elem][key]
                temp = Column(mydict)
                # we keep a copy to be able to pass it as a parameter
                if temp.is_pkey:
                    self.pkeycolumnname = elem
                    if VERBOSE: print("pkey column name found: " + elem)
                    # get pkeytype
                    self.pkeytype = temp.pkeytype
                    if VERBOSE: print("pkeytype : " + self.pkeytype)
                    if INTERRUPT: interrupt()
                self.columns[elem] = temp
                if VERBOSE: print("Column section found: " + elem)
                nbsec += 1
        print("Found: " + str(nbsec) + " sections and " + str(nblist) + " lists")
        if self.pkeycolumnname == "":
            print("pkey column name not found in file. The grammar file cannot be processes. Exiting...")
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
    def semantic_parser(self, source, store):
        delim = source.delim
        try:
            # CSV files may contain non UTF8 chars
            reader = csv.reader(open(source.file, "r", encoding='utf-8', errors='ignore'), delimiter=delim)

            # predicates is used to store all headers of the first row but in a RDF manner
            # because they will be the predicate
            predicates = []
            domain = source.domain
            # Not used in semùantic parser
            #prefix = source.prefix
            #mytype = source.type
            tim = Timer()
            pkeyindex = -1
            #counting the lines with a specific reader
            newreader = csv.reader(open(source.file, "r", encoding='utf-8', errors='ignore'), delimiter=delim)
            nblines = 0
            for i, row in enumerate(newreader):
                nblines += 1
            print("------\nSource: " + source .name + "\nNumber of lines to process: " + str(nblines))
            bar = progressbar2.ProgressBar(max_value=nblines)
            # main loop
            for i, row in enumerate(reader):
                bar.update(i)
                #print(str(i), end='|')
                #print("CSV data file: " + source.file + " - line " + str(i))
                # dealing with CSV header
                if i == 0:
                    for i in range(0,len(row)):
                        # get the pkey value to generate all triples
                        if row[i] == self.pkeycolumnname:
                            pkeyindex = i
                            if VERBOSE: print("pkeyindex = " + str(i))
                    for columnheader in row:
                        predicates.append(columnheader) # they are added with potential spaces and ""
                    if VERBOSE:
                        print(predicates)
                else:
                    if VERBOSE:
                        print("Row #" + str(i))
                        print(row)
                    # general case: standard row
                    for j in range(0,len(row)):
                        # 1. get the cell value and protect versus crappy data
                        cell = format_predicate(row[j])
                        if cell == "":
                            if VERBOSE:
                                print("------\nEmpty cell in column: " + predicates[j] + " Skipping")
                            continue
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
                                    print("------\nInfo: Section(s) starting by " + colname + " ignored due to grammar")
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
    print("Usage: \n $ csv2rdf -c [CONFIG] -o [output]")
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
        opts, args = getopt.getopt(sys.argv[1:], "c:o:ih",
                                   ["conf=", "interactive", "help"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    options = None
    interactive = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-i", "--interactive"):
            interactive = True
            print("Interactive mode chosen, you will be prompted before processing each source")
        if o in ("-c", "--conf"):
            options = a
            print("Configuration file: " + a)

    # default option file name if no options are provided
    if options == None:
        usage()
        sys.exit()
    opt = Options(options)
    opt.print()

    # Supporting multiple stores, one by source
    storeindex = 0
    
    for source in opt.sources:
        storeindex +=1
        if not source.active:
            print("The source " + source.name + " is declared as inactive. Skipping...")
            continue
        
        # determine name of the triplestore
        output = source.name + ".ttl"
        store = RDFStore(output)

        # the generation can be long: we ask if we are sure
        if interactive:
            resp = input("------\nStart " + source.name + " processing with TTL store file being '" + output + "'? ")
            if resp.upper() in ["NO","N"]:
                print("Skipping " + source.name + "...")
                continue

        # route to the proper parser
        if not source.semantic:
            default_csv_parser(source, store)
        else:
            # Parsing the grammar file
            gram = Grammar(source.semanticfile)
            gram.semantic_parser(source, store)

        # Dumping the triplestore
        store.dump()
    print("Goodbye")
    return


if __name__ == '__main__':
    main()

