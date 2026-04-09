#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

def slugify(name):
    """Convert tool name to snake_case filename."""
    return name.lower().replace(" ", "_").replace("-", "_")

def is_email(pattern):
    """Simple heuristic: email if contains @."""
    return "@" in pattern

def read_csv(filepath):
    """Read CSV and return list of dicts."""
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def generate_jsons(output_dir):
    """Generate JSON files for all tools."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect all data by tool
    tools_data = defaultdict(lambda: {
        'author_names': [],
        'author_mails': [],
        'files': [],
        'branch_name_prefix': [],
        'commit_message_prefix': [],
    })
    
    # Read all CSVs
    authors = read_csv('patterns/authors.csv')
    files = read_csv('patterns/files.csv')
    branches = read_csv('patterns/branches.csv')
    labels = read_csv('patterns/labels.csv')
    commit_prefixes = read_csv('patterns/commit_prefixes.csv')
    
    # Process authors
    for row in authors:
        tool = row['tool']
        pattern = row['pattern']
        if is_email(pattern):
            tools_data[tool]['author_mails'].append(pattern)
        else:
            tools_data[tool]['author_names'].append(pattern)
    
    # Process files
    for row in files:
        tool = row['tool']
        pattern = row['pattern']
        tools_data[tool]['files'].append(pattern)
    
    # Process branches
    for row in branches:
        tool = row['tool']
        pattern = row['pattern']
        tools_data[tool]['branch_name_prefix'].append(pattern)
    
    # Process labels (treat as branch_name_prefix for generic detection)
    for row in labels:
        tool = row['tool']
        pattern = row['pattern']
        tools_data[tool]['branch_name_prefix'].append(pattern)
    
    # Process commit prefixes
    for row in commit_prefixes:
        tool = row['tool']
        pattern = row['pattern']
        tools_data[tool]['commit_message_prefix'].append(pattern)
    
    # Generate JSON files
    count = 0
    for tool, data in sorted(tools_data.items()):
        filename = f"{slugify(tool)}.json"
        filepath = output_dir / filename
        
        # Build JSON structure
        json_data = [{
            'author_names': data['author_names'],
            'author_mails': data['author_mails'],
            'files': data['files'],
            'branch_name_prefix': data['branch_name_prefix'],
            'commit_message_prefix': data['commit_message_prefix'],
            'period_start': '',
            'period_end': None
        }]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ Generated {filename}")
        count += 1
    
    print(f"\nTotal: {count} agent JSON files generated in {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_agent_jsons.py <output_dir>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    generate_jsons(output_dir)
