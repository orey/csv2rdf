#============================================
# File name:      rdf2graphviz.py
# Author:         Olivier Rey
# Date:           November 2018
# License:        GPL v3
#============================================

import uuid, rdflib, sys, os, getopt

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
    '''
    This class is managing the representation of a RDF node.
    '''
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
    '''
    This class is representing the representation of a relationship. It is an extension of RDFNode.
    '''
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
    ''''
    This function is adding some extra representation to relationships.
    '''
    dot.node(rel.get_id(),rel.get_name(), shape='box')
    dot.edge(rel.get_source_id(), rel.get_id())
    dot.edge(rel.get_id(), rel.get_target_id())
            

def add_to_nodes_dict(rdfnode, node_dict):
    '''
    Helper function to build the dict of node representations
    We suppose that the parser will create an instance of node for each parse triple
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
    Helper function to build the dictionnary of relationship representations
    We suppose that all relationships are unique, even if they have the same label
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
    
    
def rdf_to_graphviz(store, name='default', mode=0):
    dot = Digraph(comment=name, format='pdf')
    dot.graph_attr['rankdir'] = 'LR'
    add_rdf_graph_to_dot(dot, store, mode)
    dot.render(name + '.dot', view=True)


def usage():
    print('RDF to GraphViz utility')
    print('Usage')
    print('$ python3 rdf2graphviz.py -i [input_file_or_url] -o [output_dir] (other_options)')
    print('-i or --input NAME: filename or URL')
    print('-o or --output NAME: directory name. Default will be "./tests/"')    
    print('Other options')
    print('-f or --format: "xml", "n3", "ntriples" or other format supported by Python rdflib. Default format is "n3".')
    print('-h or --help: usage')

def build_name(input):
    '''
    This function takes the input of the command line and tries to build a name
    '''
    temp = input.split('/')[-1]
    if not '\\' in temp:
        return temp
    else:
        return temp.split('\\')[-1]
    
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hi:o:f:v", [])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    input = None
    outputdir = './tests'
    myformat = 'n3'
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-i", "--input"):
            input = a
        elif o in ("-o", "--output"):
            outputdir = a
        elif o in ("-f", "--format"):
            myformat = a
        else:
            assert False, "unhandled option"
    # Check input
    if input == None:
        print("Input file or URL cannot be void.")
        usage()
        sys.exit()
    name = build_name(input)
    # Check output dir
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    store = Graph()
    result = store.parse(input, format=myformat)
    dot = Digraph(comment="RDF to Graphviz: " + name)
    dot.graph_attr['rankdir'] = 'LR'
    add_rdf_graph_to_dot(dot, store, 1)
    dot.render(os.path.join(outputdir,name + '.dot'), view=True)
