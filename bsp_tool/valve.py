from collections import namedtuple  # for type hints
import enum  # for type hints
import lzma
import struct
from types import ModuleType
from typing import Dict, List

from . import base


class ValveBsp(base.Bsp):
    # https://developer.valvesoftware.com/wiki/Source_BSP_File_Format
    FILE_MAGIC = b"VBSP"
    HEADERS: Dict[str, namedtuple]
    # ^ {"LUMP_NAME": LumpHeader}
    VERSION: int = 0  # .bsp format version
    associated_files: List[str]  # files in the folder of loaded file with similar names
    branch: ModuleType
    filesize: int = 0  # size of .bsp in bytes
    filename: str
    folder: str
    loading_errors: List[str]  # list of errors raised loading lumps

    def __init__(self, branch: ModuleType, filename: str = "untitled.bsp", autoload: bool = True):
        super(ValveBsp, self).__init__(branch, filename, autoload)

    def _read_lump(self, LUMP: enum.Enum) -> (namedtuple, bytes):  # LumpHeader, data
        """Get LUMP from self.branch.LUMP; e.g. self.branch.LUMP.ENTITIES """
        # NOTE: each branch of VBSP has unique headers; so a read_lump_header function is called from branch
        header = self.branch.read_lump_header(self.file, LUMP)
        if header.length == 0:
            return header, None
        self.file.seek(header.offset)
        data = self.file.read(header.length)
        assert len(data) == header.fourCC
        if header.fourCC != 0:  # lump is compressed
            source_lzma_header = struct.unpack("3I5c", data[:17])
            # b"LZMA" = source_lzma_header[0]
            actual_size = source_lzma_header[1]  # value of fourCC
            # compressed_size = source_lzma_header[2]
            properties = b"".join(source_lzma_header[3:])
            _filter = lzma._decode_filter_properties(lzma.FILTER_LZMA1, properties)
            decompressor = lzma.LZMADecompressor(lzma.FORMAT_RAW, None, [_filter])
            data = decompressor.decompress(data[17:])
            if len(data) != actual_size:
                data = data[:actual_size]
        return header, data
