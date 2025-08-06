# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['kdp_automation.py'],
    pathex=[],
    binaries=[],
    datas=[('config.ini', '.'), ('README.md', '.'), ('metadata_full.csv', '.')],
    hiddenimports=['pandas', 'openpyxl', 'schedule', 'json', 'logging', 'datetime', 'pathlib', 'shutil', 'os', 'time', 'selenium', 'selenium.webdriver', 'selenium.webdriver.chrome', 'selenium.webdriver.chrome.service', 'selenium.webdriver.common', 'selenium.webdriver.support', 'requests', 'urllib3', 'configparser'],
    hookspath=[],
    hooksconfig={},
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