#!/usr/bin/env python3
"""
Documentation Consolidation Analysis
Analyzes docs/ folder to identify:
- Duplicate or near-duplicate content
- Outdated version-specific docs
- Files that can be merged
- Organizational improvements
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re

def get_file_hash(filepath):
    """Get hash of file content."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def analyze_docs_structure(docs_dir):
    """Analyze documentation structure."""
    
    stats = {
        'total_files': 0,
        'total_size': 0,
        'by_directory': defaultdict(lambda: {'count': 0, 'size': 0}),
        'by_extension': defaultdict(lambda: {'count': 0, 'size': 0}),
        'duplicates': defaultdict(list),
        'version_docs': [],
        'old_daily_logs': [],
        'large_files': [],
    }
    
    hash_map = {}
    
    # Walk through all files
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            filepath = Path(root) / file
            relative_path = filepath.relative_to(docs_dir)
            
            try:
                size = filepath.stat().st_size
                stats['total_files'] += 1
                stats['total_size'] += size
                
                # By directory
                dir_key = str(relative_path.parent)
                stats['by_directory'][dir_key]['count'] += 1
                stats['by_directory'][dir_key]['size'] += size
                
                # By extension
                ext = filepath.suffix or 'no_extension'
                stats['by_extension'][ext]['count'] += 1
                stats['by_extension'][ext]['size'] += size
                
                # Check for duplicates
                file_hash = get_file_hash(filepath)
                if file_hash:
                    if file_hash in hash_map:
                        stats['duplicates'][file_hash].append(str(relative_path))
                    else:
                        hash_map[file_hash] = [str(relative_path)]
                        stats['duplicates'][file_hash] = [str(relative_path)]
                
                # Identify version-specific docs
                if re.search(r'v?\d+\.\d+\.\d+', str(relative_path)):
                    stats['version_docs'].append(str(relative_path))
                
                # Identify old daily logs
                if 'daily-logs' in str(relative_path) or 'daily_logs' in str(relative_path):
                    stats['old_daily_logs'].append(str(relative_path))
                
                # Large files (> 100KB)
                if size > 100000:
                    stats['large_files'].append((str(relative_path), size))
                    
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    # Filter duplicates to only show actual duplicates
    stats['duplicates'] = {k: v for k, v in stats['duplicates'].items() if len(v) > 1}
    
    return stats

def find_similar_topics(docs_dir):
    """Find docs with similar topics/titles that could be merged."""
    
    similar_groups = defaultdict(list)
    
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if not file.endswith('.md'):
                continue
                
            filepath = Path(root) / file
            relative_path = filepath.relative_to(docs_dir)
            
            # Extract topic from filename
            name = file.replace('.md', '').lower()
            # Remove version numbers
            name = re.sub(r'v?\d+\.\d+\.\d+', '', name)
            # Remove dates
            name = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', '', name)
            # Clean up
            name = re.sub(r'[_-]+', ' ', name).strip()
            
            if name:
                similar_groups[name].append(str(relative_path))
    
    # Only keep groups with multiple files
    similar_groups = {k: v for k, v in similar_groups.items() if len(v) > 1}
    
    return similar_groups

def generate_consolidation_report(docs_dir):
    """Generate comprehensive consolidation report."""
    
    print("=" * 80)
    print("DOCUMENTATION CONSOLIDATION ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing: {docs_dir}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    stats = analyze_docs_structure(docs_dir)
    
    # Overall stats
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size'] / 1024 / 1024:.2f} MB")
    
    # By extension
    print("\n" + "-" * 80)
    print("FILES BY EXTENSION")
    print("-" * 80)
    for ext, data in sorted(stats['by_extension'].items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"{ext:20s} {data['count']:5d} files  {data['size'] / 1024:8.2f} KB")
    
    # Top directories
    print("\n" + "-" * 80)
    print("TOP 20 DIRECTORIES BY FILE COUNT")
    print("-" * 80)
    for dir_path, data in sorted(stats['by_directory'].items(), key=lambda x: x[1]['count'], reverse=True)[:20]:
        print(f"{data['count']:4d} files  {data['size'] / 1024:8.2f} KB  {dir_path}")
    
    # Duplicates
    print("\n" + "-" * 80)
    print(f"DUPLICATE FILES: {len(stats['duplicates'])} groups")
    print("-" * 80)
    if stats['duplicates']:
        for i, (hash_val, files) in enumerate(list(stats['duplicates'].items())[:10], 1):
            print(f"\nGroup {i}:")
            for f in files:
                print(f"  - {f}")
    
    # Version docs
    print("\n" + "-" * 80)
    print(f"VERSION-SPECIFIC DOCS: {len(stats['version_docs'])} files")
    print("-" * 80)
    if stats['version_docs']:
        print("Sample (first 10):")
        for f in stats['version_docs'][:10]:
            print(f"  - {f}")
    
    # Daily logs
    print("\n" + "-" * 80)
    print(f"DAILY LOGS: {len(stats['old_daily_logs'])} files")
    print("-" * 80)
    if stats['old_daily_logs']:
        print("Sample (first 10):")
        for f in stats['old_daily_logs'][:10]:
            print(f"  - {f}")
    
    # Large files
    print("\n" + "-" * 80)
    print(f"LARGE FILES (>100KB): {len(stats['large_files'])}")
    print("-" * 80)
    for filepath, size in sorted(stats['large_files'], key=lambda x: x[1], reverse=True)[:10]:
        print(f"{size / 1024:8.2f} KB  {filepath}")
    
    # Similar topics
    print("\n" + "-" * 80)
    print("POTENTIAL MERGES (Similar Topics)")
    print("-" * 80)
    similar = find_similar_topics(docs_dir)
    if similar:
        for topic, files in sorted(similar.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"\nTopic: '{topic}' ({len(files)} files)")
            for f in files[:5]:
                print(f"  - {f}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("CONSOLIDATION RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n1. ARCHIVE OLD VERSIONS")
    print(f"   - {len(stats['version_docs'])} version-specific docs can be compressed/archived")
    print(f"   - Versions before 2.6.0 are likely safe to archive")
    
    print("\n2. CONSOLIDATE DAILY LOGS")
    print(f"   - {len(stats['old_daily_logs'])} daily log files")
    print(f"   - Consider monthly summaries instead of daily files")
    
    print("\n3. REMOVE DUPLICATES")
    print(f"   - {len(stats['duplicates'])} duplicate file groups found")
    print(f"   - Keep one copy, delete others")
    
    print("\n4. MERGE SIMILAR TOPICS")
    print(f"   - {len(similar)} topic groups with multiple files")
    print(f"   - Consolidate into single comprehensive docs")
    
    print("\n5. COMPRESS LARGE FILES")
    print(f"   - {len(stats['large_files'])} files over 100KB")
    print(f"   - Consider splitting or summarizing")
    
    print("\n" + "=" * 80)
    print("END OF REPORT")
    print("=" * 80)
    
    return stats, similar

if __name__ == "__main__":
    docs_dir = Path(__file__).parent.parent / "docs"
    stats, similar = generate_consolidation_report(docs_dir)
