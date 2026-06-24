from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO, ClassVar, Sequence, Type, TypeVar, cast

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
    
    def __get_all_prims_of_type(self, prim_type: Type[IMDPrim]) -> Sequence[IMDPrim]:
        prims: list[IMDPrim] = []

        for obj in self.objects:
            obj_prims = obj.get_prims()
            for prim in obj_prims:
                if isinstance(prim, prim_type):
                    prims.append(prim)

                prim_prims = prim.get_prims()
                for prim in prim_prims:
                    if isinstance(prim, prim_type):
                        prims.append(prim)
        
        return prims

    T = TypeVar("T")
    def get_all_objects_of_type(self, obj_type: Type[T]) -> Sequence[T]:
        return [obj for obj in self.objects if isinstance(obj, obj_type)]

    def get_all_textures(self) -> Sequence[IMDPrimTexture]:
        result = self.__get_all_prims_of_type(IMDPrimTexture)
        return cast("Sequence[IMDPrimTexture]", result)
    
    def get_all_groups(self) -> Sequence[IMDPrimModelGroup]:
        # TODO: this doesn't respect nesting -- but maybe we could just arrange a
        # dict of {parent: children} here if all groups have a transform state with a parent node ID?
        result = self.__get_all_prims_of_type(IMDPrimModelGroup)
        return cast(Sequence[IMDPrimModelGroup], result)
    
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
        header.p_objects = list(struct.unpack(f"<{header.n_objects}I", f.read(4*header.n_objects)))
        #header.unk24 = struct.unpack("<I", f.read(4))[0]
        #header.unk28 = struct.unpack("<I", f.read(4))[0]
        #header.unk2C = struct.unpack("<I", f.read(4))[0]

        f.seek(pos)
        
        return header

class IMDObj:
    type: ClassVar[int] = 0

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()
        obj_type: int = struct.unpack("<I", f.read(4))[0]
        
        obj_cls = None
        match obj_type:
            case 0x10:
                obj_cls = IMDObjModel
            case 0x20:
                obj_cls = IMDObj0x20
            case _:
                raise RuntimeError(f"Unrecognized IMD Obj type {hex(obj_type)}")

        f.seek(pos)
        obj = obj_cls.from_file(f)
        f.seek(pos)
        return obj
    
    def get_prims(self) -> list[IMDPrim]:
        return []

class IMDObjModel(IMDObj):
    type: ClassVar[int] = 0x10
    # B0; null-terminated void*[]
    prims: list[IMDPrim]

    _top_level_nodes: list[IMDPrimTransformState]

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        obj = cls()
        obj._top_level_nodes = []

        f.seek(pos + 0xB0)
        p_prims: list[int] = []
        while (ptr := struct.unpack("<I", f.read(4))[0]) != 0:
            p_prims.append(ptr)

        obj.prims = []
        for ptr in p_prims:
            f.seek(ptr)
            obj.prims.append(IMDPrim.from_file(f))
        f.seek(pos)

        # Form parent/children node relationships
        obj._construct_scene_graph()
        return obj

    def _construct_scene_graph(self):
        # Start by first gathering all transform states
        transform_states: dict[int, IMDPrimTransformState] = {}
        for prim in self.get_prims():
            for prim_prim in prim.get_prims():
                if isinstance(prim_prim, IMDPrimTransformState):
                    index = prim_prim.node_index
                    transform_states[index] = prim_prim

        # Now using we associate each model group with a state,
        # and also form the parent/child relationships in the states
        for prim in self.get_prims():
            group = prim if isinstance(prim, IMDPrimModelGroup) else None
            for prim_prim in prim.get_prims():
                if isinstance(prim_prim, IMDPrimTransformState):
                    transform_state = prim_prim
                    node_index = transform_state.node_index
                    
                    # Assign the associated groups to this transform state
                    child_state = transform_states[node_index]
                    if group is not None:
                        child_state.groups.append(group)

                    # Create the parent/child relationship, if this node has a parent
                    parent_node_index = transform_state.parent_node_index
                    if parent_node_index == -1:
                        # This transformation state has no parent
                        continue
                    assert parent_node_index in transform_states

                    parent_state = transform_states[parent_node_index]
                    child_state.parent = parent_state
                    parent_state.children.append(child_state)

        self._top_level_nodes = [tstate for tstate in transform_states.values() if tstate.parent is None]
        pass

    def get_prims(self) -> list[IMDPrim]:
        return self.prims

    def get_top_level_nodes(self):
        return self._top_level_nodes
    
