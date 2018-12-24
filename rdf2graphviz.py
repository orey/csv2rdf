#============================================
# File name:      rdf2graphviz.py
# Author:         Olivier Rey
# Date:           November 2018
# License:        GPL v3
#============================================

import uuid, rdflib, sys

from rdflib import Graph, Literal, BNode, RDF
from rdflib.namespace import FOAF, DC
from graphviz import Digraph

MAX_STRING_LENGTH = 40

def analyze_uri(uri):
    tokens = uri.split('/')
    if 'http:' in tokens or 'https:' in tokens:
        domain = tokens[2].split('.')[-2]
        mtype  = tokens[-1]
        return domain + ':' + mtype 
    else:
        print('Strange URI: ' + str(uri))
        return str(uri)


class RDFNode():
    def __init__(self, ident):
        self.id = uuid.uuid1()
        self.name = "void"
        if not isinstance(ident, rdflib.term.Identifier):
            raise TypeError("Unrecognized type: " + str(type(ident)))
        if type(ident) == rdflib.term.URIRef:
            self.name = analyze_uri(ident.toPython())
        elif type(ident) == rdflib.term.BNode \
          or type(ident) == rdflib.term.Literal:
            value = str(ident.toPython())
            if len(value) > MAX_STRING_LENGTH:
                self.name = value[0:MAX_STRING_LENGTH] + '...'
            else:
                self.name = value
        else:
            raise TypeError("Unrecognized type: " + str(type(ident)))
    def to_dot(self):
        return str(self.id), str(self.name)
    def to_gml(self):
        return self.id.int, str(self.name)
    def get_name(self):
        return self.name
    def get_id(self):
        return str(self.id)
    def get_int_id(self):
        return self.id.int

    
class RDFRel(RDFNode):
    def __init__(self, ident, source, target):
        RDFNode.__init__(self, ident)
        if type(source) != RDFNode:
            raise TypeError("Unrecognize type: " + str(type(source)))
        elif type(target) != RDFNode:
            raise TypeError("Unrecognize type: " + str(type(target)))
        self.source = source
        self.target = target
    def to_dot(self, label=True):
        # returns the label to print
        if label:
            return self.source.get_id(), self.target.get_id(), str(self.name)
        else: # returns only the link
            return self.source.get_id(), self.target.get_id()
    def to_gml(self):
        return self.source.get_int_id(), self.target.get_int_id(), str(self.name)
    def get_source_id(self):
        return self.source.get_id()
    def get_target_id(self):
        return self.target.get_id()

    
def print_rel_as_box(rel, dot):
    dot.node(rel.get_id(),rel.get_name(), shape='box')
    dot.edge(rel.get_source_id(), rel.get_id())
    dot.edge(rel.get_id(), rel.get_target_id())
            

def add_to_nodes_dict(rdfnode, node_dict):
    '''
    We suppose that the parser will create an instance of node for each
    parse triple
    '''
    name = rdfnode.get_name()
    if name in node_dict:
        print("Info: same node won't be written in the dictionary")
        return node_dict[name]
    else:
        node_dict[name] = rdfnode
        return node_dict[name]

    
def add_to_rels_dict(rdfrel, rel_dict):
    '''
    We suppose that all relationships are unique, even if they have
    the same label
    '''
    rel_dict[rdfrel.get_id()] = rdfrel

    
def add_rdf_graph_to_dot(dot, rdfgraph, mode=0):
    '''
    mode=0 (default): prints labels in edges
    mode=1: prints labels in boxes
    mode=2: prints no labels
    '''
    node_dict = {}
    rel_dict  = {}
    for s, p, o in rdfgraph:
        source = add_to_nodes_dict(RDFNode(s),node_dict)
        target = add_to_nodes_dict(RDFNode(o),node_dict)
        add_to_rels_dict(RDFRel(p, source, target),rel_dict)
    for elem in node_dict.values():
        dot.node(*elem.to_dot(), color="blue", fontcolor='blue')
    if mode==1:
        for elem in rel_dict.values():
            print_rel_as_box(elem, dot)
    elif mode==2:
        for elem in rel_dict.values():
            dot.edge(*elem.to_dot(False))
    else:
        for elem in rel_dict.values():
            dot.edge(*elem.to_dot())
    return dot


