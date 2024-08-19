# CSV To RDF Converter v4

## Overview

This program is a utility to transform CSV files into RDF files. It has 2 modes:

  * A basic mode without semantic grammar,
  * A mode with a semantic grammar

## Usage

```
$ python csv2rdf-v2 -c [CONFIG.ini] -i
```

`CONFIG.ini` is structured as a [Python configuration file](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure).

## Sample of option file

```
[./tests/test1.csv]
domain = https://www.example.com/rdf/
type = Part
predicate_prefix = CI_
delimiter = ;
active = False

[./tests/test2.csv]
domain = https://www.example.com/rdf/
# Those 2 fields are not used in the case of the semantic parser
type = NotUsed
predicate_prefix = NotUsed
delimiter = ;
active = True
semantics = semantics.ini
```

The `type` and `predicate_prefix` are only used in the basic mode of the program. If you provide a configuration file for `semantics`, those fields will be ignored.

Note: the 2 fields must be present anyway even if there is a provided semantic configuration file. Please keep the fields even with dummy data or the semantic mode won't work (I had no time to implement it properly).

The `domain` field is very important and will flag any data of the source.

## Step by step analysis of the semantic configuration

### Introduction

The semantic configuration file is also a [Python configuration file](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure) and so a `.ini`.

The section names are the **exact** names of the CSV file header.

A triple is considered to be: `subject predicate object .`

### Step by step analysis of the configuration file

#### Primary key (pkey)

```
[PNR]
# pkey: will serve for all triples
cell = pkey
celltypes = pnr
```

The file must contain a primary key, here the Part Number. By using the `pkey` value, we tell the parser that it will find the primary key in the `PNR` column.

Part numbers have types, so the system will generate something like `domain:cell a domain:pnr .`, and possibly other triples (see v4 description above).

#### Columns to be ignored

```
[MOI]
cell = ignore
```

This indicates that the column is ignored and the cells of this colum will not generate any triple.
    
#### Basic cell (subject/object)

```
[IPPN]
cell = subject
celltypes = ippn
columntypes = ippn_contains
```

Note: The column name is always the predicate, because it is the only thing that is not variable line after line (the pkey is and the cell value also is).

A classic example of the grammar :

* By saying that the cell is `subject`, while keeping in mind that we have a `pkey` value on this line, the system will generate `domain:cell domain:ippn_contains domain:pkey .`
    * A variation of that is the cell being the `object`.
* cell is of type `ippn`, so we'll generate: `domain:cell a domain:ippn .`
* `ippn` is a type so: `domain:ippn a rdfs:Resource .`, but we have also `domain:ippn_contains a rdf:Property`.

v4 introduced more generated triples, see below.

```
[CSN]
cell = object
celltypes = csn
columntypes = csn_located_in
```

Above, another sample with the cell as an `object` in the triple.

#### Cell alteration 1: Mapping cell value with a key/value list 

```
[SRV]
cell = object,map(all;*nations*)
celltypes = nation
columntypes = serviced_to

[*nations*]
FIF = Finland
NON = Norway
SES = Sweden
...
```

In the sample above, we will map the cell (that will be considered as an `object`) on the `*nations*` list. When a section name is surrounded by stars, it means that it is a list. We expect to have cells taking the `FIF`, `NON` or `SES` values and to replace them in the triples by respectively `Finland`, `Norway` and `Sweden`.

Note two things about `object,map(all;*nations*)`:

* The action `map` is separated from the role of the cell by a comma;
* The parameters of the `map` are separated by a semicolon:
    * The first one `all` means the key of the mapping is all the characters of the cell
    * This first parameter can be replaced by a subset of parameters following the conventions of Python:
        * `0:4` means from the character of index 0 (the first of the cell string) to the character of index 3 included (4 excluded),
        * `1:-1` means from the character of index 1 to the character before the last one,
        * Etc.
        
```
[Effectivity from (digits 1-4 of EFY)$1]
cell = object
celltypes = effectivity
columntypes = effectivity_from,effectivity_link

[Effectivity from (digits 1-4 of EFY)$2]
cell = object,map(1:2;*configs*)
celltypes = aircraft_configuration
columntypes = mountable_on,effectivity_link
```

The second sample above is showing in the `map` command a subset of the cell characters, `1:2` meaning we want to get only the second character of the string (index 1 included and index 2 excluded).

This couple of actions have identical names except that they finish by `$1` and `$2`. This convention is used when the same cell must be treated in several different ways to generate different sets of triples. Note that before the `$`, we still have the exact name of the CSV column.

We can also note that we have a chain of column types that is more complicated than the usual ones. The semantic parser will generate the chain: `domain:mountable_on rdfs:subPropertyOf domain:effectivity_link .` and `domain:effectivity_link a rdf:Property . `. See below the v4 features.

#### Cell alteration 2: Extracting data from a cell

```
[Effectivity to (digits 5-8 of EFY)$2]
cell = object,extract(-3:)
celltypes = bbl_validity_code
columntypes = effectivity_to_bbl,effectivity_link
```

Sometimes, we just want to extract from chain just the relevant letters for the triples. The `extract` function is doing that, having one parameter that is similar to the one of `map`.

#### Cell alteration 3: Adding a prefix

```
[NSC]
cell = object,prefix(nsc_)
celltypes = higher_level_nato_part_id,nato_part_id
columntypes = nato_supply_class,nato_codification
```

