# CSV To RDF Converter v3

## Objectives of the new version

* Manage the versions of triples and enable the deltas between versions
* Propose simple SPARQL queries based on whatever Graph

### Principles

#### Vocabulary:

* A basic triple is noted `domain1:subject domain2:predicate domain3:object .`
* We will name "data" any subject of object in a hierarchy that leads to `rdf:type` and "relation" all entities leading to `rdf:Property`

#### Principle #1

When data exist, they exist forever, independently from their version or applicability.

### Principle #2

Data are stamped with their creation date, when they enter the semantic database (or with another significant date) like `domain1:data global:created domain3:"2023-12-08"^^xsd:date`.

### Principle #3

Versions are reserved for a specific namespace of relations, in relation with an absolute namespace for long term relations.

Let's take an example:

* `domain1:Part_12 appdomain_v01:applicable_to domain1:Variant_G .`
* `domain1:Part_12 appdomain_v02:applicable_to domain1:Variant_G .`
* `domain1:Part_12 appdomain_v02:applicable_to domain1:Variant_H .`
* `appdomain_v01:applicable_to rdfs:subPropertyOf applicability:applicable_to.`
* `appdomain_v02:applicable_to rdfs:subPropertyOf applicability:applicable_to.`

We can track the versions at each new version of data, and we can make SPARQL reasoning work because their father property is absolute.

## See also

The README file of the version 2 of this code in the `csv2rdf2` folder.

