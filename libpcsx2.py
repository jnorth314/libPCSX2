from ctypes import byref, c_uint8, c_uint16, c_uint32, sizeof, windll
from ctypes.wintypes import DWORD, HANDLE, HMODULE, HWND, LPVOID, LPCVOID, LPDWORD
from functools import cached_property
import struct

import win32con

class PCSX2:
    """Class designed to interface with PCSX2"""

    def __init__(self, title: str) -> None:
        """Initialize with the title of the application"""

        self.title = title #TODO: Find the hwnd without the application title

    @cached_property
    def _hwnd(self) -> HWND:
        """Get the hwnd of the PCSX2 process"""

        return windll.user32.FindWindowW(None, self.title)

    @cached_property
    def _hprocess(self) -> HANDLE:
        """Get the handle of the PCSX2 process"""

        pid = DWORD()
        windll.user32.GetWindowThreadProcessId(self._hwnd, byref(pid))

        return windll.kernel32.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)

    @cached_property
    def _eemem(self) -> int:
        """Get the address in the PCSX2.exe for Emotion Engine memory"""

        lphModule = (HMODULE * 1024)()
        lpcbNeeded = LPDWORD()

        windll.psapi.EnumProcessModules(self._hprocess, lphModule, sizeof(lphModule), byref(lpcbNeeded))

        IMAGE_DOS_HEADER = lphModule[0]
        IMAGE_NT_HEADERS = IMAGE_DOS_HEADER + self._read(LPCVOID(IMAGE_DOS_HEADER + 0x3C), 4)
        IMAGE_OPTIONAL_HEADER = IMAGE_NT_HEADERS + 0x18

        ExportDirectoryAddress = IMAGE_DOS_HEADER + self._read(LPCVOID(IMAGE_OPTIONAL_HEADER + 0x70), 4)

        NumberOfNames = self._read(LPCVOID(ExportDirectoryAddress + 0x18), 4)
        AddressOfFunctions = IMAGE_DOS_HEADER + self._read(LPCVOID(ExportDirectoryAddress + 0x1C), 4)
        AddressOfNames = IMAGE_DOS_HEADER + self._read(LPCVOID(ExportDirectoryAddress + 0x20), 4)

        for i in range(NumberOfNames):
            NameAddress = IMAGE_DOS_HEADER + self._read(LPCVOID(AddressOfNames + (i << 2)), 4)
            FunctionAddress = IMAGE_DOS_HEADER + self._read(LPCVOID(AddressOfFunctions + (i << 2)), 4)

            if self._read(LPCVOID(NameAddress), 5).to_bytes(5)[::-1] == b"EEmem":
                return self._read(LPCVOID(FunctionAddress), 8)

        raise ValueError("Unable to find PCSX2's EEmem")

    def _read(self, lpBaseAddress: LPCVOID, nSize: int) -> int:
        """Read from process memory"""

        size = (nSize - 1) // sizeof(LPVOID) + 1
        lpBuffer = (LPVOID * size)()

        windll.kernel32.ReadProcessMemory(self._hprocess, lpBaseAddress, byref(lpBuffer), sizeof(lpBuffer), None)

        buffer = 0

        for i, _bytes in enumerate(lpBuffer):
            if _bytes is not None:
                buffer += _bytes << i*sizeof(LPVOID)

        return buffer & ((1 << nSize*8) - 1)

    def _write(self, lpBaseAddress: LPVOID, packet: c_uint8 | c_uint16 | c_uint32) -> None:
        """Write to process memory"""

        windll.kernel32.WriteProcessMemory(self._hprocess, lpBaseAddress, byref(packet), sizeof(packet), None)

    def read_u8(self, address: int) -> int:
        """Read an unsigned BYTE from EEmem"""

        return self._read(LPCVOID(self._eemem + address), 1)

    def read_u16(self, address: int) -> int:
        """Read an unsigned HALF-WORD from EEmem"""

        return self._read(LPCVOID(self._eemem + address), 2)

    def read_u32(self, address: int) -> int:
        """Read an unsigned WORD from EEmem"""

        return self._read(LPCVOID(self._eemem + address), 4)

    def read_f32(self, address: int) -> int:
        """Read a single precision floating point number from EEmem"""

        return struct.unpack("f", self._read(LPCVOID(self._eemem + address), 4).to_bytes(4, byteorder="little"))[0]

    def write_u8(self, address: int, packet: int) -> None:
        """Write an unsigned BYTE to EEmem"""

        self._write(LPVOID(self._eemem + address), c_uint8(packet))

    def write_u16(self, address: int, packet: int) -> None:
        """Write an unsigned HALF-WORD to EEmem"""

        self._write(LPVOID(self._eemem + address), c_uint16(packet))

    def write_u32(self, address: int, packet: int) -> None:
        """Write an unsigned WORD to EEmem"""

        self._write(LPVOID(self._eemem + address), c_uint32(packet))
