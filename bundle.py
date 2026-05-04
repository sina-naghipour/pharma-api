#!/usr/bin/env python3
"""
Bundle React/FastAPI Application
Creates a complete code bundle of a React or FastAPI application
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import re

def should_skip_react(path: Path) -> bool:
    """Check if file/directory should be skipped for React/FastAPI projects"""
    skip_patterns = [
        # Python/Backend patterns
        '__pycache__', '.venv', 'venv', 'env', 
        '*.pyc', '*.pyo', '*.pyd', '*.so', '.egg-info',
        'alembic/versions', 'migrations',
        
        # React/Node patterns
        'node_modules', 'build', 'dist', '.next', 'out',
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*',
        
        # Git and IDE
        '.git', '.idea', '.vscode', '.DS_Store',
        
        # Testing
        '.pytest_cache', '.coverage', 'htmlcov', '.tox', '.mypy_cache',
        'coverage', '.nyc_output', 'jest-coverage',
        
        # Environment and temp
        '.env.local', '.env.development.local', '.env.test.local', '.env.production.local',
        'temp', 'tmp', 'bundle_', 'backup*',
        
        # Static assets (binary files)
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.ico', '*.svg',
        '*.woff', '*.woff2', '*.ttf', '*.eot', '*.mp4', '*.mp3', '*.wav',
        
        # Logs and databases
        '*.log', '*.sqlite', '*.db',
        
        # Config files (usually sensitive or generated)
        '.env', '*.env',  # Skip env files for security
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        
        # Build artifacts
        '*.map', '*.min.js', '*.min.css',
        
        # Bundle output files
        'fastapi_bundle.txt', 'react_bundle.txt', 'bundle.py',
        
        # Documentation (optional - remove if you want to include)
        '*.md', 'README.md',
        
        # React specific
        'public', 'static/media', 'static/fonts',
        'service-worker.js', 'sw.js', 'manifest.json',
        
        # Config files (remove if you want to include)
        'webpack.config.js', 'vite.config.js', 'next.config.js',
        'tailwind.config.js', 'postcss.config.js',
    ]
    
    path_str = str(path)
    path_lower = path_str.lower()
    
    # Skip hidden files (except .env files which we already skip)
    if any(part.startswith('.') for part in path.parts):
        if path.name != '.' and path.name != '..':
            if not path.name.startswith('.env') and not path.name == '.gitignore':
                return True
    
    for pattern in skip_patterns:
        if pattern.startswith('*'):
            if path_str.endswith(pattern[1:]) or path_lower.endswith(pattern[1:].lower()):
                return True
        elif pattern in path_str or pattern.lower() in path_lower:
            return True
    
    return False

def get_file_extension_priority(file_path: Path) -> int:
    """Get priority for file ordering in bundle"""
    ext_priority = {
        '.py': 1,           # Python files first
        '.js': 2,           # JavaScript files
        '.jsx': 2,          # React JSX files
        '.ts': 2,           # TypeScript files
        '.tsx': 2,          # React TSX files
        '.css': 3,          # CSS files
        '.scss': 3,         # SCSS files
        '.txt': 4,          # Text files
        '.json': 5,         # Config files
        '.yml': 5,          # YAML files
        '.yaml': 5,
        '.ini': 5,
        '.toml': 5,
        '.cfg': 5,
        '.html': 6,         # HTML files
        '.sh': 7,           # Shell scripts
        '.sql': 8,          # SQL files
    }
    
    # Check for exact match first
    if file_path.name.lower() in ext_priority:
        return ext_priority[file_path.name.lower()]
    
    # Check extension
    ext = file_path.suffix.lower()
    return ext_priority.get(ext, 99)

def read_file_content(file_path: Path) -> str:
    """Read file content with proper encoding"""
    try:
        # Try UTF-8 first
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # Try Latin-1 as fallback
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except:
            # For binary files
            file_size = file_path.stat().st_size
            return f"[BINARY FILE - {file_size:,} bytes]"
    except Exception as e:
        return f"[ERROR READING FILE: {str(e)}]"

def extract_react_info(content: str) -> dict:
    """Extract React specific information from file content"""
    info = {
        'components': [],
        'hooks': [],
        'routes': [],
        'api_calls': []
    }
    
    # Look for React component definitions
    component_patterns = [
        r'function\s+(\w+)\s*\([^)]*\)\s*\{',
        r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{',
        r'class\s+(\w+)\s+extends\s+(?:React\.)?Component',
        r'export\s+default\s+function\s+(\w+)',
        r'export\s+default\s+(\w+)',
    ]
    
    for pattern in component_patterns:
        for match in re.finditer(pattern, content):
            info['components'].append(match.group(1))
    
    # Look for React hooks
    hook_patterns = [
        r'useState\(', r'useEffect\(', r'useContext\(', r'useReducer\(',
        r'useCallback\(', r'useMemo\(', r'useRef\(', r'useImperativeHandle\(',
        r'useLayoutEffect\(', r'useDebugValue\(', r'useDeferredValue\(',
        r'useTransition\(', r'useId\(', r'useSyncExternalStore\(',
    ]
    
    content_lower = content.lower()
    for hook in hook_patterns:
        if hook.lower() in content_lower:
            info['hooks'].append(hook.replace('(', ''))
    
    # Look for React Router routes
    route_patterns = [
        r'<Route\s+path=["\']([^"\']+)["\']',
        r'path:\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in route_patterns:
        for match in re.finditer(pattern, content):
            info['routes'].append(match.group(1))
    
    # Look for API calls (fetch, axios)
    api_patterns = [
        r'fetch\s*\(\s*["\']([^"\']+)["\']',
        r'axios\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        r'\.get\s*\(\s*["\']([^"\']+)["\']',
        r'\.post\s*\(\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in api_patterns:
        for match in re.finditer(pattern, content):
            url = match.group(1) if len(match.groups()) == 1 else match.group(2)
            if url and url.startswith(('/', 'http')):
                info['api_calls'].append(url)
    
    # Remove duplicates by converting to set and back
    info['components'] = list(set(info['components']))
    info['routes'] = list(set(info['routes']))
    info['api_calls'] = list(set(info['api_calls']))
    info['hooks'] = list(set(info['hooks']))
    
    return info

def bundle_react_app(output_file: str = "react_bundle.txt", include_docs: bool = True) -> Path:
    """
    Bundle a React application into a single text file
    """
    current_dir = Path.cwd()
    output_path = current_dir / output_file
    
    print(f"🚀 Bundling React Application")
    print(f"📁 Directory: {current_dir}")
    print(f"📄 Output: {output_path}")
    print("-" * 60)
    
    # Check if this looks like a React project
    react_files = ['package.json', 'src']
    has_react = any((current_dir / f).exists() for f in react_files)
    
    if not has_react:
        print("⚠️  Warning: This doesn't look like a React project")
        print("   No package.json or src directory found in root")
    
    file_count = 0
    skipped_files = []
    total_size = 0
    
    # Collect project info
    project_info = {
        'name': current_dir.name,
        'total_files': 0,
        'components': [],
        'hooks': [],
        'routes': [],
        'api_calls': []
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as bundle:
            # Write header
            bundle.write("=" * 80 + "\n")
            bundle.write("REACT APPLICATION BUNDLE\n")
            bundle.write("=" * 80 + "\n")
            bundle.write(f"Project: {current_dir.name}\n")
            bundle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            bundle.write(f"Directory: {current_dir}\n")
            bundle.write("=" * 80 + "\n\n")
            
            # Project structure section
            if include_docs:
                bundle.write("📁 PROJECT STRUCTURE\n")
                bundle.write("-" * 80 + "\n")
            
            # Collect all files with their relative paths
            all_files = []
            for root, dirs, files in os.walk(current_dir):
                root_path = Path(root)
                
                # Filter out directories to skip
                dirs[:] = [d for d in dirs if not should_skip_react(root_path / d)]
                
                for file in files:
                    file_path = root_path / file
                    if not should_skip_react(file_path):
                        # Skip the output file itself
                        if file_path == output_path:
                            continue
                        
                        all_files.append(file_path)
            
            # Sort files by priority and then alphabetically
            all_files.sort(key=lambda x: (get_file_extension_priority(x), str(x)))
            
            # Process each file
            for file_path in all_files:
                try:
                    relative_path = file_path.relative_to(current_dir)
                    
                    # Calculate indentation for structure display
                    depth = len(relative_path.parents)
                    indent = "  " * depth
                    
                    # Write structure info
                    if include_docs:
                        if file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                            bundle.write(f"{indent}📄 {relative_path}\n")
                        elif file_path.suffix in ['.css', '.scss', '.sass']:
                            bundle.write(f"{indent}🎨 {relative_path}\n")
                        elif file_path.name == 'package.json':
                            bundle.write(f"{indent}📦 {relative_path}\n")
                        elif file_path.suffix in ['.yml', '.yaml', '.json']:
                            bundle.write(f"{indent}⚙️  {relative_path}\n")
                        elif file_path.suffix == '.html':
                            bundle.write(f"{indent}🌐 {relative_path}\n")
                        else:
                            bundle.write(f"{indent}📄 {relative_path}\n")
                    
                    # Write file separator
                    bundle.write("\n" + "=" * 80 + "\n")
                    bundle.write(f"FILE: {relative_path}\n")
                    
                    try:
                        file_size = file_path.stat().st_size
                        bundle.write(f"SIZE: {file_size:,} bytes\n")
                        total_size += file_size
                        
                        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        bundle.write(f"MODIFIED: {modified_time}\n")
                    except:
                        bundle.write("SIZE: Unknown\n")
                    
                    bundle.write("=" * 80 + "\n\n")
                    
                    # Read and write file content
                    content = read_file_content(file_path)
                    bundle.write(content)
                    
                    # Extract React info from JS/TS files
                    if file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                        file_info = extract_react_info(content)
                        project_info['components'].extend(file_info['components'])
                        project_info['hooks'].extend(file_info['hooks'])
                        project_info['routes'].extend(file_info['routes'])
                        project_info['api_calls'].extend(file_info['api_calls'])
                    
                    if content and not content.endswith('\n'):
                        bundle.write('\n')
                    
                    file_count += 1
                    
                except Exception as e:
                    error_msg = f"[ERROR PROCESSING FILE: {str(e)}]"
                    bundle.write(f"\n{error_msg}\n")
                    skipped_files.append((file_path, str(e)))
            
            # Write project summary
            bundle.write("\n" + "=" * 80 + "\n")
            bundle.write("📊 PROJECT SUMMARY\n")
            bundle.write("=" * 80 + "\n")
            bundle.write(f"Total files bundled: {file_count}\n")
            bundle.write(f"Total size: {total_size:,} bytes\n")
            
            if project_info['components']:
                bundle.write(f"\n⚛️  REACT COMPONENTS ({len(set(project_info['components']))}):\n")
                for component in sorted(set(project_info['components']))[:20]:
                    bundle.write(f"  • {component}\n")
                if len(set(project_info['components'])) > 20:
                    bundle.write(f"  ... and {len(set(project_info['components'])) - 20} more\n")
            
            if project_info['hooks']:
                bundle.write(f"\n🪝 REACT HOOKS USED:\n")
                for hook in sorted(set(project_info['hooks'])):
                    bundle.write(f"  • {hook}\n")
            
            if project_info['routes']:
                bundle.write(f"\n🧭 ROUTES ({len(set(project_info['routes']))}):\n")
                for route in sorted(set(project_info['routes']))[:15]:
                    bundle.write(f"  • {route}\n")
            
            if project_info['api_calls']:
                bundle.write(f"\n🌐 API ENDPOINTS ({len(set(project_info['api_calls']))}):\n")
                for api in sorted(set(project_info['api_calls']))[:15]:
                    bundle.write(f"  • {api}\n")
            
            bundle.write(f"\n📁 Directory structure:\n")
            for file_path in all_files[:20]:  # Show first 20 files in structure
                relative_path = file_path.relative_to(current_dir)
                depth = len(relative_path.parents)
                indent = "  " * depth
                bundle.write(f"{indent}{relative_path.name}\n")
            
            if len(all_files) > 20:
                bundle.write(f"  ... and {len(all_files) - 20} more files\n")
            
            bundle.write(f"\n🕒 Bundle created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            if skipped_files:
                bundle.write(f"\n⚠️  Skipped {len(skipped_files)} files:\n")
                for file_path, reason in skipped_files[:10]:
                    bundle.write(f"  • {file_path.name}: {reason}\n")
                if len(skipped_files) > 10:
                    bundle.write(f"  ... and {len(skipped_files) - 10} more\n")
            
            bundle.write("=" * 80 + "\n")
    
    except Exception as e:
        print(f"❌ Error creating bundle: {e}")
        sys.exit(1)
    
    # Print summary to console
    print(f"\n✅ Successfully bundled {file_count} files")
    print(f"📏 Total size: {total_size:,} bytes")
    print(f"⚛️  Components found: {len(set(project_info['components']))}")
    print(f"🌐 API calls found: {len(set(project_info['api_calls']))}")
    
    if skipped_files:
        print(f"⚠️  Skipped {len(skipped_files)} files")
    
    print(f"\n📄 Bundle saved to: {output_path}")
    
    return output_path

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bundle a React/FastAPI application into a single text file'
    )
    parser.add_argument(
        '-o', '--output',
        default='react_bundle.txt',
        help='Output filename (default: react_bundle.txt)'
    )
    parser.add_argument(
        '--include-docs',
        action='store_true',
        help='Include documentation and structure info (default: True)'
    )
    parser.add_argument(
        '--minimal',
        action='store_true',
        help='Minimal output (only code, no file headers)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("React/FastAPI Application Bundle Generator")
    print("=" * 60)
    
    result = bundle_react_app(
        output_file=args.output,
        include_docs=not args.minimal
    )
    
    print("\n🎉 Bundle created successfully!")
    print(f"📁 Open with: cat {args.output}")
    print(f"📋 Or copy with: cat {args.output} | clip (Windows) | pbcopy (Mac)")

if __name__ == "__main__":
    main()