def create_gml_node_string(id, name):
    return 'node [\n  id ' + str(id) + '\n  label "' + name + '"\n]\n'

def create_gml_rel_string(sourceid, targetid, name):
    return 'edge [\n  label "' + name + '"\n' \
           '  source ' + str(sourceid) + '\n  target '+ str(targetid) + '\n]\n'
    

def add_rdf_graph_to_gml(gmlfilename, rdfgraph):
    '''
    Creates a GML file from the RDF file with the same assumptions
    than the graphviz visual representation.
    Can be used with Gephi
    '''
    node_dict = {}
    rel_dict = {}
    f = open(gmlfilename, 'w')
    f.write('graph [\n')
    for s, p, o in rdfgraph:
        source = add_to_nodes_dict(RDFNode(s),node_dict)
        target = add_to_nodes_dict(RDFNode(o),node_dict)
        add_to_rels_dict(RDFRel(p, source, target),rel_dict)
    for elem in node_dict.values():
        f.write(create_gml_node_string(*elem.to_gml()))
    for elem in rel_dict.values():
        f.write(create_gml_rel_string(*elem.to_gml()))
    f.write(']\n')
    f.close()

    
def print_store(store):
    # Iterate over triples in store and print them out.
    print("--- printing raw triples ---")
    for s, p, o in store:
        print(s, p, o)
    
    # Serialize as XML
    print("--- start: rdf-xml ---")
    print(store.serialize(format="pretty-xml"))
    print("--- end: rdf-xml ---\n")

    # Serialize as Turtle
    print("--- start: turtle ---")
    print(store.serialize(format="turtle"))
    print("--- end: turtle ---\n")

    # Serialize as NTriples
    print("--- start: ntriples ---")
    print(store.serialize(format="nt"))
    print("--- end: ntriples ---\n")
    
def test1():
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
    
    print_store(store)
    
    # Dump store
    store.serialize("test1.rdf", format="pretty-xml", max_depth=3)
    
    dot = Digraph(comment='Test1')
    add_rdf_graph_to_dot(dot, store)
    dot.render('test1.dot', view=True)
    
def test2():
    store = Graph()
    result = store.parse("http://www.w3.org/People/Berners-Lee/card")
    print_store(store)

    # Dump store
    store.serialize("test2.rdf", format="turtle")
    
    dot = Digraph(comment='Test2')
    add_rdf_graph_to_dot(dot, store)
    dot.render('test2.dot', view=True)

def test3():
    store = Graph()
    result = store.parse("http://www.w3.org/People/Berners-Lee/card")
    print_store(store)

    # Dump store
    store.serialize("test3.rdf", format="turtle")
    
    dot = Digraph(comment='Test3')
    add_rdf_graph_to_dot(dot, store, False)
    dot.render('test3.dot', view=True)

def test4():
    store = Graph()
    result = store.parse('22-rdf-syntax-ns.n3', format='n3')
    print_store(store)
    dot = Digraph(comment='test4')
    dot.graph_attr['rankdir'] = 'LR'
    add_rdf_graph_to_dot(dot, store, 1)
    dot.render('test4.dot', view=True)
    
    
def rdf_to_graphviz(store, name='default', mode=0):
    dot = Digraph(comment=name, format='pdf')
    dot.graph_attr['rankdir'] = 'LR'
    add_rdf_graph_to_dot(dot, store, mode)
    dot.render(name + '.dot', view=True)
    
if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) != 2:
        test1()
        exit(1)
    a = sys.argv[1]
    if a == 1:
        test1()
    elif a == '2':
        test2()
    elif a == '3':
        test3()
    elif a == '4':
        test4()
    else:
        test1()
