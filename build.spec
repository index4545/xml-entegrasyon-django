# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['whitenoise.middleware', 'whitenoise.storage', 'products.apps', 'integrations.apps', 'jazzmin']
tmp_ret = collect_all('jazzmin')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Add templates and static files
datas += [
    ('products/templates', 'products/templates'),
    # ('products/static', 'products/static'), # Static klasörü yoksa yorum satırı yap
    # ('core/templates', 'core/templates'), # Eğer varsa
    ('db.sqlite3', '.'), # Mevcut DB'yi dahil et (Opsiyonel, yoksa run_app oluşturur)
]

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='XML_Entegrasyon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # GUI uygulaması olduğu için konsolu gizle
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='XML_Entegrasyon',
)
