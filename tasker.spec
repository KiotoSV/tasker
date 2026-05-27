# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Tasker (Планнер).
# Usage: pyinstaller tasker.spec --noconfirm

a = Analysis(
    ['src\\tasker\\__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('src\\tasker\\ui\\fonts', 'tasker\\ui\\fonts'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinterdnd2'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Tasker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Tasker',
)
