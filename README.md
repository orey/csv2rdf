# CSV To RDF Converter

This program is a utility to transform CSV files into RDF files. It has 2 modes:

  * A standard mode without semantic grammar,
  * A mode with a semantic grammar


## Usage

```
$ csv2rdf -o [OPTIONS.ini] [-v]
```

Options:

  * "-o": [OPTION.ini] is an option file.

## Sample of option file

```
[./tests/test1.csv]
domain = https://www.example.com/rdf/design#
type = ConfigurationItem
predicate_prefix = CI_
delimiter = ;

[./tests/test2.csv]
domain = https://www.example.com/rdf/design#
type = ConfigurationItem
predicate_prefix = CI_
delimiter = ;
semantics = ./tests/semantics.csv
```


## CSV To RDF Comments

### Comments about the semantic parser

Vocabulary hypothesis: triples are decomposed in subject, predicate, object. Subjects and objects are roles that can be endorsed by URIRefs or Literal or blank nodes.

Despite the fact that there may be lists in some fields, we'll try not to use any blank node concept.

### Principle

![Principle](principle.png)

## Translation in semantic web

Here is a sample of interpretation that wa can have reading a CSV file.

The table is containing lines of `ConceptName`:
```
1. Li a ConceptName .
```

Depending on the value in the cell, if the value is an object:
```
2. Cij a Kj .
3. Cij Kj Li .
or
3. Li Kj Cij .
```

If the value oi the cell is a web semantic value:
```
3. Li kJ Cij .
```

(Cij does not have a type).

### Grammar

The semantic parser works with a semantic simplistic grammar. The idea of this grammar is to identify how the 3 following informations should be dealt with:

  * Line identifier
    * Each line is an instance of a particular concept. One column will contain the ID of the line. It will be the "master subject" that we will name `subject1`. `subject1` will be potentially used for triple generations when treating the rest of the cells.
  * Column name: generally used as a predicate.
  * Cell value: can be a Literal, an object or a subject. Can be related to `subject1` or not.

The grammar proposes the following semantic:

  * CSV line = `colum-name;command`
    * Possible evolution: use standard config file not to use CSV separators
  * colum-name will be formated with `_` by the parser (in case the column name has spaces in it)
  * command grammar = `role|type|direction|name` OR `ignore`, separator is `|`
    * Possible evolution: change separators
  * role =
    * `subject1` for the primary subject
	* `subject2` for others
	  * `subject2` is here to flag the cell as a subject or object. The fact that `subject2` be a subject or object is determine by the direction.
  * type = the type of the subject
    * Possible evolution: the type should be "defined" especially in a Turtle file. It should be an alias.
  * direction =
    * `S` for standard (meaning `subject1 predicate object`)
	* `R` for reverse (meaning `object predicate subject1`)
  * name = a string that describe better the predicate than the column name.
    * Possible evolution: the predicate type should be defined in a Turtle file. It should be an alias.
	* If this is not provided, the colum name is predicatified and is declared in the domain of the file.

Examples:

  * column_i;subject1|PN
  * column_j;subject2|PN|S|Father
  * column_k:literal
  * column_p;ignore

Note: the parser eliminates UTF8 errors.

----

See also:

  * [RDF design patterns](https://github.com/orey/graphapps/blob/master/rdf-design-patterns.md) (work in progress)
