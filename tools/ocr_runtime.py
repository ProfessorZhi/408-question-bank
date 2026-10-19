#!/usr/bin/env python3
"""在 FJPCOS 上让 onnxruntime / rapidocr 真正能加载的兼容层。

背景（2026-10-16 实测，别再重复诊断）
------------------------------------
本机 C:\\Windows\\System32 里的 MSVC 运行时是 **VS2015 时代**的：

    14.0.0.23026  C:\\Windows\\System32\\msvcp140.dll
    14.0.0.23026  C:\\Windows\\System32\\vcruntime140.dll
    缺失          C:\\Windows\\System32\\vcruntime140_1.dll
    缺失（整机）  msvcp140_1.dll

而 `onnxruntime 1.30.0` 的 `version_info.py` 写着 `vs2019 = False`，即
**VS2022 构建**，硬依赖 14.4x 代的 `msvcp140.dll` + `msvcp140_1.dll`。
缺件时 onnxruntime 抛：

    ImportError: DLL load failed while importing onnxruntime_pybind11_state

这条消息极易被误诊成「rapidocr 没装」——`pip list` 明明有 1.4.4。
本模块把这条假象终结掉：它报的是**缺哪个 DLL、版本差多少**。

做法（不改系统、不改 Python 安装、不需要管理员）
------------------------------------------------
1. 先直接 `import onnxruntime`，能过就什么都不做；
2. 否则在本机**既有的应用程序目录**里找一份**同代成套**的 VC 运行时
   （Python 自身的 `vcruntime140(_1).dll` 是 14.0.42.34438，所以优先挑
   14.0.4x 一套的，避免 msvcp 与 vcruntime 代际错配——代际错配的表现
   不是报错而是**直接段错误**）;
3. 复制到仓库内已被 .gitignore 忽略的 `build/_scratch/ocr-dll/`，
   再用 `os.add_dll_directory()` **只对本进程**生效。

注意 `os.add_dll_directory()` 返回的句柄一旦被回收，目录就从搜索路径里
消失，所以本模块把它存在 `_KEEP_ALIVE` 里，别让 GC 收走。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as _wintypes
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 私有运行时目录：随 build/_scratch/ 一起被 .gitignore 忽略，不入库
DLL_DIR = REPO / "build" / "_scratch" / "ocr-dll"

# 必须凑齐的三件套；其余 msvcp140_* 有就一并带上
REQUIRED = ("msvcp140.dll", "msvcp140_1.dll", "vcruntime140_1.dll")
OPTIONAL = ("msvcp140_2.dll", "msvcp140_atomic_wait.dll",
            "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "concrt140.dll")

# msvcp140.dll 的最低版本：System32 那份 14.0.23026（VS2015）**不合格**，
# 用了会段错误。14.0.40 以上是 VS2022 代。
MIN_VERSION = (14, 0, 40)

# 本机已知的成套运行时所在目录（2026-10-16 实测；按代际从新到旧）
KNOWN_SOURCES = (
    r"D:\develop\tools\blender-5.2.1-windows-x64\blender.crt",
    r"C:\Program Files\Oray\AweSun\flutter",
    r"D:\develop\tools\blender\blender.crt",
)

# 兜底扫描的根（只找这几棵，不全盘扫）
SEARCH_ROOTS = (
    r"D:\develop\tools",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft"),
)

# 保住 add_dll_directory 的句柄，防止被 GC 回收后搜索路径失效
_KEEP_ALIVE: list = []
_VERBOSE = False


def _log(msg: str) -> None:
    if _VERBOSE:
        print(f"[ocr-runtime] {msg}", file=sys.stderr)


def file_version(path: str | os.PathLike) -> tuple[int, int, int, int] | None:
    """读 PE 的固定版本号；读不到返回 None。"""
    try:
        v = ctypes.windll.version
        size = v.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        v.GetFileVersionInfoW(str(path), 0, size, buf)
        ptr = ctypes.c_void_p()
        length = _wintypes.UINT()
        if not v.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)):
            return None
        if not ptr:
            return None
        fields = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32))
        ms, ls = fields[2], fields[3]
        return (ms >> 16, (ms >> 8) & 0xFF, ms & 0xFF, ls >> 16)
    except Exception:
        return None


def _set_ok(directory: Path) -> bool:
    """目录里是否凑齐了三件套，且 msvcp140.dll 够新。"""
    for name in REQUIRED:
        if not (directory / name).is_file():
            return False
    have = file_version(directory / "msvcp140.dll")
    return bool(have and have[:3] >= MIN_VERSION)


def _copied_set_ok() -> bool:
    return _set_ok(DLL_DIR)


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _install_from(source: Path) -> int:
    """把成套运行时复制进私有目录。

    刻意做成**幂等 + 重试**：本机装了杀软（深信服），新写入的 DLL 可能被
    实时扫描短暂锁住，裸 `copy2` 会偶发 `WinError 32 另一个程序正在使用此文件`。
    内容一致就直接跳过，不一致才重试覆盖。
    """
    import time

    DLL_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in REQUIRED + OPTIONAL:
        src = source / name
        if not src.is_file():
            continue
        dst = DLL_DIR / name
        if dst.is_file() and dst.stat().st_size == src.stat().st_size \
                and _sha256(dst) == _sha256(src):
            continue                      # 已装且一致
        last: Exception | None = None
        for attempt in range(6):
            try:
                shutil.copyfile(src, dst)
                copied += 1
                break
            except PermissionError as exc:
                last = exc
                time.sleep(0.5 * (attempt + 1))
        else:
            raise RuntimeError(
                f"复制 {name} 到 {dst} 失败（被杀软或其它进程占用）：{last}\n"
                "  请稍后重试，或先关闭占用该目录的进程。"
            ) from last
    return copied


def _find_source() -> Path | None:
    """找一份成套运行时。

    先在 KNOWN_SOURCES 里挑代际最新的；**命中就立刻返回，不再全盘扫**——
    本机 D 盘是带杀软扫描的机械盘，`os.walk("C:\\Program Files")` 实测能跑
    十几分钟，绝不能作为常走路径。只有已知目录全落空时才兜底扫。
    """
    best: tuple[tuple[int, int, int, int], Path] | None = None

    for raw in KNOWN_SOURCES:
        directory = Path(raw)
        if not _set_ok(directory):
            continue
        version = file_version(directory / "msvcp140.dll")
        if version and (best is None or version > best[0]):
            best = (version, directory)

    if best is not None:
        _log(f"已知目录命中：{best[1]}（msvcp140 {'.'.join(map(str, best[0]))}）")
        return best[1]

    _log("已知目录均不可用，开始兜底扫描（可能很慢）")
    for raw in SEARCH_ROOTS:
        root = Path(raw)
        if not root.is_dir():
            continue
        for dirpath, dirnames, _ in os.walk(root, onerror=lambda e: None):
            depth = len(Path(dirpath).parts) - len(root.parts)
            if depth > 5:
                dirnames[:] = []
                continue
            directory = Path(dirpath)
            if not _set_ok(directory):
                continue
            version = file_version(directory / "msvcp140.dll")
            if version and (best is None or version > best[0]):
                best = (version, directory)

    return best[1] if best else None


def ensure(verbose: bool = False) -> str | None:
    """确保本进程能 import onnxruntime。

    返回 None 表示无需干预（本机本来就正常）；否则返回被注册的目录。
    失败时抛 RuntimeError，消息里写清缺什么、该怎么办。
    """
    global _VERBOSE
    _VERBOSE = verbose

    try:
        import onnxruntime  # noqa: F401
        _log("onnxruntime 可正常导入，无需干预")
        return None
    except ImportError as first_error:
        _log(f"直接导入失败：{first_error}")

    # 一旦 pymupdf 已经进来，它就把 System32 那份 14.0.23026 的 msvcp140.dll
    # 按基名钉在进程里了；后面再 add_dll_directory 也顶替不掉，onnxruntime
    # 会绑到 2015 运行时上——**不报错，直接段错误**（本机实测 exit 139，零输出）。
    # 所以这里必须失败快、报得清楚，而不是让调用方去猜段错误。
    if "pymupdf" in sys.modules or "fitz" in sys.modules:
        raise RuntimeError(
            "pymupdf 已先于本模块导入：进程已绑定 System32 的旧 msvcp140.dll，\n"
            "  继续加载 onnxruntime 会段错误（不是抛异常）。\n"
            "  修法：把 ocr_runtime.ensure() 提到 `import pymupdf` 之前调用。"
        )

    if _copied_set_ok():
        _log(f"复用已有私有运行时：{DLL_DIR}")
    else:
        source = _find_source()
        if source is None:
            raise RuntimeError(
                "onnxruntime 加载失败，且本机未找到可用的 MSVC 运行时代际。\n"
                f"  System32 里的 msvcp140.dll 版本过低（需 >= "
                f"{'.'.join(map(str, MIN_VERSION))}），并且整机缺 msvcp140_1.dll。\n"
                "  解决：安装 Microsoft Visual C++ 2015-2022 Redistributable (x64)，\n"
                "  或把一份成套的 VC 运行时目录加进 KNOWN_SOURCES 后重跑。"
            )
        copied = _install_from(source)
        _log(f"已从 {source} 复制 {copied} 个运行时 DLL 到 {DLL_DIR}")

    _KEEP_ALIVE.append(os.add_dll_directory(str(DLL_DIR)))

    try:
        import onnxruntime
    except ImportError as exc:
        raise RuntimeError(
            f"注册私有运行时目录后仍然加载失败：{exc}\n"
            f"  目录：{DLL_DIR}\n"
            "  请核对 REQUIRED 三件套是否齐全、代际是否一致（msvcp 与 vcruntime 混代会段错误）。"
        ) from exc

    _log(f"onnxruntime {onnxruntime.__version__} 加载成功")
    return str(DLL_DIR)


if __name__ == "__main__":
    try:
        where = ensure(verbose=True)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
    print("无需干预" if where is None else f"已启用私有运行时：{where}")
