from __future__ import annotations

import struct
from typing import BinaryIO

class IMD:
    header: IMDHeader

    @classmethod
    def from_file(cls, f: BinaryIO):
        # TODO
        pos = f.tell()

        imd = cls()
        imd.header = IMDHeader.from_file(f)
        #f.seek(imd.header.p_objects)

        f.seek(pos)
        
        return imd
    
class IMDHeader:
    # bytes 0:3 should be "IMD "
    _magic: str
    # 4 ; always seems to be 0x200
    #unk04: int
    # 8 ; this should always be 0 when reading a file.
    # This indicates that all offsets for this file have been converted
    # to another address space (i.e. when getting loaded in game)
    is_deserialized: bool
    # C ; number of IMD "objects" contained within the file
    n_objects: int
    # 10; always seems to be 0
    #unk10: int
    # 14: always seems to be 0
    #unk14: int
    # 18: always seems to be 0
    #unk18: int
    # 1C: always seems to be 0
    #unk1C: int
    # 20: void*[]; this points to every object within the file
    p_objects: list[int]

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        header = cls()

        f.seek(pos + 0x0)
        header._magic = struct.unpack("<4s", f.read(4))[0].decode("utf-8")
        if header._magic != "IMD ":
            raise RuntimeError("File appears not to be a IMD file.")
        
        #header.unk04 = struct.unpack("<I", f.read(4))[0]

        f.seek(pos + 0x8)
        header.is_deserialized = bool(struct.unpack("<I", f.read(4))[0])
        header.n_objects = struct.unpack("<I", f.read(4))[0]
        #header.unk10 = struct.unpack("<I", f.read(4))[0]
        #header.unk14 = struct.unpack("<I", f.read(4))[0]
        #header.unk18 = struct.unpack("<I", f.read(4))[0]
        #header.unk1C = struct.unpack("<I", f.read(4))[0]

        f.seek(pos + 0x20)
        header.p_objects = list(struct.unpack(f"<{header.n_objects}I", f.read(4)))
        #header.unk24 = struct.unpack("<I", f.read(4))[0]
        #header.unk28 = struct.unpack("<I", f.read(4))[0]
        #header.unk2C = struct.unpack("<I", f.read(4))[0]

        f.seek(pos)
        
        return header
