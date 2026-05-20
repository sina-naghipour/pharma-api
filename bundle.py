#!/usr/bin/env python3
"""
Bundle Django Application
Creates a complete code bundle of a Django application
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import re

def should_skip_django(path: Path) -> bool:
    """Check if file/directory should be skipped for Django projects"""
    skip_patterns = [
        # Python/Backend patterns
        '__pycache__', '.venv', 'venv', 'env', 
        '*.pyc', '*.pyo', '*.pyd', '*.so', '.egg-info',
        'migrations',  # Django migration files (can be excluded)
        'alembic/versions',  # For any SQLAlchemy
        'static',
        'db.sqlite3',
        # Django static/media
        'staticfiles', 'media', 'static/collected',
        'static/uploads', 'media/uploads',
        
        # Node modules if frontend inside Django
        'node_modules', 'package-lock.json', 'yarn.lock',
        
        # Git and IDE
        '.git', '.idea', '.vscode', '.DS_Store',
        
        # Testing & coverage
        '.pytest_cache', '.coverage', 'htmlcov', '.tox', '.mypy_cache',
        'coverage', '.nyc_output',
        
        # Environment and temp
        '.env', '*.env',  # Skip env files for security
        '.env.local', '.env.development', '.env.production',
        'temp', 'tmp', 'bundle_', 'backup*',
        
        # Static assets (binary files)
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.ico', '*.svg',
        '*.woff', '*.woff2', '*.ttf', '*.eot', '*.mp4', '*.mp3', '*.wav',
        
        # Logs and databases
        '*.log', '*.sqlite', '*.db',
        
        # Config files (usually sensitive)
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        
        # Build artifacts
        '*.map', '*.min.js', '*.min.css',
        
        # Bundle output files
        'django_bundle.txt', 'bundle.py',
        
        # Documentation (optional - remove if you want to include)
        '*.md', 'README.md',
        
        # Django specific - sometimes excluded
        'static/admin', 'static/rest_framework',
    ]
    
    path_str = str(path)
    path_lower = path_str.lower()
    
    # Skip hidden files (except .gitignore which is useful)
    if any(part.startswith('.') for part in path.parts):
        if path.name != '.' and path.name != '..':
            if not path.name == '.gitignore':
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
        '.html': 2,         # Django templates
        '.css': 3,          # CSS files
        '.js': 4,           # JavaScript files
        '.txt': 5,          # Text files
        '.json': 6,         # Config files
        '.yml': 6,
        '.yaml': 6,
        '.ini': 6,
        '.toml': 6,
        '.cfg': 6,
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
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except:
            file_size = file_path.stat().st_size
            return f"[BINARY FILE - {file_size:,} bytes]"
    except Exception as e:
        return f"[ERROR READING FILE: {str(e)}]"

def extract_django_info(content: str) -> dict:
    """Extract Django specific information from file content"""
    info = {
        'apps': [],
        'models': [],
        'views': [],
        'urls': [],
        'forms': [],
        'serializers': [],
        'admin_classes': [],
        'commands': [],
    }
    
    # Look for Django app definitions (apps.py)
    app_config_pattern = r'class\s+(\w+Config)\s*\(\s*AppConfig\s*\)'
    for match in re.finditer(app_config_pattern, content):
        info['apps'].append(match.group(1).replace('Config', ''))
    
    # Look for model classes (models.py)
    model_pattern = r'class\s+(\w+)\s*\(\s*models\.Model\s*\)'
    for match in re.finditer(model_pattern, content):
        info['models'].append(match.group(1))
    
    # Look for view functions/classes (views.py)
    view_func_pattern = r'def\s+(\w+)\s*\(\s*request\s*,'
    view_class_pattern = r'class\s+(\w+)\s*\(\s*(?:View|TemplateView|ListView|DetailView|CreateView|UpdateView|DeleteView|FormView)\s*\)'
    for match in re.finditer(view_func_pattern, content):
        info['views'].append(match.group(1))
    for match in re.finditer(view_class_pattern, content):
        info['views'].append(match.group(1))
    
    # Look for URL patterns (urls.py)
    url_patterns = [
        r'path\s*\(\s*["\']([^"\']+)["\']',
        r're_path\s*\(\s*["\']([^"\']+)["\']',
        r'url\s*\(\s*["\']([^"\']+)["\']',
    ]
    for pattern in url_patterns:
        for match in re.finditer(pattern, content):
            info['urls'].append(match.group(1))
    
    # Look for form classes (forms.py)
    form_pattern = r'class\s+(\w+)\s*\(\s*forms\.(?:ModelForm|Form)\s*\)'
    for match in re.finditer(form_pattern, content):
        info['forms'].append(match.group(1))
    
    # Look for DRF serializers (serializers.py)
    serializer_pattern = r'class\s+(\w+)\s*\(\s*serializers\.(?:ModelSerializer|Serializer)\s*\)'
    for match in re.finditer(serializer_pattern, content):
        info['serializers'].append(match.group(1))
    
    # Look for admin classes (admin.py)
    admin_pattern = r'class\s+(\w+)\s*\(\s*admin\.(?:ModelAdmin|StackedInline|TabularInline)\s*\)'
    for match in re.finditer(admin_pattern, content):
        info['admin_classes'].append(match.group(1))
    
    # Look for custom management commands (management/commands/*.py)
    command_pattern = r'class\s+Command\s*\(\s*BaseCommand\s*\)'
    if re.search(command_pattern, content):
        # Extract command name from file name logic will be handled in main loop
        info['commands'].append('found')
    
    # Remove duplicates
    for key in info:
        info[key] = list(set(info[key]))
    
    return info

def bundle_django_app(output_file: str = "django_bundle.txt", include_docs: bool = True) -> Path:
    """
    Bundle a Django application into a single text file
    """
    current_dir = Path.cwd()
    output_path = current_dir / output_file
    
    print(f"🚀 Bundling Django Application")
    print(f"📁 Directory: {current_dir}")
    print(f"📄 Output: {output_path}")
    print("-" * 60)
    
    # Check if this looks like a Django project
    django_files = ['manage.py', 'settings.py', 'requirements.txt']
    has_django = any((current_dir / f).exists() for f in django_files) or \
                 any((current_dir / 'app' / f).exists() for f in ['settings.py']) or \
                 (current_dir / 'requirements.txt').exists()
    
    if not has_django:
        print("⚠️  Warning: This doesn't look like a Django project")
        print("   No manage.py, settings.py, or requirements.txt found")
    
    file_count = 0
    skipped_files = []
    total_size = 0
    
    # Collect project info
    project_info = {
        'name': current_dir.name,
        'apps': [],
        'models': [],
        'views': [],
        'urls': [],
        'forms': [],
        'serializers': [],
        'admin_classes': [],
        'commands': [],
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as bundle:
            # Write header
            bundle.write("=" * 80 + "\n")
            bundle.write("DJANGO APPLICATION BUNDLE\n")
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
                dirs[:] = [d for d in dirs if not should_skip_django(root_path / d)]
                
                for file in files:
                    file_path = root_path / file
                    if not should_skip_django(file_path):
                        if file_path == output_path:
                            continue
                        all_files.append(file_path)
            
            # Sort files by priority and then alphabetically
            all_files.sort(key=lambda x: (get_file_extension_priority(x), str(x)))
            
            # Process each file
            for file_path in all_files:
                try:
                    relative_path = file_path.relative_to(current_dir)
                    depth = len(relative_path.parents)
                    indent = "  " * depth
                    
                    # Write structure info
                    if include_docs:
                        if file_path.suffix == '.py':
                            bundle.write(f"{indent}🐍 {relative_path}\n")
                        elif file_path.suffix == '.html':
                            bundle.write(f"{indent}🌐 {relative_path}\n")
                        elif file_path.suffix in ['.css', '.scss']:
                            bundle.write(f"{indent}🎨 {relative_path}\n")
                        elif file_path.suffix == '.js':
                            bundle.write(f"{indent}📜 {relative_path}\n")
                        elif file_path.name in ['requirements.txt', 'Pipfile', 'pyproject.toml']:
                            bundle.write(f"{indent}📦 {relative_path}\n")
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
                    
                    # Extract Django info from Python files
                    if file_path.suffix == '.py':
                        file_info = extract_django_info(content)
                        for key in project_info:
                            if key in file_info:
                                project_info[key].extend(file_info[key])
                    
                    # Special handling for management commands
                    if 'management/commands' in str(file_path) and file_path.suffix == '.py':
                        cmd_name = file_path.stem
                        if cmd_name not in ['__init__', 'base']:
                            project_info['commands'].append(cmd_name)
                    
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
            
            if project_info['apps']:
                bundle.write(f"\n📱 DJANGO APPS ({len(set(project_info['apps']))}):\n")
                for app in sorted(set(project_info['apps'])):
                    bundle.write(f"  • {app}\n")
            
            if project_info['models']:
                bundle.write(f"\n🗄️  MODELS ({len(set(project_info['models']))}):\n")
                for model in sorted(set(project_info['models']))[:20]:
                    bundle.write(f"  • {model}\n")
                if len(set(project_info['models'])) > 20:
                    bundle.write(f"  ... and {len(set(project_info['models'])) - 20} more\n")
            
            if project_info['views']:
                bundle.write(f"\n👁️  VIEWS ({len(set(project_info['views']))}):\n")
                for view in sorted(set(project_info['views']))[:20]:
                    bundle.write(f"  • {view}\n")
                if len(set(project_info['views'])) > 20:
                    bundle.write(f"  ... and {len(set(project_info['views'])) - 20} more\n")
            
            if project_info['urls']:
                bundle.write(f"\n🔗 URL PATTERNS ({len(set(project_info['urls']))}):\n")
                for url in sorted(set(project_info['urls']))[:15]:
                    bundle.write(f"  • {url}\n")
            
            if project_info['forms']:
                bundle.write(f"\n📝 FORMS ({len(set(project_info['forms']))}):\n")
                for form in sorted(set(project_info['forms']))[:10]:
                    bundle.write(f"  • {form}\n")
            
            if project_info['serializers']:
                bundle.write(f"\n📦 SERIALIZERS ({len(set(project_info['serializers']))}):\n")
                for ser in sorted(set(project_info['serializers']))[:10]:
                    bundle.write(f"  • {ser}\n")
            
            if project_info['admin_classes']:
                bundle.write(f"\n🖥️  ADMIN CLASSES ({len(set(project_info['admin_classes']))}):\n")
                for admin in sorted(set(project_info['admin_classes']))[:10]:
                    bundle.write(f"  • {admin}\n")
            
            if project_info['commands']:
                bundle.write(f"\n⚙️  MANAGEMENT COMMANDS:\n")
                for cmd in sorted(set(project_info['commands'])):
                    bundle.write(f"  • {cmd}\n")
            
            bundle.write(f"\n📁 Directory structure (first 20 files):\n")
            for file_path in all_files[:20]:
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
    print(f"📱 Django apps: {len(set(project_info['apps']))}")
    print(f"🗄️  Models: {len(set(project_info['models']))}")
    print(f"👁️  Views: {len(set(project_info['views']))}")
    
    if skipped_files:
        print(f"⚠️  Skipped {len(skipped_files)} files")
    
    print(f"\n📄 Bundle saved to: {output_path}")
    
    return output_path

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bundle a Django application into a single text file'
    )
    parser.add_argument(
        '-o', '--output',
        default='django_bundle.txt',
        help='Output filename (default: django_bundle.txt)'
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
    print("Django Application Bundle Generator")
    print("=" * 60)
    
    result = bundle_django_app(
        output_file=args.output,
        include_docs=not args.minimal
    )
    
    print("\n🎉 Django bundle created successfully!")
    print(f"📁 Open with: cat {args.output}")
    print(f"📋 Or copy with: cat {args.output} | clip (Windows) | pbcopy (Mac)")

if __name__ == "__main__":
    main()