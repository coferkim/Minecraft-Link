from __future__ import annotations

import ctypes
import json
import re
import sys
from dataclasses import dataclass
from typing import Any


IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    MEM_COMMIT = 0x1000
    PAGE_GUARD = 0x100
    PAGE_NOACCESS = 0x01
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    kernel32.VirtualQueryEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL


SAUTH_KEYS = ("client_login_sn", "udid", "deviceid", "sdkuid", "sessionid")
PROCESS_CANDIDATES = (
    "FeverGamesInstaller.exe",
    "Minecraft.Windows.exe",
    "FeverGamesWeb.exe",
)
SEARCH_KEYS = (
    b"client_login_sn",
    b'"client_login_sn"',
    "client_login_sn".encode("utf-16-le"),
    '"client_login_sn"'.encode("utf-16-le"),
)
MAX_REGION_READ = 4 * 1024 * 1024
OVERLAP = 16 * 1024


@dataclass(frozen=True)
class CaptureResult:
    pid: int
    process_name: str
    sauth: dict[str, Any]
    scanned_bytes: int
    matched_offsets: int


def list_processes() -> list[tuple[int, str]]:
    if not IS_WINDOWS:
        return []
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == INVALID_HANDLE_VALUE:
        return []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    processes: list[tuple[int, str]] = []
    try:
        if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                processes.append((int(entry.th32ProcessID), entry.szExeFile))
                if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return processes


def _iter_regions(handle: int):
    address = 0
    mbi = MEMORY_BASIC_INFORMATION()
    while True:
        result = kernel32.VirtualQueryEx(
            handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi),
        )
        if not result:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            break
        if (
            mbi.State == MEM_COMMIT
            and mbi.Protect != PAGE_NOACCESS
            and not (mbi.Protect & PAGE_GUARD)
        ):
            yield base, size
        address = base + size
        if address <= base:
            break


def _read_region(handle: int, address: int, size: int) -> bytes | None:
    buffer = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(
        handle,
        ctypes.c_void_p(address),
        buffer,
        size,
        ctypes.byref(read),
    )
    if not ok:
        return None
    return buffer.raw[: read.value]


def _json_object_around(data: bytes, position: int) -> dict[str, Any] | None:
    start_limit = max(0, position - 24 * 1024)
    end_limit = min(len(data), position + 64 * 1024)
    starts = [i for i in range(start_limit, position + 1) if data[i : i + 1] == b"{"]
    for start in reversed(starts):
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, end_limit):
            char = data[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == 0x5C:
                    escaped = True
                elif char == 0x22:
                    in_string = False
                continue
            if char == 0x22:
                in_string = True
            elif char == 0x7B:
                depth += 1
            elif char == 0x7D:
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(data[start : index + 1].decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        break
                    if isinstance(value, dict) and any(key in value for key in SAUTH_KEYS):
                        return value
                    break
    return None


def _normalize_sauth(value: dict[str, Any]) -> dict[str, Any] | None:
    for wrapper in ("sauth_json", "sauth", "data"):
        nested = value.get(wrapper)
        if isinstance(nested, dict):
            normalized = _normalize_sauth(nested)
            if normalized:
                return normalized
        if isinstance(nested, str):
            try:
                parsed = json.loads(nested)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                normalized = _normalize_sauth(parsed)
                if normalized:
                    return normalized
    aliases = {
        "client_login_sn": ("client_login_sn", "CLIENT_LOGIN_SN"),
        "udid": ("udid", "UDID"),
        "deviceid": ("deviceid", "device_id", "DEVICE_ID"),
        "sdkuid": ("sdkuid", "SDKUID"),
        "sessionid": ("sessionid", "session_id", "SESSIONID"),
    }
    result: dict[str, Any] = {}
    for target, names in aliases.items():
        for name in names:
            if value.get(name) not in (None, ""):
                result[target] = str(value[name])
                break
    if all(key in result for key in SAUTH_KEYS):
        for key, item in value.items():
            result.setdefault(key, item)
        return result
    return None


def _extract_candidates(data: bytes) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for needle in SEARCH_KEYS:
        start = 0
        while True:
            position = data.find(needle, start)
            if position < 0:
                break
            candidate = _json_object_around(data, position)
            if candidate:
                normalized = _normalize_sauth(candidate)
                if normalized and normalized not in found:
                    found.append(normalized)
            start = position + len(needle)
    return found


def _candidate_key(value: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(value.get(key, "")) for key in SAUTH_KEYS)


def _capture_pid(pid: int, process_name: str, max_bytes: int) -> CaptureResult:
    if not IS_WINDOWS:
        raise RuntimeError("sauth 自动捕获仅支持 Windows")

    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        raise PermissionError(f"无法读取进程 {process_name} (pid={pid})，错误码 {error}")

    scanned = 0
    offsets = 0
    candidates: dict[tuple[str, ...], dict[str, Any]] = {}
    try:
        for base, region_size in _iter_regions(handle):
            if scanned >= max_bytes:
                break
            offset = 0
            previous_tail = b""
            while offset < region_size and scanned < max_bytes:
                chunk_size = min(MAX_REGION_READ, region_size - offset, max_bytes - scanned)
                chunk = _read_region(handle, base + offset, chunk_size)
                if chunk:
                    scanned += len(chunk)
                    for candidate in _extract_candidates(previous_tail + chunk):
                        candidates[_candidate_key(candidate)] = candidate
                    previous_tail = chunk[-OVERLAP:]
                offset += chunk_size
    finally:
        kernel32.CloseHandle(handle)

    if not candidates:
        return CaptureResult(pid, process_name, {}, scanned, 0)
    best = max(candidates.values(), key=lambda item: sum(bool(item.get(key)) for key in SAUTH_KEYS))
    offsets = len(candidates)
    return CaptureResult(pid, process_name, best, scanned, offsets)


def capture_sauth(
    pid: int | None = None,
    process_name: str | None = None,
    max_bytes: int = 1024 * 1024 * 1024,
) -> CaptureResult | None:
    if not IS_WINDOWS:
        raise RuntimeError("sauth 自动捕获仅支持 Windows")

    processes = list_processes()
    if pid is not None:
        actual_name = next((name for item_pid, name in processes if item_pid == pid), process_name or str(pid))
        return _capture_pid(pid, actual_name, max_bytes)

    names = [process_name] if process_name else list(PROCESS_CANDIDATES)
    matches: list[tuple[int, str]] = []
    for name in names:
        matches.extend(item for item in processes if item[1].lower() == name.lower())
    if not matches:
        matches = [
            item
            for item in processes
            if item[1].lower() in {"minecraft.windows.exe", "minecraft.exe"}
        ]
    if not matches:
        return None

    last_result: CaptureResult | None = None
    last_error: Exception | None = None
    for candidate_pid, candidate_name in matches:
        try:
            result = _capture_pid(candidate_pid, candidate_name, max_bytes)
        except PermissionError as exc:
            last_error = exc
            continue
        if result.sauth:
            return result
        last_result = result
    if last_error and last_result is None:
        raise last_error
    return last_result


def capture_from_text(text: str) -> dict[str, Any] | None:
    data = text.encode("utf-8", errors="ignore")
    candidates = _extract_candidates(data)
    if candidates:
        return candidates[0]
    fields: dict[str, str] = {}
    for key in SAUTH_KEYS:
        match = re.search(rf"{re.escape(key)}\s*[=:]\s*['\"]?([^&,\s\"']+)", text)
        if match:
            fields[key] = match.group(1)
    return _normalize_sauth(fields)
