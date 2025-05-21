 Based on my analysis, use this PyInstaller command on your Windows machine:

  pyinstaller --onefile --add-binary="C:/path/to/poppler/bin;poppler/bin" --hidden-import=pikepdf._qpdf --hidden-import=pkg_resources.py2_warn --hidden-import=cv2 
  --collect-submodules=pyzbar --collect-submodules=pdf2image barkus.py

  Key points:
  1. Replace C:/path/to/poppler/bin with your actual Poppler path
  2. Install Poppler on Windows (required by pdf2image)
  3. Install Visual C++ Redistributable (required by various dependencies)
  4. Use a virtual environment with all dependencies installed before compiling

  This configuration handles the complex dependencies of pikepdf, OpenCV, and the PDF processing libraries.

● Update Todos
  ⎿  ☒ Analyze app dependencies and requirements
     ☒ Identify PyInstaller compilation options
     ☒ Determine correct PyInstaller command with appropriate options
     ☒ Check for binary dependencies that need special handling

● You'll also need to ensure zbar is installed on your system since pyzbar depends on it. The easiest approach on Windows is to:

  1. Install the pre-built zbar binaries (download from SourceForge)
  2. Add zbar to your PATH or use --add-binary to include it in your package

  If you're still having issues after trying the command I provided, you can create a PyInstaller spec file for more control:

  # barkus.spec
  a = Analysis(['barkus.py'],
      binaries=[('C:/path/to/poppler/bin/*', 'poppler/bin'),
                ('C:/path/to/zbar/bin/*', 'zbar/bin')],
      hiddenimports=['pikepdf._qpdf', 'pkg_resources.py2_warn', 'cv2'],
      hookspath=[],
      runtime_hooks=[],
      excludes=[],
      win_no_prefer_redirects=False,
      win_private_assemblies=False,
      noarchive=False)

  pyz = PYZ(a.pure, a.zipped_data)

  exe = EXE(pyz,
      a.scripts,
      a.binaries,
      a.zipfiles,
      a.datas,
      [],
      name='barkus',
      debug=False,
      bootloader_ignore_signals=False,
      strip=False,
      upx=True,
      upx_exclude=[],
      runtime_tmpdir=None,
      console=True)

  Then run: pyinstaller barkus.spec