class IMDObj0x20(IMDObj):
    type: ClassVar[int] = 0x20

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        obj = cls()
        print(f"IMD | WARNING: Encountered unimplemented Obj type {hex(obj.type)}")
        
        f.seek(pos)

        return obj
    
@dataclass
class Vertex:
    # Generic vertex object class
    size: ClassVar[int] = 0x0
    """Size of the vertex object (in the IMD file)"""
    position: Vec4 = field(default_factory=Vec4)
    """Position of this vertex"""
    vertex_order: int = 0
    """The vertex order of the polygon this vertex is the last vertex for.
    Can be 1 of three possible value ranges:

    x<0: The vertices are in ascending order (e.g. 0 1 2, at least for Panda3D)

    x=0: A polygon is not drawn using this vertex as the last vertex

    x>0: The vertices are in descending order (e.g. 2 1 0, at least for Panda3D)
    """
    normal: Vec4 = field(default_factory=Vec4)
    """
    The normal for this vertex. Note that if the vertex pool does not use vertex normals,
    the normal of the last vertex will be used for the polygon instead.
    """
    rgba: Color4 | None = None
    """RGBA for the vertex; not all vertex pool types have RGBA values."""
    u: float = 0.0
    """Texture U coordinate"""
    v: float = 0.0
    """Texture V coordinate"""

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        vert = cls()
        
        f.seek(pos)

        return vert

class IMDPrim:
    type: ClassVar[int] = 0

    @classmethod
    def from_file(cls, f: BinaryIO) -> IMDPrim:
        pos = f.tell()
        prim_type: int = struct.unpack("<I", f.read(4))[0]
        
        prim_cls = None
        match prim_type:
            case 0x01:
                prim_cls = IMDPrimModelGroup
            case 0x02:
                prim_cls = IMDPrimModelTransformStateList
            case 0x10:
                prim_cls = IMDPrimTransformState
            case 0x13:
                prim_cls = IMDPrim0x13
            case 0x20:
                prim_cls = IMDPrimVertexColor
            case 0x21:
                prim_cls = IMDPrimTexture
            case 0x22:
                prim_cls = IMDPrim0x22
            case 0x23:
                prim_cls = IMDPrimTextureAnimated
            case 0x24:
                prim_cls = IMDPrim0x24
            case 0x25:
                prim_cls = IMDPrim0x25
            case 0x26:
                prim_cls = IMDPrim0x26
            case 0x28:
                prim_cls = IMDPrim0x28
            case 0x40:
                prim_cls = IMDPrimFloatVertexPool
            case 0x41:
                prim_cls = IMDPrimFloatVertexPoolWithRGBA
            case 0x42:
                prim_cls = IMDPrim0x42
            case 0x48:
                prim_cls = IMDPrimShortVertexPool
            case 0x49:
                prim_cls = IMDPrimShortVertexPoolWithRGBA
            case 0x4A:
                prim_cls = IMDPrim0x4A
            case 0x50:
                prim_cls = IMDPrim0x50
            case 0x58:
                prim_cls = IMDPrimDeformableVertexPool
            case 0x60:
                prim_cls = IMDPrim0x60
            case 0x64:
                prim_cls = IMDPrim0x64
            case 0x66:
                prim_cls = IMDPrim0x66
            case 0x6C:
                prim_cls = IMDPrim0x6C
            case _:
                raise RuntimeError(f"Unrecognized IMD Prim type {hex(prim_type)}")

        f.seek(pos)
        prim = prim_cls.from_file(f)
        f.seek(pos)
        return prim
    
    def get_prims(self) -> Sequence[IMDPrim]:
        return []
    
