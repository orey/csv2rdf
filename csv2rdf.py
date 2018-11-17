#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           November 2018
# License:        GPL v3
#============================================
import getopt, sys, csv, configparser, os.path, traceback
from rdflib import Graph, Literal, URIRef, RDF, BNode
from rdf2graphviz import rdf_to_graphviz


#------------------------------------------ Options
class Options():
    '''
    This class reads the option file that is acting as a command file.
    It is managing several files or several times the same file.
    '''
    # Mandatory fields per csv file
    DOMAIN = 'domain'
    TYPE = 'type'
    PREFIX = 'predicate_prefix'
    DELIMITER = 'delimiter'

    # Optional fields
    SEMANTICS = 'semantics'
    SEM_DELIM = 'semantics_delimiter'
    DEFAULT_SEM_DELIM = ';'
    
    def __init__(self, filename):
        if not os.path.isfile(filename):
            raise FileNotFoundError('File "' + filename + '" not found.')
        self.filename = filename
        self.config = configparser.ConfigParser()
        self.config.read(filename)
        self.sections = self.config.sections()
        self.filenb = len(self.sections)
    def get_files(self):
        return self.sections
    def get_option(self, datafile, key):
        if self.config.has_section(datafile):
            if self.config.has_option(datafile, key):
                return self.config.get(datafile,key)
            else:
                if key == Options.SEM_DELIM:
                    return Options.DEFAULT_SEM_DELIM
                # Usable in case of lack of semantics in the config file
                return None
        else:
            raise ValueError('Unknown section in configuration file: ' + datafile)
    def print(self):
        for sec in self.config.sections():
            print('Section: ' + sec)
            for opt in self.config.options(sec):
                print('Option: ' + opt)


def test_Options():
    options = Options('csv2rdf.ini')
    options.print()
    print(options.get_files())
    

#------------------------------------------ RDFStore
class RDFStore():
    '''
    This class wraps the RDF store proposed by rdflib
    TODO Add more output formats in dump_store
    '''
    def __init__(self, name):
        # Expecting name to be something like "toto"
        self.name = name + '.ttl'
        self.store = Graph()
    def get_store(self):
        return self.store
    def add(self, triple):
        self.store.add(triple)
    def dump(self, verbose=False):
        self.store.serialize(self.name, format='turtle')
        if verbose:
            print('Store dumped')

def test_RDFStore():
    store = RDFStore('test_RDFStore')
    subject = BNode()
    object = URIRef('https://www.test.urg/sem#oups')
    store.add((subject, RDF.type, object))
    store.dump(True)

#------------------------------------------ default_csv_parser
def format_predicate(pred):
    new = ''
    for i, c in enumerate(pred):
        if c in [' ', '-']:
            new += '_'
        else:
            new += pred[i]
    return new

    
def test_pred():
    print(format_predicate('I am a big-boy'))


def default_csv_parser(conf, f, store, verbose=False):
    '''
    In case no semantics are provided, this is the default parsing procedure
    This function reads the CSV file line by line and generates default triples:
    -> domain:predicate_prefix+index RDF.type type .
    And for each cell in the line:
    -> domain:predicate_prefix+index COLUMN_TITLE Literal(value) .
    '''
    delim = conf.get_option(f, Options.DELIMITER)
    try:
        reader = csv.reader(open(f, "r"), delimiter=delim)

        # predicates is used to store all headers of the first row but in a RDF manner
        # because they will be the predicate
        predicates = []
        domain = conf.get_option(f, Options.DOMAIN)
        prefix = conf.get_option(f, Options.PREFIX)
        mytype = conf.get_option(f, Options.TYPE)
        for i, row in enumerate(reader):
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
  
        
def test_default_csv_parser():
    test_pred()
    options = Options('csv2rdf.ini')
    store = RDFStore('TEST_dump')
    default_csv_parser(options, 'test1.csv', store, True)
    store.dump(True)


#------------------------------------------ semantic_csv_parser
class SGrammar():
    SEP = '|'
    IGNORE = 'ignore'
    SUBJECT1 = 'subject1'
    SUBJECT2 = 'subject2'
    LITERAL = 'literal'

class Subject1():
    def __init__(self, index, cname, stype):
        self.index = index
        self.cname = cname
        self.stype = stype

class Subject2(Subject1):
    def __init__(self, index, cname, stype, direction, multi, name=''):
        super().__init__(index, cname, stype)
        self.direction = direction
        self.multi = multi
        self.name = name


