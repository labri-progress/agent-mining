# Agent Mining

This repository is a community driven initiative to register coding agents information:

- their global workflow, described in a markdown file;
- the traces (files, branch names, co-authors,...) that can be used to detect agent use, those are described in a json file for automatic parsing and use, they are also present in the description markdown  with links to GitHUb urls to quickly see examples.
- a sample of repositories with commits, files or branches with agent use;
- scripts to quickly detect agent use using these heuristics and to sample elements using the GitHub REST API.

## Structure

- The [agents](agents) folder contains for each agent two files:

  - a markdown description with links to examples
  - a JSON file enabling easy parsing of the heuristics

- [heuristic.py](heuristics.py) which describes a heuristic as a python object and enables easy loading
- [github_query_helper.py](github_query_helper.py) which enables to sample elements matching a given heuristic using the GitHub REST API
- [projects_with_agent_traces.csv](projects_with_agent_traces.csv) is a CSV file containing a bit more than 10,000 projects that we have identified as using coding agents with our heuristics. The projects may use agents at the file level, the commit level (including pull requests), or be identified since their ``.gitignore'' file includes files from coding agents.

## Contributing

Contributions are welcome!
Please open a pull request and we will try to get back to you as soon as possible.

## Citing

Will be added at the end of the anonymous period