class IMDPrimGenericVertexPool(IMDPrim):
    type = 0x100 #special
    # Generic class for vertex pool primitives
    VERTEX_CLASS = Vertex
    VIF_PACKET_START_OFFSET = 0x10
    VERTEX_START_OFFSET = 0x50
    has_vertex_normals: bool
    vertices: Sequence[Vertex]

    @classmethod
    def from_file(cls, f: BinaryIO): # type: ignore # This is a base class so it's fine
        pos = f.tell()

        prim = cls()

        vif_pos = pos + cls.VIF_PACKET_START_OFFSET

        f.seek(pos + 0xE)
        num_vertices = struct.unpack("<H", f.read(2))[0]

        # NOTE: Technically, since a pool is a collection of 1 or more VIF packets,
        # each packet could have a different configuration (such that one part of the pool
        # uses polygon normals, and another vertex normals, etc.). For the time being it'd be nice
        # to avoid handling each packet separately, if it's possible/accurate.
        f.seek(vif_pos + 0x26)
        prim.has_vertex_normals = bool(struct.unpack("<B", f.read(1))[0] & 0x4)

        vertex_size = prim.VERTEX_CLASS.size

        prim.vertices = []
        offset = cls.VERTEX_START_OFFSET
        for i in range(num_vertices):
            vertex_pos = vif_pos + offset + (i * vertex_size)
            f.seek(vertex_pos)

            f.seek(vertex_pos + 0xF)
            if struct.unpack("<B", f.read(1))[0] == 0x17:
                # It appears this marks the end of a GIF packet(?)
                # we can skip over the start of the next packet and
                # continue reading vertex data
                # (To do this we skip 0x50; but, we also want to skip over
                # the first two vertices in the new packet as well, as they seem to
                # just send the last two vertices from the old packet again,
                # so 0x50 + (0x18 * 2) or 0x80 in total)
                delta = (prim.VERTEX_START_OFFSET) + vertex_size * 2
                offset += delta
                vertex_pos += delta
            f.seek(vertex_pos)

            prim.vertices.append(prim.VERTEX_CLASS.from_file(f))
        
        f.seek(pos)

        return prim

class IMDPrimModelGroup(IMDPrim):
    type: ClassVar[int] = 1
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
    
    def get_prims(self) -> Sequence[IMDPrim]:
        return self.prims
    
class IMDPrimModelTransformStateList(IMDPrim):
    # TODO: This primitive is like an IMDPrimModelGroup, but only contains transformation states!
    # These states will essentially be empty nodes, but will provide some sort of additional
    # transformation for children; we'll need to process these in order to properly establish the
    # parent/child relationship of groups.
    type: ClassVar[int] = 0x2
    # 10; null-terminated prim*[]
    prims: list[IMDPrimTransformState]

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x10)
        p_prims: list[int] = []
        while (ptr := struct.unpack("<I", f.read(4))[0]) != 0:
            p_prims.append(ptr)

        prim.prims = []
        for ptr in p_prims:
            f.seek(ptr)
            new_prim = IMDPrim.from_file(f)
            assert isinstance(new_prim, IMDPrimTransformState)
            prim.prims.append(new_prim)
        
        f.seek(pos)

        return prim
    
    def get_prims(self) -> Sequence[IMDPrimTransformState]:
        return self.prims

