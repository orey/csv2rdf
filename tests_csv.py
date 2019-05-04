#============================================
# File name:      tests.py
# Author:         Olivier Rey
# Date:           December 2018
# License:        GPL v3
#============================================
#!/usr/bin/env python3

import unittest, os, sys

from rdflib import Graph, Literal, URIRef, RDF, BNode

from csv2rdf import *


class TestCsv2Rdf(unittest.TestCase):
    def test_Options(self):
        '''
        Objective is to read the config file
        '''
        try:
            options = Options('./tests/csv2rdf.ini')
            options.print()
            print(options.get_files())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)


    def test_RDFStore(self):
        '''
        The objective is to dump a very simple store
        '''
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
        '''
        The objective is to test the format predicate function
        '''
        try:
            print(format_predicate('I am a big-boy'))
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_default_csv_parser(self):
        '''
        The objective is to test the default parser
        '''
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
        '''
        The objective is to test the orchestrator
        Warning this test cumulates both files in the same store
        '''
        try:
            #orchestrator('toto.ini')
            store = RDFStore('./output/ORCHESTRE')
            orchestrator(Options('./tests/csv2rdf.ini'), store, verbose=True)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

class TestFullSemantics(unittest.TestCase):
    def test_FullSemantics(self):
        '''
        Objective is to read the config filetest the full semantics
        '''
        try:
            options = Options('./tests/csv2rdf2.ini')
            store = RDFStore('./output/Full_Semantic_CI_Catalog')
            orchestrator(options, store)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()
    
