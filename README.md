This is a toy example of our duplication tool. You just need to replace in the data folder the demo.txt file by your sentences of interest.

# 1 input Format

demo.txt
each sentence is separeted by a tabulation
"sentence1"\t"sentence2"

# build the hegp-dup-aligmnent image

run the script build.sh in order to construct an image which will contain the duplication sources.

# run the  hegp-dup-aligmnent image

run the script run.sh, it will output our sample text 
the offset is set to 3 and the fingerpint to 15

# How to run tests

1. Install package in editable mode with test and extra dependencies by running `pip install -e ".[tests, ncls, intervaltree]"` in the repo directory
2. Launch `pytest tests/`

# About ncls and intervaltree

This tool can be used without any additional dependencies, but performance can
be improved when using interval trees. To benefit from this you well need to
install either the [ncls](https://github.com/biocore-ntnu/ncls) package or the
[intervaltree](https://github.com/chaimleib/intervaltree) package.