class IMDPrimTransformState(IMDPrim):
    type: ClassVar[int] = 0x10
    # size = 0x70
    # Represents the transform state
    # (of some data within the model? Of the group containing this?)
    # and the relation between this node and others within the model
    # 8 - info about billboarding
    is_billboard: bool
    is_billboard_axis: bool
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

    # internal properties
    parent: IMDPrimTransformState | None
    children: list[IMDPrimTransformState]
    groups: list[IMDPrimModelGroup] # Groups which utilize this transform state

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        prim.parent = None
        prim.children = []
        prim.groups = []

        f.seek(pos + 0x8)
        prim.is_billboard = bool(struct.unpack("<b", f.read(1))[0] & 0x1)
        if prim.is_billboard:
            f.seek(pos + 0x8)
            prim.is_billboard_axis = bool(struct.unpack("<b", f.read(1))[0] & 0x2)
        else:
            prim.is_billboard_axis = False

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
    type: ClassVar[int] = 0x13
    # size = 0x90

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim

class IMDPrimVertexColor(IMDPrim):
    type: ClassVar[int] = 0x20
    # size = 0x50
    # 10; vertex color scale?
    color_scale: Color4
    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()

        f.seek(pos + 0x10)
        prim.color_scale = Color4(*(c / 255.0 for c in struct.unpack("<4f", f.read(4*4))))
        prim.color_scale.a = min(prim.color_scale.a * 2.0, 1.0)
        
        f.seek(pos)

        return prim
    
class IMDPrimTexture(IMDPrim):
    type: ClassVar[int] = 0x21
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

class IMDPrim0x22(IMDPrim):
    type: ClassVar[int] = 0x22

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
 
class IMDPrimTextureAnimated(IMDPrimTexture):
    type: ClassVar[int] = 0x23
    # An animated texture of some sort,
    # presumably utilizing UV scroll.

    @classmethod
    def from_file(cls, f: BinaryIO):
        print("IMD | WARNING: Animated texture (0x23) partially implemented as static texture (0x21).")
        return super().from_file(f)
    
class IMDPrim0x24(IMDPrim):
    type: ClassVar[int] = 0x24

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x25(IMDPrim):
    type: ClassVar[int] = 0x25

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x26(IMDPrim):
    type: ClassVar[int] = 0x26

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x28(IMDPrim):
    type: ClassVar[int] = 0x28

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class Vertex0x40(Vertex):
    size = 0x30

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()
        vert = cls()

        # 0..B; 3 packed floats for position
        f.seek(pos + 0x0)
        vert.position = Vec4(*struct.unpack("<3f", f.read(4*3)))

        # C; vertex order
        # This one is a bit weird; if when read as a 16-bit and is non-zero,
        # this polygon is not drawn. Else, we use the float value to
        # determine the order (usu. 1.0f or -1.0f).
        f.seek(pos + 0xC)
        is_drawn = struct.unpack("<h", f.read(2))[0] == 0
        if not is_drawn:
            vert.vertex_order = 0
        else:
            f.seek(pos + 0xC)
            vert.vertex_order = int(struct.unpack("<f", f.read(4))[0])

        # 10..1B; 3 packed floats for normal
        f.seek(pos + 0x10)
        vert.normal = Vec4(*struct.unpack("<3f", f.read(4*3)))

        # 20/24; u and v
        f.seek(pos + 0x20)
        vert.u = struct.unpack("<f", f.read(4))[0]
        vert.v = 1.0 - struct.unpack("<f", f.read(4))[0]

        f.seek(pos)
        return vert
    
class IMDPrimFloatVertexPool(IMDPrimGenericVertexPool):
    type: ClassVar[int] = 0x40
    VERTEX_CLASS = Vertex0x40
    VERTEX_START_OFFSET = 0x40

