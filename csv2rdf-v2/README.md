# CSV To RDF Converter

This program is a utility to transform CSV files into RDF files. It has 2 modes:

  * A standard mode without semantic grammar,
  * A mode with a semantic grammar


## Usage

```
$ csv2rdf -c [CONFIG] -o [OUTPUT] [-v]
```

## Sample of option file

```
[./tests/test1.csv]
domain = https://www.example.com/rdf/
type = ConfigurationItem
predicate_prefix = CI_
delimiter = ;
active = False

[./tests/test2.csv]
domain = https://www.example.com/rdf/
type = ConfigurationItem
predicate_prefix = CI_
delimiter = ;
active = True
semantics = ./tests/semantics.csv
```

## CSV To RDF Comments

### Comments about the semantic parser

Vocabulary hypothesis: triples are decomposed in subject, predicate, object. Subjects and objects are "roles" that can be endorsed by URIRefs or Literal or blank nodes.

Despite the fact that there may be lists in some fields, we'll try not to use any blank node concept but generate multiple triples instead.

## Translation in semantic web

### Type

`type` in the configuration file will be the type of each triple, in the context of the `domain` that you have provided.

The CSV file is containing lines of `domain:type`:
```
domain:Li a domain:type .
```

### Hierarchy of types and relashionships

For sure, once in the triple store, you have to link all types and all relationships to existing types, for instance:
```
domain:type a rdfs:Resource .
```

This triple and all the types that you will ue and all the relationships must be linked to `rdfs:Resource` or `rdfs:Property`. Surely, they can have their own hierarchy of types, which will enable sparql to 'reason' on them.

### Modeling the cell information

Depending on the value in the cell, if the value is an object, we can have the following cases.

`Li` is the identifier of the i-th line and `Kj` is the identifier of the j-th column; `Cij` is the cell.

If `Cij` is a value, we have 2 choices:

* `domain:Li domain:Kj domain:Cij .`
* `domain:Ki domain:Li domain:Cij .`

The second one is weird because `Li` is supposed to be an object, so be at the subject or object place rather than at the predicate place.

If `Cij` is not a value, it is an object, so we have to type it :

```
domain:Cij a domain:Kj .
```

We then have multiple possibilities:

* `domain:Li domain:Kj domain:Cij .`
* `domain:Li domain:Cij domain:Kj .`
* `domain:Cij domain:Kj domain:Li .`
* `domain:Kj domain:Cij domain:Li .`
* Etc.

### Grammar

The semantic parser works with a semantic simplistic grammar. The idea of this grammar is to identify how the 3 following informations should be dealt with:

* Line identifier
    * Each line is an instance of a particular concept. One column will contain the ID of the line. It will be the "master subject" that we will name `pkey`. `pkey` will be potentially used for triple generations when treating the rest of the cells.
* Column name: generally used as a predicate.
* Cell value: can be a Literal, an object or a subject. Can be related to `pkey` or not.

The grammar proposes the following semantic:

* CSV line = `colum-name;command`
    * colum-name will be formated with `_` by the parser (in case the column name has spaces in it) when generating triples
* command grammar = `cellrole|celltype|columnrole|columnalias` OR `ignore`, separator is `|`
    * `cellrole` = `pkey` or `subject` or `predicate` or `object` or `value`
        * `pkey` for the primary subject (the line identifier, that does not need to be unique). Note that there is only one column that is `pkey` in the file.
    * `celltype` = the type of the cell
        * Not applicable if the cell is a `value`
    * `columrole` = `subject` or `predicate` or `object`
    * `columnalias` = a string that describe better the predicate than the column name.