Last function, the `prefix` adds a prefix to the cell string in order to generate the URI name.

#### More cell alterations?

We can alter cell values in multiple ways and not all are implemented, for sure.

## V4 clarifications

## Principles

### Vocabulary

The vocabulary behind the software was clarified.

* A basic triple is noted `domain1:subject domain2:predicate domain3:object .`
* We will name **data** any subject of object in a hierarchy that leads to `rdfs:Class` and "relation" all entities leading to `rdf:Property` through a **chain of types**.
* A cell value is an instance of a class, noted `rdf:type` or `a`.
    * It can be preprocessed before the triple is generated.
* A class type is instance of `rdfs:Class` and often located in a type hierarchy.
    * Any subtype of the class type is a `rdfs:subClassOf` the very type.
    * This defined the chain of types for cell types.
* A property type is instance of `rdf:Property` and often located in a type hierarchy.
    * Any subproperty of the property type is a `rdfs:subPropertyOf` the very type.
    * This defined the chain of types for property types.

### Principle #1

When data exist, they exist forever, independently from their version or applicability.

## Principle #2 (implemented in v4)

Data are stamped with their creation date, when they enter the semantic database (or with another significant date) like `domain1:data global:created domain3:"2023-12-08"^^xsd:date`.

## Principle #3 (not implemented in v4)

Versions are reserved for a specific **namespace of relations**, in relation with an absolute namespace for long term relations.

Let's take an example:

When importing the data into the triple store the first time, we generate:

* `domain1:Part_12 appdomain_v01:applicable_to domain1:Variant_G .`
* `appdomain_v01:applicable_to rdfs:subPropertyOf applicability:applicable_to.`

This enables SPARQL reasoning.

Then, when we import further versions, we have:

* `domain1:Part_12 appdomain_v02:applicable_to domain1:Variant_G .`
* `domain1:Part_12 appdomain_v02:applicable_to domain1:Variant_H .`
* `appdomain_v02:applicable_to rdfs:subPropertyOf applicability:applicable_to .`

We can track the versions at each new version of data, and we can make SPARQL reasoning work because their father property is absolute.

Note: That feature was not implemented even if it is quite easy to do because it depends on the various SPARQL requests that we intend to develop for the specific use cases.

## A sample of V4

For a simple cell, we obtain the following triples generated:

```
------
Domain: https://www.nhindustries.com/rdf/mipl/
Cell value: C0418E023
pkeyvalue: S000N0011051
<https://www.nhindustries.com/rdf/mipl/C0418E023> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.nhindustries.com/rdf/mipl/ippn> .
Continue?
```

Each value is typed by the type present in the configuration file in the order defined by the configuration file (here subject): `cellvalue a celltype .`

```
[IPPN]
cell = subject
celltypes = ippn
columntypes = ippn_contains
```

The pkey was identified in the conf file as being the value in the column `PNR` as shown below.

```
[PNR]
# pkey: will serve for all triples
cell = pkey
celltypes = pnr
```

So the following triples can associate the cell value to the pkey in subject/object role depending on the configuration.

```
<https://www.nhindustries.com/rdf/mipl/C0418E023> <https://www.nhindustries.com/rdf/mipl/ippn_contains> <https://www.nhindustries.com/rdf/mipl/S000N0011051> .
Continue?
```

The record above is the main one. The following triple was generated: `cellvalue columntype pkey .`

Then we have to create the `rdfs:domain` and `rdfs:range` of all column types with the types of the cell and the type of the pkey.

```
<https://www.nhindustries.com/rdf/mipl/ippn_contains> <http://www.w3.org/2000/01/rdf-schema#domain> <https://www.nhindustries.com/rdf/mipl/ippn> .
Continue?
<https://www.nhindustries.com/rdf/mipl/ippn_contains> <http://www.w3.org/2000/01/rdf-schema#range> <https://www.nhindustries.com/rdf/mipl/pnr> .
Continue?
```

This will enable SPARQL request and inference once the data are imported into a triplestore.

We now have the create the type chain, both for the cell type (at the end, we have `rdfs:Class`) and for the colum type (at the end, we have `rdf:Property`). This typing is crucial for inferences once in the triplestore.

```
<https://www.nhindustries.com/rdf/mipl/ippn> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2000/01/rdf-schema#Class> .
Continue?
```

Note that each type line of the configuration file can provide an ordered list of types. In that case, all types will be chained together, the cell type chain ending in `rdfs:Class` and the relationship type chain ending in `rdf:Property`.

We have a sample above. `vapmov_country_applicable_to` will be a `rdfs:subPropertyOf vapmov .`, `vapmov` being a `rdf:Property`. The same with `rdfs:subClassOf` for cell values.

```
[VAPMOV$1]
# Should generate a duplicate from SRV
cell = object,map(0:1;*nationcodes*)
celltypes = nation
columntypes = vapmov_country_applicable_to,vapmov
```

The initial sample shows:

```
<https://www.nhindustries.com/rdf/mipl/ippn_contains> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/1999/02/22-rdf-syntax-ns#Property> .
Continue?
```

Then we generate the date created of the record attached to the cell. That parameter will be tunable in the future.

```
<https://www.nhindustries.com/rdf/mipl/C0418E023> <https://www.nhindustries.com/rdf/mipl/date_created> <2024-08-19> .
Continue?
Done for cell: C0418E023
------
```


