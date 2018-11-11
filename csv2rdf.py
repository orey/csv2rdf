#============================================
# File name:      csv2rdf.py
# Author:         Olivier Rey
# Date:           November 2018
# License:        GPL v3
#============================================
import getopt, sys, csv, configparser
from rdflib import Graph, Literal, URIRef, RDF
from rdf2graphviz import rdf_to_graphviz

# Keys in the config file
DOMAIN = 'domain'
TYPE = 'type'
PREFIX = 'predicate_prefix'
DELIMITER = 'delimiter'

class Options():
    def __init__(self, filename):
        self.filename = filename
        self.config = configparser.ConfigParser()
        self.config.read(filename)
    def get_option(self, datafile, key):
        # not safe
        return self.config[datafile][key]


class Config():
    def __init__(self,csv_filename, options, verbose=False):
        self.domain = ''
        self.type = ''
        self.prefix = ''
        self.delimiter = ''
        self.predicates = []
        self.csv_filename = csv_filename
        self.options = options
        self.verbose = verbose
        self.domain    = self.options.get_option(csv_filename, DOMAIN)
        self.type      = self.options.get_option(csv_filename, TYPE)
        self.prefix    = self.options.get_option(csv_filename, PREFIX)
        self.delimiter = self.options.get_option(csv_filename, DELIMITER)
        self.store = Graph()
        self.type = URIRef(self.domain + self.type)
    def print(self):
        print('Configuration for ' + self.csv_filename + ': ' \
              + self.domain + '|' + self.type + '|' + self.prefix \
              + '|' + self.delimiter)
    def parse_file(self):
        reader = csv.reader(open(self.csv_filename, "r"), \
                            delimiter=self.delimiter)
        try:
            for i, row in enumerate(reader):
                if i == 0:
                    for elem in row:
                        predicate = self.domain + format_predicate(elem)
                        self.predicates.append(URIRef(predicate))
                    if self.verbose:
                        print(self.predicates)
                else:
                    subject = URIRef(self.domain + self.prefix + str(i))
                    self.store.add((subject, RDF.type, self.type))
                    for n, elem in enumerate(row):
                        if not elem == '':
                            e = Literal(elem)
                            self.store.add((subject, self.predicates[n], e))
            if self.verbose:            
                print("%d lines loaded" % (i-1))
        except csv.Error as e:
            print("Error caught in loading csv file")
            print(e)
    def dump_store(self):
        storename = self.csv_filename.split('.')[0] + '.ttl'
        self.store.serialize(storename, format='turtle')
        if self.verbose:
            print('Store dumped')
    def get_store(self):
        return self.store


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

class Semantic():
    '''
    Semantic file is a CSV file with in first column the header name of the data file
    and in the second column orders about the type.
    '''
    def __init__(self, semantic, opt, verbose):
        self.semantic = semantic
        self.opt      = opt
        self.verbose  = verbose
        self.soptions = {}
        reader = csv.reader(open(self.semantic, "r"), \
                            delimiter=self.delimiter)
        


def usage():
    print("Utility to transform CSV files into RDF files")
    print("Usage: \n $ csv2rdf -f FILE_TO_CONVERT.csv [-o OPTIONS.ini] [-d INT] [-h]")
    print("Options:")
    print('"-o": If "-o OPTION.ini" is not provided, "csv2rdf.ini" will be searched for')
    print('"-d": Option to generate a graphviz/dot file')
    print('The output RDF file will be "FILE_TO_CONVERT.ttl" and is in Turtle format.')
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


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:o:d:s:hvt",
                                   ["file=", "options=", "display=", \
                                    "semantic=", "help", "verbose", "test"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    file    = None
    options = None
    verbose = False
    test    = False
    display = -1
    semantic = None
    for o, a in opts:
        if o == "-v":
            verbose = True
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-f", "--file"):
            file = a
        if o in ("-o", "--options"):
            options = a
        if o in ('-t', '--test'):
            test = True
        if o in ('-d', '--display'):            
            display = to_int(a, range(0, 3))
        if o in ('-s', '--semantic'):
            semantic = a
    # default option file name if no options are provided
    if options == None:
        options = 'csv2rdf.ini'
    if file == None:
        usage();
        sys.exit(1)
    opt = Options(options)
    conf = Config(file, opt, verbose)
    if test:
        conf.print()
        test_pred()
    if semantic != None:
        soptions = Semantic(file, opt, verbose)
        # TODO pass soptions to parse_file
        conf.parse_file()
    else:
        conf.parse_file()
    conf.dump_store()
    if display != -1:
        rdf_to_graphviz(conf.get_store(),file.split('.')[0], display)


if __name__ == '__main__':
    main()
