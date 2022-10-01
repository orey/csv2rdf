from distutils.core import setup

with open("README.md", 'r') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(name='csv2rdf',
    version='1.0',
    description='CSV to RDF converter',
    author='Olivier Rey',
    author_email='rey.olivier@gmail.com',
    url='https://github.com/orey/csv2rdf',
    packages=['csv2rdf'],
)

