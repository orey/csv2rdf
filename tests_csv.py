#============================================
# File name:      tests.py
# Author:         Olivier Rey
# Date:           December 2018
# License:        GPL v3
#============================================
import unittest, os

from csv2rdf import *

import rdfviz
from rdfviz import *

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
            store = RDFStore('test_RDFStore')
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
            store = RDFStore('TEST_dump')
            default_csv_parser(options, './tests/test1.csv', store, True)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_orchestrator(self):
        try:
            #orchestrator('toto.ini')
            orchestrator(Options('./tests/csv2rdf.ini'), RDFStore('ORCHESTRE'), verbose=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)


class TestCsv2RdfWithGml(unittest.TestCase):
    def test_with_gml_output(self):
        try:
            options = Options('./tests/csv2rdf2.ini')
            store = RDFStore('Z_semantic')
            orchestrator(options, store, False)
            store.dump()
            add_rdf_graph_to_gml('Z_semantic.gml', store.get_store())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

            
class TestCsv2RdfWithGml(unittest.TestCase):
    def test_with_gml_output(self):
        try:
            options = Options('csv2rdf2.ini')
            if not os.path.exists('./tests'):
                os.makedirs('./tests')
            store = RDFStore('./tests/Z_semantic')
            orchestrator(options, store, False)
            store.dump()
            rdf2gml.add_rdf_graph_to_gml('./tests/Z_semantic.gml', store.get_store())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

            
if __name__ == '__main__':
    unittest.main()
    
