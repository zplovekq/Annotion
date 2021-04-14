import rdflib
import json
import re
from rdflib import Namespace, RDF, RDFS
def owl_parse(owl_path):
    result=[]
    g = rdflib.Graph()
    g.parse("theory.owl")
    q='''SELECT ?class ?classLabel
    WHERE {
    ?class rdf:type owl:Class.
    ?class rdfs:label ?classLabel.
    }'''
    for a, b in g.query(q):
        result.append(str(b))
    return result
# print(owl_parse(None))
# a = g.query("SELECT ?class WHERE { ?class a owl:Class }")
d =dict()
d["习近平"]="PER"
d["3月3日"]="T"
f=open("dict.json","w",encoding="utf-8")
f.write(json.dumps(d,ensure_ascii=False))
# for s, p, o in g:
#     print(s,p,o)
    # if type(s) == rdflib.term.URIRef:
    #         # print('Subject = ',s)
    #         # print(' ')
    #         # print('Property = ',p)
    #         # print(' ')
    #         if type(o) == rdflib.term.Literal:
    #             print(o,type(s),type(p))
    #         # print()