def semantic_csv_parser(conf, f, store, verbose=False):
    semantic = conf.get_option(f, conf.SEMANTICS)
    if semantic == None:
        raise ValueError('No semantic file found')
    soptions = {}
    try:
        reader = csv.reader(open(semantic, 'r'), delimiter = conf.get_option(f, conf.SEM_DELIM))
        for i, row in enumerate(reader):
            if len(row) != 2:
                raise ValueError('Row #' + str(i+1) + ' does not have 3 flields: ' + str(row))
            key = row[0]
            value = row[1]
            if value != SGrammar.IGNORE:
                if verbose: print(row)
                parts = value.split(SGrammar.SEP)
                if len(parts) < 1:
                    raise ValueError('Grammar line not recognized: ' + row[1])
                if verbose: print(parts)
                # subject 1
                if parts[0] == SGrammar.SUBJECT1:
                    if len(parts) != 2:
                        raise ValueError('Grammar line not correct for subject1: ' + row[1])
                    soptions[i] = Subject1(i, row[0], parts[1])
                elif parts[0] == SGrammar.SUBJECT2:
                    if len(parts) == 4:
                        soptions[i] = Subject2(i, row[0], parts[1], parts[2], parts[3])
                    elif len(parts) == 5:
                        soptions[i] = Subject2(i, row[0], parts[1], parts[2], parts[3], parts[4])
                    else:
                        raise ValueError('Grammar line not correct for subject2: ' + row[1])
                elif parts[0] == SGrammar.LITERAL:
                    soptions[i] = SGrammar.LITERAL
                else:
                    raise ValueError('Grammar line not recognized: ' + row[1])
        if verbose: print(soptions)
    except Exception as e:
        print(type(e), e, e.args)
        traceback.print_exc()


class Semantic():
    '''
    Semantic file is a CSV file with in first column the header name of the data file
    and in the second column orders about the type.
    '''
    def __init__(self, option, verbose):
        self.semantic = semantic
        self.verbose  = verbose
        self.soptions = {}
        reader = csv.reader(open(self.semantic, "r"), delimiter=';')
        try:
            for row in reader:
                print(row)
                self.soptions[row[0]] = row[1]
            if self.verbose:            
                print("Semantic config loaded")
        except csv.Error as e:
            print("Error caught in loading csv file")
            print(e)
    def print(self):
        print(self.soptions)
    def get_root(self):
        for k,v in self.soptions.items():
            if v.startswith('primary'):
                return k, v[8:]
            else:
                raise ValueError('No primary found in configuration')
    def create_triple(self, root, cname, cvalue):
        rule = self.soptions[cname]
        if rule == 'ignore':
            return None
        if rule.startswith('primary'):
            return cvalue
        
#------------------------------------------ orchestrator
def orchestrator(conf_file, storename, verbose=False):
    '''
    The orchestrator determines what to do from the option files and calls the right parser
    depending on the semantic file presence of absence
    '''
    try:
        options = Options(conf_file)
        store = RDFStore(storename)
        files = options.get_files()
        for f in files:
            if options.get_option(f, Options.SEMANTICS) != None:
                semantic_csv_parser(options, f, store, verbose)
            else:
                default_csv_parser(options, f, store, verbose)
        return store
    except Exception as e:
        print(type(e))
        print(e)
        sys.exit(1)

        
def test_orchestrator():
    #orchestrator('toto.ini')
    orchestrator('csv2rdf.ini', 'ORCHESTRE', verbose=True)

        
#------------------------------------------ usage
def usage():
    print("Utility to transform CSV files into RDF files")
    print("Usage: \n $ csv2rdf -o OPTIONS.ini [-v]")
    print("$ csv2rdf -h")
    print("Options:")
    print('"-o": If "-o OPTION.ini" is not provided, "csv2rdf.ini" will be searched for')
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


def test_cases():
    print('**************************************************')
    print('Test start\n------------')
    test_Options()
    test_RDFStore()
    test_default_csv_parser()
    test_orchestrator()
    print('------------\nTest end')
    


def main():
    try:
        # Option 't' is a hidden option
        opts, args = getopt.getopt(sys.argv[1:], "ohvt",
                                   ["options=", "display=", \
                                    "semantic=", "help", "verbose", "test"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    options = None
    verbose = False
    test    = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-o", "--options"):
            options = a
        if o in ('-t', '--test'):
            test = True
    # Test scenario
    if test:
        test_cases()
        sys.exit(0)

            
    # default option file name if no options are provided
    if options == None:
        options = 'csv2rdf.ini'
#    if myfile == None:
#        usage();
#        sys.exit(1)
    # We have the csv file
    opt = Options(options)

    store = RDFStore(myfile.split('.')[0])

    conf = Config(myfile, opt, verbose)
    if test:
        conf.print()
        test_pred()
    if semantic != None:
        soptions = Semantic(semantic, verbose)
        soptions.print()
        print(soptions.get_root())
        # TODO pass soptions to parse_file
        conf.parse_file()
    else:
        conf.parse_file()
    conf.dump_store()
    if display != -1:
        rdf_to_graphviz(conf.get_store(),file.split('.')[0], display)


if __name__ == '__main__':
    main()
