#============================================
# File name:      tests.py
# Author:         Olivier Rey
# Date:           December 2018
# License:        GPL v3
#============================================
import unittest, os

from rdf2graphviz import *
from rdf2gml      import *
from csv2rdf      import *


class TestRdf2Graphviz(unittest.TestCase):
    def test_graphviz_with_basic_data(self):
        try:
            store = Graph()

            # Bind a few prefix, namespace pairs for pretty output
            store.bind("dc", DC)
            store.bind("foaf", FOAF)

            # Create an identifier to use as the subject for Donna.
            donna = BNode()

            # Add triples using store's add method.
            store.add((donna, RDF.type, FOAF.Person))
            store.add((donna, FOAF.nick, Literal("donna", lang="foo")))
            store.add((donna, FOAF.name, Literal("Donna Fales")))
    
            #print_store(store)
    
            # Dump store
            if not os.path.exists('./tests'):
                os.makedirs('./tests')
            store.serialize("./tests/test1.rdf", format="pretty-xml", max_depth=3)
    
            dot = Digraph(comment='Test1')
            add_rdf_graph_to_dot(dot, store)
            dot.render('./tests/test1.dot', view=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)
    
    def test_graphviz_with_online_data(self):
        try:
            store = Graph()
            result = store.parse("http://www.w3.org/People/Berners-Lee/card")
            print_store(store)

            # Dump store
            if not os.path.exists('./tests'):
                os.makedirs('./tests')
            store.serialize("./tests/test2.rdf", format="turtle")
    
            dot = Digraph(comment='Test2')
            add_rdf_graph_to_dot(dot, store)
            dot.render('./tests/test2.dot', view=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_graphviz_with_rdf_syntax(self):
        try:
            store = Graph()
            result = store.parse('./resources/22-rdf-syntax-ns.n3', format='n3')
            print_store(store)
            dot = Digraph(comment='test3')
            dot.graph_attr['rankdir'] = 'LR'
            add_rdf_graph_to_dot(dot, store, 1)
            dot.render('./tests/test3.dot', view=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_graphviz_with_simplified_rdf_syntax(self):
        try:
            store = Graph()
            result = store.parse('./resources/22-rdf-syntax-ns-simplified.n3', format='n3')
            print_store(store)
            dot = Digraph(comment='test4')
            dot.graph_attr['rankdir'] = 'LR'
            add_rdf_graph_to_dot(dot, store, 1)
            dot.render('./tests/test4.dot', view=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)


class TestRdf2Gml(unittest.TestCase):
    def test_gml_basic(self):
        try:
            store = Graph()
            result = store.parse('./resources/22-rdf-syntax-ns-simplified.n3', format='n3')
            add_rdf_graph_to_gml('./tests/test5.gml', store)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

            
class TestCsv2Rdf(unittest.TestCase):
    def test_Options(self):
        try:
            options = Options('csv2rdf.ini')
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
            options = Options('csv2rdf.ini')
            store = RDFStore('TEST_dump')
            default_csv_parser(options, 'test1.csv', store, True)
            store.dump(True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

    def test_orchestrator(self):
        try:
            #orchestrator('toto.ini')
            orchestrator(Options('csv2rdf.ini'), RDFStore('ORCHESTRE'), verbose=True)
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)


    def test_with_gml_output(self):
        try:
            options = Options('csv2rdf2.ini')
            store = RDFStore('Z_semantic')
            orchestrator(options, store, False)
            store.dump()
            add_rdf_graph_to_gml('Z_semantic.gml', store.get_store())
            self.assertTrue(True)
        except Exception as e:
            print(e)
            self.assertTrue(False)

            
if __name__ == '__main__':
    unittest.main()
    
