from __future__ import annotations

import copy
from typing import TextIO

from imd import (
    IMD, 
    IMDPrimGroup, # 01
    IMDPrim0x2, # 02
    IMDPrimTransformState, # 10
    IMDPrim0x13, # 13
    IMDPrimVertexColor, # 20
    IMDPrimTexture, # 21
    IMDPrimVertexPool, # 48
    IMDPrimVertexPoolWithRGBA, # 49
    Vertex0x49,
)
from util import Color4, Vec4

# Various constants yadayada
COORDINATE_SYSTEM = "Z-up"
INDENT_AMOUNT = 2

def _write_with_indent(output_file: TextIO, msg: str, indent: int):
    output_file.write(" " * indent + msg)

class Egg:

    @staticmethod
    def from_imd(imd: IMD, output_file: TextIO) -> None:

        # intro comment
        output_file.write("<Comment> { Converted by IMD2egg }\n\n")

        # coordinate system
        output_file.write(f"<CoordinateSystem> {{ {COORDINATE_SYSTEM} }}\n\n")

        # Write textures
        textures = imd.get_all_textures()
        for texture in textures:
            Egg._write_texture(output_file, texture)

        # Write groups
        for i, group in enumerate(imd.get_all_groups()):
            Egg._write_group(output_file, group, str(i))
        

    @staticmethod
    def _write_texture(output_file: TextIO, texture: IMDPrimTexture, indent: int = 0):
        texture_id = texture.texture_id
        texture_path = f"TEX/{texture_id}.png"

        _write_with_indent(output_file, f"<Texture> {texture_id} {{\n", indent)
        indent += INDENT_AMOUNT

        _write_with_indent(output_file, f"\"{texture_path}\"\n", indent)

        # TODO: Write any texture scalars here

        indent -= INDENT_AMOUNT
        _write_with_indent(output_file, "}", indent)
        output_file.write("\n\n")

    @staticmethod
    def _write_group(output_file: TextIO, group: IMDPrimGroup, group_name: str, indent: int = 0):
        EggGroup(group, group_name).write(output_file, indent)

    @staticmethod
    def convert_imd_coordinates(vec: Vec4):
        # NOTE: IMD's Up is Y-down
        vec = copy.copy(vec)
        match COORDINATE_SYSTEM:
            case "Z-up":
                vec.x, vec.y, vec.z = vec.x, vec.z, -vec.y
            case _:
                raise RuntimeError("Unsupported .egg coordinate system")
        return vec

