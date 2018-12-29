#============================================
# File name:      tests.py
# Author:         Olivier Rey
# Date:           December 2018
# License:        GPL v3
#============================================
import unittest, os

from rdf2graphviz import *
from rdf2gml      import *


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
                

            
            
if __name__ == '__main__':
    unittest.main()
    
