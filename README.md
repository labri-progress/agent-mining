# Agent Mining

This repository is a community driven initiative to register coding agents information:

- their global workflow, described in a markdown file;
- the traces (files, branch names, co-authors,...) that can be used to detect agent use, those are described in a json file for automatic parsing and use, they are also present in the description markdown  with links to GitHUb urls to quickly see examples.
- a sample of repositories with commits, files and branches with agent use;
- scripts to quickly detect agent use using these heuristics and to sample elements using the GitHub REST API.

## Structure

- The [agents](agents) folder contains for each agent two files:

  - a markdown description with links to examples
  - a JSON file enabling easy parsing of the heuristics

- ``heuristic.py`` which describes a heuristic as a python object and enables easy loading
- ``github_query_helper.py`` which enables to sample elements matching a given heuristic using the GitHub REST API

## Contributing

Contributions are welcome!
Please open a pull request and we will try to get back to you as soon as possible.

## Citing

TODO
