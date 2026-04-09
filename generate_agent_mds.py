#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from urllib.parse import quote

def escape_regex(pattern):
    """Escape special regex characters."""
    special_chars = r'.^$*+?{}[]|()\\'
    return ''.join(f'\\{c}' if c in special_chars else c for c in pattern)

def tool_name_from_filename(filename):
    """Convert snake_case filename to Title Case tool name."""
    name = filename.replace('.json', '').replace('_', ' ')
    return ' '.join(word.capitalize() for word in name.split())

def generate_github_search_urls(pattern, search_type):
    """Generate GitHub search URL for different pattern types."""
    if search_type == 'file':
        # Escape regex for file path search
        escaped = escape_regex(pattern)
        query = f'path:/(^|\\/)({escaped})($|/)'
        return f'https://github.com/search?q={quote(query)}&type=code'
    
    elif search_type == 'commit':
        # Author or co-author search
        query = f'Co-authored-by: "{pattern}"'
        return f'https://github.com/search?q={quote(query)}&type=commits'
    
    elif search_type == 'author':
        # Author search
        query = f'author: "{pattern}"'
        return f'https://github.com/search?q={quote(query)}&type=commits'
    
    elif search_type == 'branch':
        # Branch search
        query = f'head:{pattern} type:pr'
        return f'https://github.com/search?q={quote(query)}&type=issues'
    
    elif search_type == 'label':
        # Label search
        query = f'label:{pattern} type:pr'
        return f'https://github.com/search?q={quote(query)}&type=issues'

def extract_header(md_filepath):
    """Extract human-editable header from existing markdown (before the separator line)."""
    if not md_filepath.exists():
        return None
    
    with open(md_filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split at the first --- separator marker
    if "\n---\n" in content:
        header = content.split("\n---\n")[0].rstrip() + "\n\n"
        return header
    
    # Fallback: if no separator, split at ## Files
    if "## Files" in content:
        header = content.split("## Files")[0].rstrip() + "\n\n"
        return header
    
    # If neither marker exists, return None (file might be malformed)
    return None

def load_tools_urls():
    """Load tool URLs from tools.csv."""
    tools_urls = {}
    with open('patterns/tools.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tools_urls[row['tool']] = row['url']
    return tools_urls

def generate_markdown(json_filepath, output_dir, tools_urls):
    """Generate markdown from JSON file, preserving human-editable header if it exists."""
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        return None
    
    entry = data[0]  # Take first entry (should be only one)
    tool_name = tool_name_from_filename(json_filepath.name)
    
    # Check if we have an existing header to preserve
    md_filepath = Path(output_dir) / (json_filepath.stem + '.md')
    existing_header = extract_header(md_filepath)
    
    if existing_header:
        md_content = existing_header
    else:
        md_content = f"# {tool_name}\n\n"
        # Add tool website link if available
        url = tools_urls.get(tool_name)
        if url:
            md_content += f"[Tool Website]({url})\n\n"
    
    # Add separator before auto-generated content
    md_content += "---\n\n⚠️ **Note:** Everything below this line is auto-generated and will be overwritten when the generation script is run. Only edit content above this line.\n\n"
    
    # Files section
    files = entry.get('files', [])
    if files:
        md_content += "## Files\n\n"
        for pattern in files:
            url = generate_github_search_urls(pattern, 'file')
            md_content += f"- [{pattern}]({url})\n"
        md_content += "\n"
    
    # Commits section
    author_names = entry.get('author_names', [])
    author_mails = entry.get('author_mails', [])
    
    if author_names or author_mails:
        md_content += "## Commits\n\n"
        
        for name in author_names:
            commit_url = generate_github_search_urls(name, 'commit')
            author_url = generate_github_search_urls(name, 'author')
            md_content += f"- [{name}]({commit_url}), [auth]({author_url})\n"
        
        for mail in author_mails:
            commit_url = generate_github_search_urls(mail, 'commit')
            author_url = generate_github_search_urls(mail, 'author')
            md_content += f"- [{mail}]({commit_url}), [auth]({author_url})\n"
        
        md_content += "\n"
    
    # Branches section
    branches = entry.get('branch_name_prefix', [])
    md_content += "## Branches\n\n"
    if branches:
        for pattern in branches:
            url = generate_github_search_urls(pattern, 'branch')
            md_content += f"- [{pattern}]({url})\n"
    else:
        md_content += "No heuristic yet\n"
    md_content += "\n"
    
    # Commit message prefixes section
    commit_prefixes = entry.get('commit_message_prefix', [])
    md_content += "## Commit Prefixes\n\n"
    if commit_prefixes:
        for pattern in commit_prefixes:
            # For commit prefixes, just display the pattern (no special search URL needed)
            md_content += f"- {pattern}\n"
    else:
        md_content += "No heuristic yet\n"
    md_content += "\n"
    
    # Labels section (not populated yet)
    md_content += "## Labels\n\n"
    md_content += "No heuristic yet\n"
    
    return md_content

def generate_mds(json_dir, output_dir):
    """Generate markdown files for all JSON files in directory."""
    json_dir = Path(json_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load tool URLs
    tools_urls = load_tools_urls()
    
    json_files = sorted(json_dir.glob('*.json'))
    count = 0
    
    for json_filepath in json_files:
        try:
            md_content = generate_markdown(json_filepath, output_dir, tools_urls)
            if md_content:
                md_filename = json_filepath.stem + '.md'
                md_filepath = output_dir / md_filename
                
                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                print(f"✓ Generated {md_filename}")
                count += 1
        except Exception as e:
            print(f"✗ Error processing {json_filepath.name}: {e}", file=sys.stderr)
    
    print(f"\nTotal: {count} markdown files generated in {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_agent_mds.py <json_dir> <output_dir>")
        sys.exit(1)
    
    json_dir = sys.argv[1]
    output_dir = sys.argv[2]
    generate_mds(json_dir, output_dir)
