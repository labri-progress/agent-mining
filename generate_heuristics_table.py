#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from urllib.parse import quote

def escape_for_regex(pattern):
    """Escape special regex characters and convert glob wildcards to regex.
    Handles * and ? wildcards from glob patterns."""
    # First escape regex special characters (but not * and ? yet)
    special_chars = '.^$+{}[]|()\\'
    escaped = ''.join(f'\\{c}' if c in special_chars else c for c in pattern)
    # Then convert glob wildcards to regex
    escaped = escaped.replace('*', '.*').replace('?', '.')
    # Finally escape forward slashes
    escaped = escaped.replace('/', '\\/')
    return escaped

def tool_name_from_filename(filename):
    """Convert snake_case filename to Title Case tool name."""
    name = filename.replace('.json', '').replace('_', ' ')
    return ' '.join(word.capitalize() for word in name.split())

def slugify(name):
    """Convert tool name to snake_case filename."""
    return name.lower().replace(" ", "_").replace("-", "_")

def generate_github_search_urls(pattern, search_type):
    """Generate GitHub search URL for different pattern types."""
    if search_type == 'file':
        escaped = escape_for_regex(pattern)
        # For directories (ending with /), don't use end anchor
        if pattern.endswith('/'):
            query = f'path:/(?:^|\\/)({escaped})/'
        else:
            # For files, use end anchor to match only at end of path
            query = f'path:/(?:^|\\/)({escaped})$/'
        return f'https://github.com/search?q={quote(query)}&type=code'
    
    elif search_type == 'commit':
        query = f'Co-authored-by:"{pattern}"'
        return f'https://github.com/search?q={quote(query)}&type=commits'
    
    elif search_type == 'author':
        query = f'author:"{pattern}"'
        return f'https://github.com/search?q={quote(query)}&type=commits'
    
    elif search_type == 'branch':
        query = f'head:{pattern} type:pr'
        return f'https://github.com/search?q={quote(query)}&type=pullrequests'
    
    elif search_type == 'label':
        query = f'label:{pattern} type:pr'
        return f'https://github.com/search?q={quote(query)}&type=pullrequests'

def format_cell(patterns, search_type):
    """Format a cell with patterns and links."""
    if not patterns:
        return "-"
    
    links = []
    for pattern in patterns:
        url = generate_github_search_urls(pattern, search_type)
        links.append(f"[{pattern}]({url})")
    
    return ", ".join(links)

def generate_heuristics_table(json_dir, output_file, md_dir="tools"):
    """Generate heuristics markdown table."""
    json_dir = Path(json_dir)
    output_file = Path(output_file)
    
    # Read all JSON files
    json_files = sorted(json_dir.glob('*.json'))
    
    # Build table rows
    rows = []
    for json_filepath in json_files:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            continue
        
        entry = data[0]
        tool_name = tool_name_from_filename(json_filepath.name)
        slug = slugify(tool_name)
        
        # Tool name with link
        tool_cell = f"[{tool_name}]({md_dir}/{slug}.md)"
        
        # File patterns
        files = entry.get('files', [])
        file_cell = format_cell(files, 'file')
        
        # Author patterns (names and mails)
        author_names = entry.get('author_names', [])
        author_mails = entry.get('author_mails', [])
        all_authors = author_names + author_mails
        
        # For commit cell, we need both co-author and author links
        commit_links = []
        for name in author_names:
            co_url = generate_github_search_urls(name, 'commit')
            auth_url = generate_github_search_urls(name, 'author')
            commit_links.append(f"[{name}]({co_url}), [auth]({auth_url})")
        
        for mail in author_mails:
            co_url = generate_github_search_urls(mail, 'commit')
            auth_url = generate_github_search_urls(mail, 'author')
            commit_links.append(f"[{mail}]({co_url}), [auth]({auth_url})")
        
        commit_cell = ", ".join(commit_links) if commit_links else "-"
        
        # Branch patterns
        branches = entry.get('branch_name_prefix', [])
        branch_cell = format_cell(branches, 'branch')
        
        # Labels
        labels = entry.get('labels', [])
        label_cell = format_cell(labels, 'label')
        
        # Add row
        row = f"| {tool_cell} | {file_cell} | {commit_cell} | {branch_cell} | {label_cell} |"
        rows.append(row)
    
    # Write markdown file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("| Tool | File | Commit | Branches | Labels |\n")
        f.write("|------|------|--------|----------|--------|\n")
        for row in rows:
            f.write(row + "\n")
        
        # Add note at the bottom
        f.write("\n---\n\n")
        f.write("⚠️ **Auto-Generated**: This table is generated automatically. Be aware that some search patterns may not be fully supported by GitHub's interface:\n")
        f.write("- `label:` queries do not support regex syntax (use literal strings only)\n")
        f.write("- `path:` queries require specific regex syntax with non-capturing groups\n")
        f.write("- Result counts returned by GitHub are approximate\n")
    
    print(f"✓ Generated heuristics table: {output_file}")
    print(f"  Total tools: {len(rows)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_heuristics_table.py <json_dir> [output_file] [md_dir]")
        print("  json_dir:    directory with tool JSON files")
        print("  output_file: output markdown file (default: heuristics.md)")
        print("  md_dir:      directory path for tool md links (default: tools)")
        sys.exit(1)
    
    json_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "heuristics.md"
    md_dir = sys.argv[3] if len(sys.argv) > 3 else "tools"
    
    generate_heuristics_table(json_dir, output_file, md_dir)