class Vertex0x41(Vertex0x40):
    # size = 0x20
    size = 0x40
    # Like the vertex class used for primitive 0x08, but this vertex
    # also has color data which is linearly interpolated on the triangle
    # along other vertices in the triangle.

    @classmethod
    def from_file(cls, f: BinaryIO):
        vert = super().from_file(f)
        
        pos = f.tell()

        # 30 - packed float color rgba
        f.seek(pos + 0x30)
        vert.rgba = Color4(*(c / 128.0 for c in struct.unpack("<4f", f.read(4*4))))
        #vert.rgba.a = min(vert.rgba.a * 2, 1.0)
        
        f.seek(pos)
        return vert
    
class IMDPrimFloatVertexPoolWithRGBA(IMDPrimFloatVertexPool):
    type: ClassVar[int] = 0x41
    VERTEX_CLASS = Vertex0x41
    # NOTE: I have not thoroughly tested this, but after glancing at it in a file
    # this seems similar to the 0x48/0x49 pairing.
    
class IMDPrim0x42(IMDPrim):
    type: ClassVar[int] = 0x42

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim

class Vertex0x48(Vertex):
    size = 0x18

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        vertex = cls()

        f.seek(pos + 0xE)
        # TODO: Some sort of scale value, guessing at this
        #scale = struct.unpack("<h", f.read(2))[0] / 0x1000

        f.seek(pos + 0x0)
        # 0..5; packed 3 signed 16-bit Vertex position
        # NOTE: This scale is just arbitrary
        vertex.position = Vec4(*(c / 0x40 for c in struct.unpack("<3h", f.read(2*3))))

        # 6 (short); The vertex order of the polygon this vertex is the last vertex for.
        # Can be 1 of three possible value ranges:
        # x<0: The vertices are in ascending order (e.g. 0 1 2, at least for Panda3D)
        # x=0: A polygon is not drawn using this vertex as the last vertex
        # x>0: The vertices are in descending order (e.g. 2 1 0, at least for Panda3D)
        f.seek(pos + 0x6)
        vertex.vertex_order = struct.unpack("<h", f.read(2))[0]

        # 8..D 3 signed 16-bits for normal?
        f.seek(pos + 0x8)
        vertex.normal = Vec4(*(v / 0x8000 for v in struct.unpack("<3h", f.read(2*3))))

        # 10 texture U (short)
        # 12 texture V (short)
        # NOTE: 14 and 16 seem to be possibly be divisors for U and V,
        # these are probably 0x1000 but we should probably read these too.
        f.seek(pos + 0x10)
        vertex.u = struct.unpack("<h", f.read(2))[0] / 0x1000
        vertex.v = 1.0 - struct.unpack("<h", f.read(2))[0] / 0x1000

        f.seek(pos)
        return vertex
    
    @property
    def x(self):
        return self.position.x
    @property
    def y(self):
        return self.position.y
    @property
    def z(self):
        return self.position.z

class IMDPrimShortVertexPool(IMDPrimGenericVertexPool):
    type: ClassVar[int] = 0x48
    VERTEX_CLASS = Vertex0x48

class Vertex0x49(Vertex0x48):
    # size = 0x20
    size = 0x20
    # Like the vertex class used for primitive 0x48, but this vertex
    # also has color data which is linearly interpolated on the triangle
    # along other vertices in the triangle.

    @classmethod
    def from_file(cls, f: BinaryIO):
        vert = super().from_file(f)
        
        pos = f.tell()

        # 18 - packed uint16 color rgba
        f.seek(pos + 0x18)
        vert.rgba = Color4(*(c / 0x80 for c in struct.unpack("<4h", f.read(2*4))))
        vert.rgba.a = min(vert.rgba.a * 2, 1.0)
        
        f.seek(pos)
        return vert

class IMDPrimShortVertexPoolWithRGBA(IMDPrimShortVertexPool):
    type: ClassVar[int] = 0x49
    VERTEX_CLASS = Vertex0x49
    
class IMDPrim0x4A(IMDPrim):
    type: ClassVar[int] = 0x4A

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x50(IMDPrim):
    type: ClassVar[int] = 0x50

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
@dataclass
class Vertex0x58Base(Vertex0x48):
    is_connective = False
    
