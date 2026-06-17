from __future__ import annotations

import struct
from typing import BinaryIO, ClassVar

from util import Color4, Vec4

class IMD:
    header: IMDHeader
    objects: list[IMDObj]
    # UP = -y
    UP: ClassVar[int] = -1

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
                prim_cls = IMDPrimTransformState
            case 0x13:
                prim_cls = IMDPrim0x13
            case 0x20:
                prim_cls = IMDPrim0x20
            case 0x21:
                prim_cls = IMDPrimTexture
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

class IMDPrimTransformState(IMDPrim):
    # type = 0x10
    # size = 0x70
    # Represents the transform state
    # (of some data within the model? Of the group containing this?)
    # and the relation between this node and others within the model
    # 8 - unknown int
    # C - unknown short
    # E - unknown short
    # 10
    orientation: Vec4
    # 20
    position: Vec4
    # 30
    scale: Vec4
    # 40 - unknown vec4
    # 50 - unknown vec4
    # 60 - the index of this node
    node_index: int
    # 64 - the index of the parent node (-1 indicates no parent)
    # Transformations are applied relative to the parent
    parent_node_index: int

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x10)
        prim.orientation = Vec4(*struct.unpack("<4f", f.read(4*4)))

        f.seek(pos + 0x20)
        prim.position = Vec4(*struct.unpack("<4f", f.read(4*4)))

        f.seek(pos + 0x30)
        prim.scale = Vec4(*struct.unpack("<4f", f.read(4*4)))

        f.seek(pos + 0x60)
        prim.node_index = struct.unpack("<i", f.read(4))[0]

        f.seek(pos + 0x64)
        prim.parent_node_index = struct.unpack("<i", f.read(4))[0]
        
        f.seek(pos)

        return prim

class IMDPrim0x13(IMDPrim):
    # type = 0x13
    # size = 0x90

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        
        f.seek(pos)

        return prim

class IMDPrim0x20(IMDPrim):
    # type = 0x20
    # size = 0x50
    # 20; vertex color scale?
    color_scale: Color4
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x20)
        prim.color_scale = Color4(*struct.unpack("<4f", f.read(4*4)))
        
        f.seek(pos)

        return prim
    
class IMDPrimTexture(IMDPrim):
    # type = 0x21
    # size = 0x60
    # texture?
    # 10; texture ID
    texture_id: int
    # 20; vec4f; color scale for this texture [0..128f]
    color_scale: Color4

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x10)
        prim.texture_id = struct.unpack("<I", f.read(4))[0]

        f.seek(pos + 0x20)
        prim.color_scale = Color4(*struct.unpack("<4f", f.read(4*4)))
        
        f.seek(pos)

        return prim

class IMDPrim0x48(IMDPrim):
    # UV + vertex data?
    # E; number of vertices
    # 60; the vertex data
    vertices: list[Vertex]

    class Vertex:
        # size = 0x18
        # OK, so here we seem to have the position of each vertex,
        # some unknown info,
        # a divisor value to convert shorts into floats,
        # some unknown info, and some UV info?
        # 0
        position: Vec4
        @classmethod
        def from_file(cls, f: BinaryIO):
            pos = f.tell()

            vertex = cls()

            f.seek(pos + 0xE)
            divisor = struct.unpack("<h", f.read(2))[0]
            if divisor == 0:
                pass

            f.seek(pos + 0x0)
            vertex.position = Vec4(*(c / divisor for c in struct.unpack("<3h", f.read(2*3))))

            f.seek(pos)
            return vertex

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0xE)
        num_vertices = struct.unpack("<H", f.read(2))[0]

        prim.vertices = []
        for i in range(num_vertices):
            vertex_pos = pos + 0x60 + (i * 0x18)
            f.seek(vertex_pos)

            # TODO: Models can seem to have breaks in their vertices list,
            # indicated by a 0x17 0xF bytes away from the last vertex.
            # How to handle this is unknown...
            # This might be to indicate two parts of the model which
            # don't have any vertices connecting them, perhaps?
            f.seek(vertex_pos + 0xF)
            if struct.unpack("<B", f.read(1))[0] == 0x17:
                raise RuntimeError(f"Found break in vertex list at {hex(vertex_pos)}; handling unimplemented.")
            f.seek(vertex_pos)

            prim.vertices.append(IMDPrim0x48.Vertex.from_file(f))
        
        f.seek(pos)

        return prim
