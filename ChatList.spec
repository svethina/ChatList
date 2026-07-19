# -*- mode: python ; coding: utf-8 -*-
"""Сборка ChatList. Версия берётся только из version.py."""

import sys
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPECPATH)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from version import __version__

ICON_PATH = ROOT / "assets" / "icon.ico"


def _file_version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


_file_version = _file_version_tuple(__version__)
_version_str = ".".join(str(p) for p in _file_version)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_file_version,
        prodvers=_file_version,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", ""),
                        StringStruct("FileDescription", "ChatList"),
                        StringStruct("FileVersion", _version_str),
                        StringStruct("InternalName", "ChatList"),
                        StringStruct("OriginalFilename", "ChatList.exe"),
                        StringStruct("ProductName", "ChatList"),
                        StringStruct("ProductVersion", _version_str),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ChatList",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    version=version_info,
)