class EggGroup:
    # user properties
    name: str
    # internal
    prim_group: IMDPrimGroup
    indent: int
    output_file: TextIO | None
    __num_vertex_pools: int # bit of a hack just to ensure unique vertex pool names for now
    # model properties
    vertex_rgba: Color4
    texture_id: int

    # TODO: Reordering egg groups later to nest them before writing them
    parent_group_id: int
    children: list[EggGroup]

    def __init__(self, prim_group: IMDPrimGroup, name: str) -> None:
        self.name = name
        self.prim_group = prim_group
        self.indent = 0
        self.output_file = None
        self.__num_vertex_pools = 0
        self.vertex_rgba = Color4(1.0, 1.0, 1.0, 1.0)
        self.texture_id = -1
        self.parent_group_id = -1
        self.children = []

    def write(self, output_file: TextIO, indent: int = 0) -> None:
        self.indent = indent
        self.output_file = output_file

        _write_with_indent(output_file, f"<Group> {self.name} {{\n", self.indent)
        self.indent += INDENT_AMOUNT

        for prim in self.prim_group.get_prims():
            match prim.type:
                case 0x01:
                    assert isinstance(prim, IMDPrimGroup)
                    self.__proc_prim_group(prim)
                case 0x02:
                    assert isinstance(prim, IMDPrim0x2)
                    self.__proc_prim_02(prim)
                case 0x10:
                    assert isinstance(prim, IMDPrimTransformState)
                    self.__proc_prim_transform_state(prim)
                case 0x13:
                    assert isinstance(prim, IMDPrim0x13)
                    self.__proc_prim_13(prim)
                case 0x20:
                    assert isinstance(prim, IMDPrimVertexColor)
                    self.__proc_prim_vertex_color(prim)
                case 0x21:
                    assert isinstance(prim, IMDPrimTexture)
                    self.__proc_prim_texture(prim)
                case 0x48:
                    assert isinstance(prim, IMDPrimVertexPool)
                    self.__proc_prim_vertex_pool(prim)
                case 0x49:
                    assert isinstance(prim, IMDPrimVertexPoolWithRGBA)
                    self.__proc_prim_vertex_pool(prim)
                case _:
                    print(f"EggGroup: Unknown prim type {hex(prim.type)}")

        self.indent -= INDENT_AMOUNT
        _write_with_indent(output_file, "}\n", indent)

        self.output_file = None

    def __proc_prim_group(self, prim_group: IMDPrimGroup):
        raise RuntimeError("Nested PrimGroup unsupported")

    def __proc_prim_02(self, prim: IMDPrim0x2):
        pass

    def __proc_prim_transform_state(self, prim: IMDPrimTransformState):
        pass
    
    def __proc_prim_13(self, prim: IMDPrim0x13):
        pass

    def __proc_prim_vertex_color(self, prim: IMDPrimVertexColor):
        self.vertex_rgba = prim.color_scale

    def __proc_prim_texture(self, prim: IMDPrimTexture):
        self.texture_id = prim.texture_id

    def __proc_prim_vertex_pool(self, prim: IMDPrimVertexPool):
        assert self.output_file is not None
        pool_name = f"{self.name}_{self.__num_vertex_pools}.verts"
        _write_with_indent(self.output_file, f"<VertexPool> {pool_name} {{\n", self.indent)
        self.indent += INDENT_AMOUNT

        for i, vertex in enumerate(prim.vertices):
            vec = Egg.convert_imd_coordinates(vertex.position)
            _write_with_indent(self.output_file, f"<Vertex> {i} {{ {vec.x} {vec.y} {vec.z}\n", self.indent)
            self.indent += INDENT_AMOUNT
            _write_with_indent(self.output_file, f"<UV> {{ {vertex.u} {vertex.v} }}\n", self.indent)
            if isinstance(prim, IMDPrimVertexPoolWithRGBA):
                assert isinstance(vertex, Vertex0x49)
                c = vertex.color
                _write_with_indent(self.output_file, f"<RGBA> {{ {c.r} {c.g} {c.b} {c.a} }}\n", self.indent)
            self.indent -= INDENT_AMOUNT
            _write_with_indent(self.output_file, "}\n", self.indent)
        self.indent -= INDENT_AMOUNT
        _write_with_indent(self.output_file, "}\n", self.indent)

        # TODO: How do these vertices connect together...?
        # NOTE: These are probably always triangle strips...
        r, g, b, a = self.vertex_rgba
        for i in range(0, len(prim.vertices)-2):
            # Skip this polygon if the last vertex doesn't close it
            if prim.vertices[i+2].vertex_order == 0:
                continue

            _write_with_indent(self.output_file, f"<Polygon> {{\n", self.indent)
            self.indent += INDENT_AMOUNT
            if self.texture_id != -1:
                _write_with_indent(self.output_file, f"<TRef> {{ {self.texture_id} }}\n", self.indent)
            _write_with_indent(self.output_file, f"<RGBA> {{ {r} {g} {b} {a} }}\n", self.indent)
            _write_with_indent(self.output_file, f"<BFace> {{ 0 }}\n", self.indent)
            if prim.vertices[i+2].vertex_order > 0:
                _write_with_indent(self.output_file, f"<VertexRef> {{ {i+2} {i+1} {i+0} <Ref> {{ {pool_name} }} }}\n", self.indent)
            else:
                _write_with_indent(self.output_file, f"<VertexRef> {{ {i+0} {i+1} {i+2} <Ref> {{ {pool_name} }} }}\n", self.indent)
            self.indent -= INDENT_AMOUNT
            _write_with_indent(self.output_file, "}\n", self.indent)

        self.__num_vertex_pools += 1

        # NOTE: Seemingly when a vertex pool is exhausted, the previously used texture is cleared.
        # I'm not sure exactly if this affects other properties such as vertex color or not at this time.
        # If we don't clear the texture ID, then triangles such as Geo's ring won't properly render
        # as they are erroneously using his eye texture.
        self.texture_id = -1
