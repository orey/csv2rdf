#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           November 2018
# License:        GPL v3
#============================================
#!/usr/bin/env python3

import getopt, sys, csv, configparser, os.path, traceback, time, datetime

from rdflib import Graph, Literal, URIRef, RDF, BNode

MY_RDF_STORE = "rdf_store.rdf"


#------------------------------------------ Options
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

class Options():
    '''
    This class reads the option file that is acting as a command file.
    It is managing several files or several times the same file.
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
    def print(self):
        for source in self.sources:
            source.print()
    

#------------------------------------------ RDFStore
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
    def dump(self, verbose=False):
        self.store.serialize(self.name, format='turtle')
        if verbose:
            print('Store dumped')


#------------------------------------------ default_csv_parser
def format_predicate(pred):
    new = ''
    for i, c in enumerate(pred):
        if c in [' ', '-']:
            new += '_'
        else:
            new += pred[i]
    return new

    
def default_csv_parser(source, store, verbose=False):
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
                if verbose:
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
        if verbose:            
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

#------------------------------------------ semantic_ini_parser
def generate_type_triples(str, store, domain):
    '''
    We analyze a list of types separated by a comma and create the
    genealogy. The last one must be a rdf/rdfs type.
    Works for cell and column.
    '''
    lst = str.split(',')
    if len(lst) < 2:
        return True
    # we generate couples so not for the last one
    for i in range(0, len(lst)-1):
        lower = lst[i] # should not be a rdf/rdfs
        new = lst[i+1]
        lowertype = URIRef(domain + lower)
        if new.upper() == "RDFS:RESOURCE":
            newtype = RDFS.Resource
        elif new.upper() == "RDF.PROPERY":
            newtype = RDF.Property
        elif new.upper() == "RDFS:COMMENT":
            newtype = RDFS.comment
        else:
            newtype = URIRef(domain + new)
        store.add((lowertype, RDF.type, newtype))
    return True


class Column():
    to_ignore = False
    is_pkey = False
    is_pkey_descr = False
    def __init__(self,mydict):
        self.mydict = mydict
        if mydict['cell'] == 'ignore':
            self.to_ignore = True
        elif mydict['cell'] == 'pkey':
            self.is_pkey = True
        elif mydict['celltypes'] == 'string':
            self.is_pkey_descr = True
            
    def generate_triples(self,store,domain,cell,pkey,lists=None):
        # gestion des trois cas particuliers
        if self.to_ignore:
            return
        if self.is_pkey:
            mytype = mydict['celltypes'].split(',')[0]
            store.add((URIRef(domain + cell), RDF.type, URIRef(domain + mytype)))
            generate_type_triples(mydict['celltypes'], store, domain)
            return
        if self.is_pkey_descr:
            store.add((URIRef(domain + pkey),RDFS.comment,cell))
            return
        #cas général
        cellgrammar = self.mydict['cell'].split(',') #simple or with command
        celltypes = self.mydict['celltypes'].split(',') #hierarchy of types, last one being rdf/rdfs
        colgrammar = self.mydict['column'].split(',') #should have only one element
        coltypes = self.mydict['columntypes'].split(',') #hierarchy of types, last one being rdf/rdfs
        #simple case, we have the 6 triples
        if len(cellgrammar) == 1:
            if cellgrammar[0] == 'subject' and colgrammar[0] == 'predicate':
                store.add((URIRef(domain + cell), URIRef(domain + coltypes[0]), URIRef(domain + pkey)))
            elif cellgrammar[0] == 'object' and colgrammar[0] == 'predicate':
                store.add((URIRef(domain + pkey), URIRef(domain + coltypes[0]), URIRef(domain + cell)))
            elif cellgrammar[0] == 'predicate' and colgrammar[0] == 'subject': #strange case
                store.add((URIRef(domain + coltypes[0]), URIRef(domain + cell), URIRef(domain + pkey)))
            elif cellgrammar[0] == 'predicate' and colgrammar[0] == 'object': #strange case
                store.add(URIRef(domain + pkey), URIRef(domain + cell), (URIRef(domain + coltypes[0])))
            elif cellgrammar[0] == 'subject' and colgrammar[0] == 'object': #strange case
                store.add(URIRef(domain + cell), URIRef(domain + pkey), (URIRef(domain + coltypes[0])))
            elif cellgrammar[0] == 'object' and colgrammar[0] == 'subject': #strange case
                store.add(URIRef(domain + coltypes[0]), URIRef(domain + pkey), (URIRef(domain + cell)))
            else:
                print("This should not happen. Exiting...")
                exit(0)
        # we have a command to process, 'cell' will be altered
        # map, extract, prefix
        else:
            newcell = ""
            # map
            if cellgrammar[1].startswith("map("):
                args = cellgrammar[1][4:-1].split(',')#expecting 2 arguments 'all,*suppliers*' or '1:2,*configs*'
                maptable = lists[args[1]] #getting dict
                if args[0] == 'all':
                    newcell = maptable[cell]
                else:
                    [myinf,mymax] = args[0].split(":")
                    myinfchar = int(myinf) if (myinf != "") else 0
                    mymaxchar = int(mymax) if (mymax != "") else 0
                    newcell = maptable[cell[myinfchar:mymaxchar]]
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
                mewcell = args + cell
            else:
                print("Unknown command: " + cellgrammar[1] + " Exiting...")
                exit(0)
            if cellgrammar[0] == 'subject' and colgrammar[0] == 'predicate':
                store.add((URIRef(domain + newcell), URIRef(domain + coltypes[0]), URIRef(domain + pkey)))
            elif cellgrammar[0] == 'object' and colgrammar[0] == 'predicate':
                store.add((URIRef(domain + pkey), URIRef(domain + coltypes[0]), URIRef(domain + newcell)))
            elif cellgrammar[0] == 'predicate' and colgrammar[0] == 'subject': #strange case
                store.add((URIRef(domain + coltypes[0]), URIRef(domain + newcell), URIRef(domain + pkey)))
            elif cellgrammar[0] == 'predicate' and colgrammar[0] == 'object': #strange case
                store.add(URIRef(domain + pkey), URIRef(domain + newcell), (URIRef(domain + coltypes[0])))
            elif cellgrammar[0] == 'subject' and colgrammar[0] == 'object': #strange case
                store.add(URIRef(domain + newcell), URIRef(domain + pkey), (URIRef(domain + coltypes[0])))
            elif cellgrammar[0] == 'object' and colgrammar[0] == 'subject': #strange case
                store.add(URIRef(domain + coltypes[0]), URIRef(domain + pkey), (URIRef(domain + newcell)))
            else:
                print("This should not happen. Exiting...")
                exit(0)
        #remains the generation of triples associated to types and relationships
        generate_type_triples(celltypes, store, domain)
        generate_type_triples(coltypes, store, domain)
        return


class Grammar():
    pkey = None
    def __init__(self,filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        config = configparser.ConfigParser()
        config.read(filename)
        self.columns = dict() #dictionary of dictionaries: 'name : Column object'
        self.lists = dict() #dictionary of dictionaries: 'name : dictionary of key/values'
        #read sections
        nbsec = 0
        nblist = 0
        for elem in config.sections():
            if elem.startswith('*') and elem.endswith('*'):
                print("List found: " + elem)
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
                    self.pkey = temp
                self.columns[elem] = temp
                print("Column section found: " + elem)
                nbsec += 1
        print("Found: " + str(nbsec) + " sections and " + str(nblist) + " lists")
                




        

#------------------------------------------ semantic_csv_parser
class SGrammar():
    SEP = '|'
    IGNORE = 'ignore'
    SUBJECT1 = 'pkey'
    SUBJECT2 = 'subject2'
    LITERAL = 'literal'
    FORGET = ['NONE', '-', '']
    STANDARD = 'S'
    REVERSE = 'R'

class MLiteral():
    def __init__(self, index, cname):
        self.index = index
        self.cname = cname
    def get_cname(self):
        return self.cname

class Subject1(MLiteral):
    def __init__(self, index, cname, stype):
        super().__init__(index, cname)
        self.stype = stype
    def get_type(self):
        return self.stype

class Subject2(Subject1):
    def __init__(self, index, cname, stype, direction, name=''):
        super().__init__(index, cname, stype)
        self.direction = direction
        self.name = name
    def is_standard(self):
        if self.direction == SGrammar.STANDARD:
            return True
        else:
            return False
    def get_name(self):
        if self.name == '':
            return format_predicate(self.cname)
        else:
            return self.name

def semantic_csv_parser(conf, f, store, verbose=False):
    semantic = conf.get_option(f, conf.SEMANTICS)
    if semantic == None:
        raise ValueError('No semantic file found')
    subj1 = None
    soptions = {}
    try:
        # 1. Parse options & semantic grammar
        with open(semantic, 'r', encoding='utf-8', errors='ignore') as semf:
            reader = csv.reader(semf, delimiter = conf.get_option(f, conf.SEM_DELIM))
            for i, row in enumerate(reader):
                if len(row) != 2:
                    raise ValueError('Row #' + str(i+1) + ' does not have 3 flields: ' + str(row))
                key = row[0]
                value = row[1]
                if value != SGrammar.IGNORE:
                    if verbose: print(row)
                    parts = value.split(SGrammar.SEP)
                    if len(parts) < 1:
                        raise ValueError('Grammar line not recognized: ' + value)
                    if verbose: print(parts)
                    # subject 1
                    if parts[0] == SGrammar.SUBJECT1:
                        if len(parts) != 2:
                            raise ValueError('Grammar line not correct for subject1: ' + row[1])
                        subj1 = i, Subject1(i, row[0], parts[1])
                    # Subject2
                    elif parts[0] == SGrammar.SUBJECT2:
                        if len(parts) == 3:
                            soptions[i] = Subject2(i, row[0], parts[1], parts[2])
                        elif len(parts) == 4:
                            soptions[i] = Subject2(i, row[0], parts[1], parts[2], parts[3])
                        else:
                            raise ValueError('Grammar line not correct for subject2: ' + row[1])
                    # Literal
                    elif parts[0] == SGrammar.LITERAL:
                        soptions[i] = MLiteral(i, row[0])
                    else:
                        raise ValueError('Grammar line not recognized: ' + row[1])
            if verbose:
                print(subj1)
                print(soptions)
            semf.close()

        # 2. Parse file
        domain = conf.get_option(f, Options.DOMAIN)
        mytype = conf.get_option(f, Options.TYPE)
        with open(f, 'r', encoding='utf-8', errors='ignore') as dataf:
            reader = csv.reader(dataf , delimiter = conf.get_option(f, conf.DELIMITER))
            for i, row in enumerate(reader):
                sys.stdout.write(str(i+1) + '|')
                # First row is skipped
                if i == 0:
                    continue
                # Standard row: get the subject1 value
                subj = URIRef(domain + 'A_' + row[subj1[0]])
                triple = (subj, RDF.type, URIRef(domain + 'A_' + subj1[1].get_type()))
                if verbose: print(triple)
                store.add(triple)
                # Iterate through soptions
                keys = soptions.keys()
                values = soptions.values()
                for k in keys:
                    # Get the value in cell i, k
                    val = row[k]
                    if val in SGrammar.FORGET:
                        # Skip before not meaningful
                        continue
                    if verbose: print(val)
                    gram = soptions[k]
                    triple = None
                    if type(gram) == MLiteral:
                        triple = (subj, URIRef(domain + 'A_' + gram.get_cname()), Literal(val))
                        if verbose: print(triple)
                        store.add(triple)
                    elif type(gram) == Subject2:
                        # Get infos
                        mtype = URIRef(domain + 'A_' + gram.get_type())
                        # TODO the function that discovers entities in the cell shoudl be parameterizable
                        vals = val.split(' ')
                        for valor in vals:
                            # Type all records
                            temp = URIRef(domain + 'A_' + valor)
                            t = (temp, RDF.type, mtype)
                            store.add(t)
                            if verbose: print(t)
                            # Link them with the subj after analyzing in what direction
                            if gram.is_standard():
                                t = (subj, URIRef(domain + 'A_' + gram.get_name()), temp)
                            else:
                                t = (temp, URIRef(domain + 'A_' + gram.get_name()), subj)
                            if verbose: print(t)
                            store.add(t)
            dataf.close()
    except Exception as e:
        print(type(e), e, e.args)
        traceback.print_exc()
        
#------------------------------------------ usage
def usage():
    print("Utility to transform CSV files into RDF files")
    print("Usage: \n $ csv2rdf -c [CONFIG] -o [output] [-v]")
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


#------------------------------------------ main
def main():
    try:
        # Option 't' is a hidden option
        opts, args = getopt.getopt(sys.argv[1:], "c:o:hv",
                                   ["conf=", "output=", "help", "verbose"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    options = None
    verbose = False
    output = ""
    test = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-c", "--conf"):
            options = a
            print("Configuration file: " + a)
        if o in ("-o", "--output"):
            output = a
            print("Ouput file: " + a)
        if o == "test":
           test = True

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
        if output == "":
            output = "rdfstore" + '-' + str(storeindex) + ".ttl"
        else:
            output = output.split(".")[0] + '-' + str(storeindex) + ".ttl"
        store = RDFStore(output)

        # the generation can be long: we ask if we are sure
        resp = input("Start " + source.name + " processing with store file being '" + output + "'?")
        if resp.upper() in ["NO","N"]:
            print("Skipping " + source.name + "...")
            continue

        # route to the proper parser
        if not source.semantic:
            default_csv_parser(source, store, verbose=False)
        else:
            gram = Grammar(source.semanticfile)
            return

        # Dumping the triplestore
        print("Store dump begin")
        store.dump()
        print("Store dump end")
    print("Goodbye")
    return





#    conf = Config(myfile, opt, verbose)
#    if semantic != None:
#        soptions = Semantic(semantic, verbose)
#        soptions.print()
#        print(soptions.get_root())
        # TODO pass soptions to parse_file
#        conf.parse_file()
#    else:
#        conf.parse_file()
#    conf.dump_store()
#    if display != -1:
#        rdf_to_graphviz(conf.get_store(),file.split('.')[0], display)


if __name__ == '__main__':
    main()

