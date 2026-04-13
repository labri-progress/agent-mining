# Agent Mining

This repository is a community driven initiative to register coding agents information:

- traces (files, branch names, labels, co-authors,...) that can be used to detect agent use;
- heuristics stored as JSON for automatic parsing and use;
- markdown documentation with links to GitHub examples;
- a sample of (~ 10,000) repositories with commits, files or branches with agent use;
- scripts to quickly detect agent use using these heuristics and to sample elements using the GitHub REST API.

For a more complete example of how these heuristics can be used, refer to the [code from the Agent adoption study](https://github.com/labri-progress/agent-impact/). 

## Workflow

Heuristics are maintained as CSV files in the [patterns](patterns) directory:
- [authors.csv](patterns/authors.csv) - Author names and emails
- [files.csv](patterns/files.csv) - File patterns and directory structures
- [branches.csv](patterns/branches.csv) - Branch name patterns
- [labels.csv](patterns/labels.csv) - GitHub issue/PR labels
- [commit_prefixes.csv](patterns/commit_prefixes.csv) - Commit message prefixes

These CSV files are then automatically converted to:
- JSON files in [heuristics-json](heuristics-json) for programmatic use
- Markdown files in [agents](agents) with human-readable descriptions and GitHub search links
- A consolidated table in [heuristics.md](heuristics.md)

**Note:** The markdown files in the [agents](agents) folder can be manually edited above the `---` separator line to add custom descriptions and links. The content below the separator is auto-generated and will be overwritten when regenerating.

Run `bash generate_all.sh heuristics-json agents` to regenerate all outputs from the CSV sources.

## Structure

- The [agents](agents) folder contains markdown documentation for each agent with links to examples
- The [heuristics-json](heuristics-json) folder contains JSON files for each agent enabling easy parsing of the heuristics
- [heuristic.py](heuristic.py) describes a heuristic as a python object and enables easy loading
- [github_query_helper.py](github_query_helper.py) enables sampling elements matching a given heuristic using the GitHub REST API
- [projects_with_agent_traces.csv](projects_with_agent_traces.csv) is a CSV file containing a bit more than 10,000 projects that we have identified as using coding agents with our heuristics. The projects may use agents at the file level, the commit level (including pull requests), or be identified since their ``.gitignore'' file includes files from coding agents.

## Contributing

Contributions are welcome!
Please open a pull request and we will try to get back to you as soon as possible.

## Citing

You can cite our MSR 2026 paper: "Promises, Perils, and (Timely) Heuristics for Mining Coding Agent Activity" ([Preprint](https://arxiv.org/abs/2601.18345)). The Agent adoption study is the paper "Agentic Much? Adoption of Coding Agents on GitHub" ([Preprint](https://arxiv.org/abs/2601.18341)).
 
