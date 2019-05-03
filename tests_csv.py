#============================================
# File name:      tests.py
# Author:         Olivier Rey
# Date:           December 2018
# License:        GPL v3
#============================================
import unittest, os, sys

from rdflib import Graph, Literal, URIRef, RDF, BNode

sys.path.insert(0, '/home/olivier/Documents/github/rdftools')
from csv2rdf import *

#sys.path.insert(0, '/home/olivier/Documents/github/rdfviz')
#from rdfviz import *


class TestCsv2Rdf(unittest.TestCase):
    def test_Options(self):
        try:
            options = Options('./tests/csv2rdf.ini')
            options.print()
            print(options.get_files())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_RDFStore(self):
        try:
            store = RDFStore('./output/test_RDFStore')
            subject = BNode()
            object = URIRef('https://www.test.urg/sem#oups')
            store.add((subject, RDF.type, object))
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)
            
    def test_pred(self):
        try:
            print(format_predicate('I am a big-boy'))
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_default_csv_parser(self):
        try:
            self.test_pred()
            options = Options('./tests/csv2rdf.ini')
            store = RDFStore('./output/TEST_dump')
            default_csv_parser(options, './tests/test1.csv', store, True)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_orchestrator(self):
        try:
            #orchestrator('toto.ini')
            store = RDFStore('./output/ORCHESTRE')
            orchestrator(Options('./tests/csv2rdf.ini'), store, verbose=True)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
    