class Vertex0x58NonConnective(Vertex0x58Base):
    size = 0x18
    is_connective = False

class Vertex0x58Connective(Vertex0x58Base):
    size = 0x28
    is_connective = True
    

class IMDPrimDeformableVertexPool(IMDPrim):
    type: ClassVar[int] = 0x58
    VIF_PACKET_START_OFFSET = 0x30
    VERTEX_START_OFFSET = 0x50
    has_vertex_normals: bool
    vertices: Sequence[Vertex]

    pool_index: int
    connected_pools: Sequence[int]

    @classmethod
    def from_file(cls, f: BinaryIO): # type: ignore # This is a base class so it's fine
        pos = f.tell()

        prim = cls()
        prim.vertices = []
        prim.pool_index = -1
        prim.connected_pools = []

        vif_pos = pos + cls.VIF_PACKET_START_OFFSET

        f.seek(pos + 0xE)
        num_vertices = struct.unpack("<H", f.read(2))[0]
        

        # 10; a sign-terminated list of 8 32-bit ints. If a length of 1, indicates the
        # index of this pool. If a length of >1, then this indicates which pools this pool connects to.
        f.seek(pos + 0x14)
        vertex_class = Vertex0x58NonConnective
        second_pool = struct.unpack("<i", f.read(4))[0]
        if second_pool != -1:
            print("IMD | WARNING: Encountered connective 0x58 prim; this is not yet properly supported.")
            f.seek(pos + 0x10)
            while (pool := struct.unpack("<i", f.read(4))[0]) != -1:
                prim.connected_pools.append(pool)
            vertex_class = Vertex0x58Connective
        else:
            f.seek(pos + 0x10)
            prim.pool_index = struct.unpack("<i", f.read(4))[0]
            vertex_class = Vertex0x58NonConnective

        # NOTE: Technically, since a pool is a collection of 1 or more VIF packets,
        # each packet could have a different configuration (such that one part of the pool
        # uses polygon normals, and another vertex normals, etc.). For the time being it'd be nice
        # to avoid handling each packet separately, if it's possible/accurate.
        f.seek(vif_pos + 0x36)
        prim.has_vertex_normals = bool(struct.unpack("<B", f.read(1))[0] & 0x4)

        f.seek(pos + 0x14)
        vertex_size = vertex_class.size

        offset = cls.VERTEX_START_OFFSET
        for i in range(num_vertices):
            vertex_pos = vif_pos + offset + (i * vertex_size)
            f.seek(vertex_pos)

            f.seek(vertex_pos + 0xF)
            if struct.unpack("<B", f.read(1))[0] == 0x17:
                # It appears this marks the end of a GIF packet(?)
                # we can skip over the start of the next packet and
                # continue reading vertex data
                # (To do this we skip 0x50; but, we also want to skip over
                # the first two vertices in the new packet as well, as they seem to
                # just send the last two vertices from the old packet again,
                # so 0x50 + (0x18 * 2) or 0x80 in total)
                delta = (prim.VERTEX_START_OFFSET) + vertex_size * 2
                offset += delta
                vertex_pos += delta
            f.seek(vertex_pos)

            prim.vertices.append(vertex_class.from_file(f))
        
        f.seek(pos)

        return prim
    
class IMDPrim0x60(IMDPrim):
    type: ClassVar[int] = 0x60

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x64(IMDPrim):
    type: ClassVar[int] = 0x64

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
    
class IMDPrim0x66(IMDPrim):
    type: ClassVar[int] = 0x66

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim

class IMDPrim0x6C(IMDPrim):
    type: ClassVar[int] = 0x6C

    @classmethod
    def from_file(cls, f: BinaryIO):
        pos = f.tell()

        prim = cls()
        print(f"IMD | WARNING: Encountered unimplemented Prim type {hex(prim.type)}")
        
        f.seek(pos)

        return prim
