# CSV To RDF Converter v3

## Change log

### What was done

This version is essentially the same than the v2 version except that:

* Only the relevant cases are managed
    * The column name is now **always** the predicate (because other situations make no sense).
    * The `column` entry in the configuration file is still there and will have to be removed in v4.
* The object and suject types are all `subClassOf rdfs:Class` and the predicates types are all `subPropertyOf rdf:Property`.
* The `rdfs:domain` and `rdfs:range` were implemented for all the predicates which enables SPARQL inference.

The v4 will change some stuff:

* Removal of the column 'role' in the main configuration file, because the column type should always be the predicate.
* Timestamp of the objects and subjects with the date of processing of the file, understood as the date the data were included into a semantic database (like Jena or Allegro).
* The predicates will be versioned with a super type. The versioning system will use URI suffixes.
* The documentation will be complete and the reasons of the design choices will be explained in more details.


### Principles

#### Vocabulary:

* A basic triple is noted `domain1:subject domain2:predicate domain3:object .`
* We will name "data" any subject of object in a hierarchy that leads to `rdfs:Class` and "relation" all entities leading to `rdf:Property`
* A cell value is an instance of a class, noted `rdf:type` or `a`.
    * It can be preprocessed before the triple is generated.
* A class type is instance of `refs:Class` and often located in a type hierarchy.
* A property type is instance of `rdf:Property` and often located in a type hierarchy.

#### Principle #1

When data exist, they exist forever, independently from their version or applicability.

### Principle #2 (not implemented in v3)

Data are stamped with their creation date, when they enter the semantic database (or with another significant date) like `domain1:data global:created domain3:"2023-12-08"^^xsd:date`.

### Principle #3 (not implemented in v3)

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

