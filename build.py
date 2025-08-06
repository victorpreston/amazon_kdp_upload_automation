#!/usr/bin/env python3
"""Build script for KDP Automation System
Compiles both preparation and automation scripts into standalone executables"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"Removed {spec_file}")

def create_spec_files():
    """Create PyInstaller spec files with custom configuration for both scripts"""
    # Common hidden imports
    common_hidden_imports = [
        'pandas',
        'openpyxl',
        'schedule',
        'json',
        'logging',
        'datetime',
        'pathlib',
        'shutil',
        'os',
        'time'
    ]
    
    # Common datas
    common_datas = [
        ('config.ini', '.'),
        ('README.md', '.'),
        ('metadata_full.csv', '.')
    ]
    
    # Create spec for kdp_preparation.py
    prep_spec = f'''# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['kdp_preparation.py'],
    pathex=[],
    binaries=[],
    datas={common_datas},
    hiddenimports={common_hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KDP_Preparation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''

    # Create spec for kdp_automation.py (similar to your original)
    auto_spec = f'''# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['kdp_automation.py'],
    pathex=[],
    binaries=[],
    datas={common_datas},
    hiddenimports={common_hidden_imports + [
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common',
        'selenium.webdriver.support',
        'requests',
        'urllib3',
        'configparser'
    ]},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KDP_Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''

    with open('kdp_preparation.spec', 'w') as f:
        f.write(prep_spec.strip())
    
    with open('kdp_automation.spec', 'w') as f:
        f.write(auto_spec.strip())
    
    print("Created PyInstaller spec files for both scripts")

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        return False
    return True

def build_executables():
    """Build both executables using PyInstaller"""
    print("Building executables...")
    try:
        # Build preparation script
        subprocess.run([
            'pyinstaller',
            '--clean',
            '--noconfirm',
            'kdp_preparation.spec'
        ], check=True)
        
        # Build automation script
        subprocess.run([
            'pyinstaller',
            '--clean',
            '--noconfirm',
            'kdp_automation.spec'
        ], check=True)
        
        print("Build completed successfully!")
        print("Executables created in: ./dist/")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False

def create_release_package():
    """Create a release package with all necessary files"""
    release_dir = Path('release')
    release_dir.mkdir(exist_ok=True)
    
    # Copy executables
    prep_exe = Path('dist/KDP_Preparation.exe')
    auto_exe = Path('dist/KDP_Automation.exe')
    
    if prep_exe.exists():
        shutil.copy2(prep_exe, release_dir / 'KDP_Preparation.exe')
    if auto_exe.exists():
        shutil.copy2(auto_exe, release_dir / 'KDP_Automation.exe')
    
    # Copy configuration files
    files_to_copy = [
        'config.ini',
        'README.md',
        'requirements.txt',
        'metadata_full.csv'
    ]
    
    for file_name in files_to_copy:
        if os.path.exists(file_name):
            shutil.copy2(file_name, release_dir / file_name)
    
    # Create batch file that runs both scripts in sequence
    batch_content = '''@echo off
echo Starting KDP Preparation System...
KDP_Preparation.exe

echo Starting KDP Automation System...
KDP_Automation.exe

pause
'''
    
    with open(release_dir / 'run_kdp_full_process.bat', 'w') as f:
        f.write(batch_content)
    
    print(f"Release package created in: {release_dir}")

def main():
    """Main build process"""
    print("KDP Automation System - Build Script")
    print("=" * 40)
    
    # Check if main scripts exist
    if not os.path.exists('kdp_automation.py'):
        print("Error: kdp_automation.py not found!")
        return
    
    if not os.path.exists('kdp_preparation.py'):
        print("Error: kdp_preparation.py not found!")
        return
    
    # Clean previous builds
    clean_build_dirs()
    
    # Install requirements
    if not install_requirements():
        return
    
    # Create spec files
    create_spec_files()
    
    # Build executables
    if build_executables():
        create_release_package()
        print("\n" + "=" * 40)
        print("BUILD SUCCESSFUL!")
        print("Your executables are ready in the 'release' directory")
        print("Run 'run_kdp_full_process.bat' to start the full process")
    else:
        print("\n" + "=" * 40)
        print("BUILD FAILED!")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()