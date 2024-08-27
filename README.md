# upfront note
A little less than half of the code was written on my phone while traveling, the other half was scrapped together in less than a day. I used some really dirty tricks to get stuff done and the code is **obviously** not meant to be used in any sort of production environment. PURELY EDUCATIONAL.

# barg
**B**arni's P**ar**ser ~~**G**enerator~~ **G**rammar is a tiny python lib/app that can take a in grammar file in my weird meta-regex format and parse strings with it. it doesn't directly generate a python parser for it (yet).

# how to install
## install from pypi
you can install from PyPI like this: `pip install barg`.

## install from local clone of project
download the project. in the project root (directory where this file is located), run `python setup.py sdist && pip install -r requirements.txt && pip install .`. this will create some directories which you can safely delete.

# how to use
**CURRENTLY NOT IMPLEMENTED** ~~generate a python parser: `python -m barg codegen grammar.barg -o parser.py`~~

parse the file using some grammar: `python -m barg exec file.abc -g grammar.barg`

run unit tests: `python -m unittest barg.tests`.

if you are trying to run the source code directly without installing it, you will have to set PYTHONPATH=src. eg `PYTHONPATH=src python -m barg --help`
