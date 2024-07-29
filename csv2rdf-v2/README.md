# CSV To RDF Converter v2

## A better version

This program is a utility to transform CSV files into RDF files. It has 2 modes:

  * A standard mode without semantic grammar,
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

## Step by step analysis of the semantic configuration

### Introduction

The semantic configuration file is also a [Python configuration file](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure) and so a `.ini`.

The section names are the **exact** names of the CSV file header.

A triple is considered to be: `subject predicate object .`

### Step by step

```
[PNR]
# pkey: will serve for all triples
cell = pkey
celltypes = pnr,rdfs:Resource
```

The file must contain a primary key, here the Part Number. By using the `pkey` value, we tell the parser that it will find the primary key in the `PNR` column.

Part numbers have types, so the system will generate something like `domain:cell a domain:pnr .`

The `domain:pnr` is a type attached to `rdfs:Resource`. So the system will generate  `domain:pnr a rdfs:Resource .`

Those 2 triples will be generated each time unless the value of the cell is a `Literal`.

```
[MOI]
cell = ignore
```

This indicates that the column is ignored and the cells of this colum will not generate any triple.

```
[IPPN]
cell = subject
celltypes = ippn,rdfs:Resource
column = predicate
columntypes = ippn_contains,rdf:Property
```

A classic example of the grammar :

* By saying that the cell is `subject` and the colum is `predicate`, while keeping in ming that the `pkey` is the 3rd member of the triple, the system will generate `domain:cell domain:ippn_contains domain:pkey .`
    * A variation of that is the cell being the `object` and the column being the `predicate`. All possibilities are feasible, between the cell and the column, considering that the `pkey` is always the 3rd member of the triple.
* cell is of type `ippn`, so we'll generate: `domain:cell a domain:ippn .`
* `ippn` is a type so: `domain:ippn a rdfs:Resource .`, but we have also `domain:ippn_contains a rdf:Property`.

```
[CSN]
cell = object
celltypes = csn,rdfs:Resource
column = predicate
columntypes = csn_located_in,rdf:Property
```

Above, another sample with the cell as an `object` in the triple.

```
[SRV]
cell = object,map(all;*nations*)
celltypes = nation,rdfs:Resource
column = predicate
columntypes = serviced_to,rdf:Property

[*nations*]
FIF = Finland
NON = Norway
SES = Sweden
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
celltypes = effectivity,rdfs:Resource
column = predicate
columntypes = effectivity_from,effectivity_link,rdf:Property

[Effectivity from (digits 1-4 of EFY)$2]
cell = object,map(1:2;*configs*)
celltypes = aircraft_configuration,rdfs:Resource
column = predicate
columntypes = mountable_on,effectivity_link,rdf:Property
```
The second sample above is showing in the `map` command a subset of the cell characters, `1:2` meaning we want to get only the second character of the string (index 1 included and index 2 excluded).

This couple of actions have identical names except that they finish by `$1` and `$2`. This convention is used when the same cell must be treated in several different ways to generate different sets of triples. Note that before the `$`, we still have the exact name of the CSV column.

We can also note that we have a chain of column types that is more complicated than the usual ones. The semantic parser will generate the chain: `domain:mountable_on a domain:effectivity_link .` and `domain:effectivity_link a rdf:Property . `

```
[Effectivity to (digits 5-8 of EFY)$2]
cell = object,extract(-3:)
celltypes = bbl_validity_code,rdfs:Resource
column = predicate
columntypes = effectivity_to_bbl,effectivity_link,rdf:Property
```

Sometimes, we just want to extract from chain just the relevant letters for the triples. The `extract` function is doing that, having one parameter that is similar to the one of `map`.

```
[NSC]
cell = object,prefix(nsc_)
celltypes = higher_level_nato_part_id,nato_part_id,rdfs:Resource
column = predicate
columntypes = nato_supply_class,nato_codification,rdf:Property
```

Last function, the `prefix` adds a prefix to the cell string in order to generate the URI name.



