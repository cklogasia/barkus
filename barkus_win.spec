# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Collect all data and submodules for key dependencies
datas = []
binaries = []
hiddenimports = []

# Collect zxing-cpp data and binaries (replaces pyzbar for Windows 11)
try:
    zxing_datas, zxing_binaries, zxing_hiddenimports = collect_all('zxingcpp')
    datas += zxing_datas
    binaries += zxing_binaries
    hiddenimports += zxing_hiddenimports
except ImportError:
    pass

# Collect OpenCV data and binaries
try:
    cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')
    datas += cv2_datas
    binaries += cv2_binaries
    hiddenimports += cv2_hiddenimports
except ImportError:
    pass

# Collect PIL/Pillow data
try:
    pillow_datas = collect_data_files('PIL')
    datas += pillow_datas
except ImportError:
    pass

# Collect pdf2image data
try:
    pdf2image_datas = collect_data_files('pdf2image')
    datas += pdf2image_datas
except ImportError:
    pass

# Collect pikepdf data and binaries
try:
    pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = collect_all('pikepdf')
    datas += pikepdf_datas
    binaries += pikepdf_binaries
    hiddenimports += pikepdf_hiddenimports
except ImportError:
    pass

# Collect numpy data (critical for Windows compatibility)
try:
    numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
    datas += numpy_datas
    binaries += numpy_binaries
    hiddenimports += numpy_hiddenimports
except ImportError:
    pass

# Collect reportlab data (for test functionality)
try:
    reportlab_datas = collect_data_files('reportlab')
    datas += reportlab_datas
except ImportError:
    pass

# Collect qrcode data (for test functionality)  
try:
    qrcode_datas = collect_data_files('qrcode')
    datas += qrcode_datas
except ImportError:
    pass

# Add project requirements file
datas += [('requirements.txt', '.')]

# Add Poppler binaries (Windows 11 specific path: C:\Poppler)
poppler_path = 'C:/Poppler/bin'
if os.path.exists(poppler_path):
    poppler_files = ['pdftoppm.exe', 'pdftocairo.exe', 'pdfinfo.exe']
    for file in poppler_files:
        full_path = os.path.join(poppler_path, file)
        if os.path.exists(full_path):
            binaries += [(full_path, 'poppler/bin')]

# Fallback Poppler paths if C:\Poppler not found
fallback_poppler_paths = [
    'C:/poppler/Library/bin',
    'C:/Program Files/poppler/bin', 
    'C:/tools/poppler/bin',
    'C:/poppler/bin'
]

# Only check fallbacks if primary path doesn't exist
if not os.path.exists('C:/Poppler/bin'):
    for poppler_path in fallback_poppler_paths:
        if os.path.exists(poppler_path):
            poppler_files = ['pdftoppm.exe', 'pdftocairo.exe', 'pdfinfo.exe']
            for file in poppler_files:
                full_path = os.path.join(poppler_path, file)
                if os.path.exists(full_path):
                    binaries += [(full_path, 'poppler/bin')]
            break

# Hidden imports for Windows 11 compatibility
hiddenimports += [
    # Core PDF processing
    'pikepdf',
    'pikepdf._qpdf',
    'pikepdf._core',
    'pikepdf._methods',
    'pikepdf.objects',
    'pdf2image',
    'pdf2image.backends',
    'pdf2image.backends.poppler',
    'pdf2image.exceptions',
    
    # Barcode detection (zxing-cpp instead of pyzbar)
    'zxingcpp',
    'zxingcpp._zxingcpp',
    
    # Image processing - OpenCV
    'cv2',
    'cv2.cv2',
    
    # NumPy - critical Windows imports
    'numpy',
    'numpy.core',
    'numpy.core._methods', 
    'numpy.core._multiarray_umath',
    'numpy.core._multiarray_tests',
    'numpy.lib.format',
    'numpy.random',
    'numpy.random._pickle',
    'numpy.random._common',
    'numpy.random.bit_generator',
    'numpy.random._bounded_integers',
    'numpy.random.mtrand',
    'numpy.fft',
    'numpy.linalg',
    
    # PIL/Pillow
    'PIL', 
    'PIL._tkinter_finder',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageOps',
    'PIL.ImageFilter',
    'PIL._imaging',
    'PIL._imagingft',
    'PIL._webp',
    
    # Test dependencies (if needed for runtime)
    'reportlab',
    'reportlab.lib',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib.pagesizes',
    'reportlab.graphics.barcode',
    'reportlab.graphics.barcode.qr',
    'reportlab.platypus',
    'qrcode',
    'qrcode.image',
    'qrcode.image.pil',
    'qrcode.constants',
    'qrcode.util',
    
    # Application modules
    'barkus_modules',
    'barkus_modules.application',
    'barkus_modules.barcode_detector',
    'barkus_modules.pdf_processor',
    'barkus_modules.file_operations',
    'barkus_modules.logging_handler',
    
    # Standard library modules that may be missed
    'argparse',
    'csv',
    'datetime',
    'logging',
    'logging.handlers',
    'tempfile',
    'shutil',
    'collections',
    'collections.defaultdict',
    'enum',
    'dataclasses',
    'typing',
    
    # Additional Windows compatibility
    'pkg_resources',
    'pkg_resources.py2_warn',
    'pkg_resources._vendor',
    'setuptools',
    'distutils',
    'distutils.util',
]

# Windows-specific excludes to reduce size
excludes = [
    'tkinter',
    'matplotlib', 
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'pytest',
    'pyzbar',  # Excluded since we use zxing-cpp
    'docx',  # Only needed for compilation guide creation
    'unittest',  # Test framework not needed in production
    'test',
    'tests',
    '_pytest',
]

a = Analysis(
    ['barkus_main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='barkus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# COLLECT for directory mode (dist/barkus/)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='barkus'
)