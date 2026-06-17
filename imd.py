from __future__ import annotations

import struct
from typing import BinaryIO

class IMD:
    header: IMDHeader
    objects: list[IMDObj]

    @classmethod
    def from_file(cls, f: BinaryIO):
        # TODO
        pos = f.tell()

        imd = cls()
        imd.header = IMDHeader.from_file(f)

        imd.objects = []
        for ptr in imd.header.p_objects:
            f.seek(ptr)
            imd.objects.append(IMDObj.from_file(f))

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

class IMDObj:
    type: int

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()
        obj_type: int = struct.unpack("<I", f.read(4))[0]
        
        obj_cls = None
        match obj_type:
            case 0x10:
                obj_cls = IMDObj0x10
            case _:
                raise RuntimeError(f"Unrecognized IMD Obj type {hex(obj_type)}")

        f.seek(pos)
        obj = obj_cls.from_file(f)
        f.seek(pos)
        return obj

class IMDObj0x10(IMDObj):
    # B0; null-terminated void*[]
    prims: list[IMDPrim]

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        obj = cls()

        f.seek(pos + 0xB0)
        p_prims: list[int] = []
        while (ptr := struct.unpack("<I", f.read(4))[0]) != 0:
            p_prims.append(ptr)

        obj.prims = []
        for ptr in p_prims:
            f.seek(ptr)
            obj.prims.append(IMDPrim.from_file(f))
        f.seek(pos)

        return obj


class IMDPrim:
    type: int

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()
        prim_type: int = struct.unpack("<I", f.read(4))[0]
        
        prim_cls = None
        match prim_type:
            case 0x01:
                prim_cls = IMDPrimGroup
            case 0x10:
                prim_cls = IMDPrim0x10
            case 0x13:
                prim_cls = IMDPrim0x13
            case 0x20:
                prim_cls = IMDPrim0x20
            case 0x21:
                prim_cls = IMDPrim0x21
            case 0x48:
                prim_cls = IMDPrim0x48
            case _:
                raise RuntimeError(f"Unrecognized IMD Prim type {hex(prim_type)}")

        f.seek(pos)
        prim = prim_cls.from_file(f)
        prim.type = prim_type
        f.seek(pos)
        return prim

class IMDPrimGroup(IMDPrim):
    # type 0x1
    # Seems to just be a list of primitives;
    # perhaps some sort of grouping.
    # 8; some sort of bitmask
    unk8: int 
    # C; some sort of bitmask (similar to 8)
    unkC: int
    # 10; null-terminated prim*[]
    prims: list[IMDPrim]

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x8)
        prim.unk8 = struct.unpack("<I", f.read(4))[0]
        f.seek(pos + 0xC)
        prim.unkC = struct.unpack("<I", f.read(4))[0]

        f.seek(pos + 0x10)
        p_prims: list[int] = []
        while (ptr := struct.unpack("<I", f.read(4))[0]) != 0:
            p_prims.append(ptr)

        prim.prims = []
        for ptr in p_prims:
            f.seek(ptr)
            prim.prims.append(IMDPrim.from_file(f))
        
        f.seek(pos)

        return prim

class IMDPrim0x10(IMDPrim):
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim

class IMDPrim0x13(IMDPrim):
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim

class IMDPrim0x20(IMDPrim):
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim
    
class IMDPrim0x21(IMDPrim):
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim

class IMDPrim0x48(IMDPrim):
    # UV + vertex data?
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim
