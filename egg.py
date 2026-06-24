from __future__ import annotations

import copy
from typing import TextIO

from imd import (
    IMD, 
    IMDObjModel, # 10
    IMDPrimGenericVertexPool,
    IMDPrimModelGroup, # 01
    IMDPrimModelTransformStateList, # 02
    IMDPrimTransformState, # 10
    IMDPrim0x13, # 13
    IMDPrimVertexColor, # 20
    IMDPrimTexture, # 21
    IMDPrimTextureAnimated, # 23
    #IMDPrimFloatVertexPool, # 40
    #IMDPrimFloatVertexPoolWithRGBA, # 41
    #IMDPrimShortVertexPool, # 48
    #IMDPrimShortVertexPoolWithRGBA, # 49
    IMDPrimDeformableVertexPool, # 58
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

        # Just process the first model object for now
        models = imd.get_all_objects_of_type(IMDObjModel)
        assert len(models) > 0
        Egg._proc_model(output_file, models[0])

    @staticmethod
    def _proc_model(output_file: TextIO, model: IMDObjModel):
        # Pre-process textures
        # TODO: Abstract this a little bit
        for prim in model.get_prims():
            for prim in prim.get_prims():
                if isinstance(prim, IMDPrimTexture):
                    Egg._write_texture(output_file, prim)

        # Write groups
        for i, tstate in enumerate(model.get_top_level_nodes()):
            Egg._write_group(output_file, tstate, str(i))

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
    def _write_group(output_file: TextIO, tstate: IMDPrimTransformState, group_name: str, indent: int = 0):
        EggGroup(tstate, group_name).write(output_file, indent)

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
    transform_state: IMDPrimTransformState
    indent: int
    output_file: TextIO | None
    __num_vertex_pools: int # bit of a hack just to ensure unique vertex pool names for now
    # model properties
    vertex_rgba: Color4
    texture_id: int

    # TODO: Reordering egg groups later to nest them before writing them
    parent_group_id: int
    children: list[EggGroup]

    def __init__(self, tstate: IMDPrimTransformState, name: str) -> None:
        self.name = name
        self.transform_state = tstate
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

        # For each transformation state, we have to write the groups associated with the state,
        # and its children. Since a transform state can have multiple groups which utilize it,
        # We'll keep this simple and just have lists of PandaNodes (with the states) and the
        # geometry under those nodes, e.g.:
        #
        #       P
        #      / \
        # G-G-G   P
        #        / \
        #     G-G   P 
        #
        # where P is a transformation state, and G is a node with geometry.

        # So, first, write the panda node for this state
        _write_with_indent(output_file, f"<Group> {self.name} {{\n", self.indent)
        self.indent += INDENT_AMOUNT
        # Insert our transformation state at the top
        self.__proc_prim_transform_state(self.transform_state)
        # Now write the groups with geometry here
        for i, group in enumerate(self.transform_state.groups):
            self.__write_group(output_file, group, f"{self.name}_geom_{i}")
        # Now write our children
        for i, tstate in enumerate(self.transform_state.children):
            EggGroup(tstate, f"{self.name}_{i}").write(output_file, self.indent)

        # and that's a wrap (hopefully)
        self.indent -= INDENT_AMOUNT
        _write_with_indent(output_file, "}\n", self.indent)

        self.output_file = None

    def __write_group(self, output_file: TextIO, prim_group: IMDPrimModelGroup, name: str):
        _write_with_indent(output_file, f"<Group> {name} {{\n", self.indent)
        self.indent += INDENT_AMOUNT

        for prim in prim_group.get_prims():
            match prim.type:
                case 0x01:
                    assert isinstance(prim, IMDPrimModelGroup)
                    self.__proc_prim_group(prim)
                case 0x02:
                    assert isinstance(prim, IMDPrimModelTransformStateList)
                    self.__proc_prim_02(prim)
                case 0x10:
                    assert isinstance(prim, IMDPrimTransformState)
                    pass # Should already be handled
                case 0x13:
                    assert isinstance(prim, IMDPrim0x13)
                    self.__proc_prim_13(prim)
                case 0x20:
                    assert isinstance(prim, IMDPrimVertexColor)
                    self.__proc_prim_vertex_color(prim)
                case 0x21:
                    assert isinstance(prim, IMDPrimTexture)
                    self.__proc_prim_texture(prim)
                case 0x23:
                    print("EGG | Warning: Implementing animated texture as static")
                    assert isinstance(prim, IMDPrimTextureAnimated)
                    self.__proc_prim_texture(prim)
                case 0x40 | 0x41 | 0x48 | 0x49:
                    assert isinstance(prim, IMDPrimGenericVertexPool)
                    self.__proc_prim_vertex_pool(prim)
                case 0x58:
                    assert isinstance(prim, IMDPrimDeformableVertexPool)
                    # TODO: We might want a separate processing function for this one
                    self.__proc_prim_vertex_pool(prim)
                case _:
                    print(f"EggGroup: Unknown prim type {hex(prim.type)}")

        self.indent -= INDENT_AMOUNT
        _write_with_indent(output_file, "}\n", self.indent)

    def __proc_prim_group(self, prim_group: IMDPrimModelGroup):
        raise RuntimeError("Nested PrimGroup unsupported")

    def __proc_prim_02(self, prim: IMDPrimModelTransformStateList):
        pass

    def __proc_prim_transform_state(self, prim: IMDPrimTransformState | None):
        assert self.output_file is not None
        if prim is None:
            return

        # NOTE: These type strings aren't documented in the egg syntax doc,
        # but possible strings are "axis", "point_eye", "point_world", and "point" (case-insensitive)
        # An axis billboard effect can be seen in the Survivor Compass model
        if prim.is_billboard:
            axis_type = "Point_eye"
            if prim.is_billboard_axis:
                axis_type = "Axis"
            _write_with_indent(self.output_file, f"<Billboard> {{ {axis_type} }}\n", self.indent)

        # TODO: The actual transformation matrix
    
    def __proc_prim_13(self, prim: IMDPrim0x13):
        pass

    def __proc_prim_vertex_color(self, prim: IMDPrimVertexColor):
        self.vertex_rgba = prim.color_scale

    def __proc_prim_texture(self, prim: IMDPrimTexture):
        self.texture_id = prim.texture_id

    def __proc_prim_vertex_pool(self, prim: IMDPrimGenericVertexPool | IMDPrimDeformableVertexPool):
        assert self.output_file is not None
        pool_name = f"{self.name}_{self.__num_vertex_pools}.verts"
        _write_with_indent(self.output_file, f"<VertexPool> {pool_name} {{\n", self.indent)
        self.indent += INDENT_AMOUNT

        # Write each vertex tag
        for i, vertex in enumerate(prim.vertices):
            vec = Egg.convert_imd_coordinates(vertex.position)
            _write_with_indent(self.output_file, f"<Vertex> {i} {{ {vec.x} {vec.y} {vec.z}\n", self.indent)
            self.indent += INDENT_AMOUNT
            # Scalars
            # Normal
            if prim.has_vertex_normals:
                normal = Egg.convert_imd_coordinates(vertex.normal)
                _write_with_indent(self.output_file, f"<Normal> {{ {normal[0]} {normal[1]} {normal[2]} }}\n", self.indent)
            # UV
            _write_with_indent(self.output_file, f"<UV> {{ {vertex.u} {vertex.v} }}\n", self.indent)
            # RGBA
            if vertex.rgba is not None:
                c = vertex.rgba
                _write_with_indent(self.output_file, f"<RGBA> {{ {c.r} {c.g} {c.b} {c.a} }}\n", self.indent)
            self.indent -= INDENT_AMOUNT
            _write_with_indent(self.output_file, "}\n", self.indent)
        self.indent -= INDENT_AMOUNT
        _write_with_indent(self.output_file, "}\n", self.indent)

        # These seem to always be triangle strips
        r, g, b, a = self.vertex_rgba
        for i in range(0, len(prim.vertices)-2):
            # Skip this polygon if the last vertex doesn't close it
            if prim.vertices[i+2].vertex_order == 0:
                continue

            _write_with_indent(self.output_file, f"<Polygon> {{\n", self.indent)
            self.indent += INDENT_AMOUNT
            # Scalars
            # Texture
            if self.texture_id != -1:
                _write_with_indent(self.output_file, f"<TRef> {{ {self.texture_id} }}\n", self.indent)
            # Normals
            if not prim.has_vertex_normals:
                normal = Egg.convert_imd_coordinates(prim.vertices[i+2].normal)
                _write_with_indent(self.output_file, f"<Normal> {{ {normal[0]} {normal[1]} {normal[2]} }}\n", self.indent)
            # RGBA
            _write_with_indent(self.output_file, f"<RGBA> {{ {r} {g} {b} {a} }}\n", self.indent)
            # Back face always seems to be false
            _write_with_indent(self.output_file, f"<BFace> {{ 0 }}\n", self.indent)
            # Vertex ordering is different based on a value immediately after where vertex position is stored
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
        # NOTE: Prim 0x58 seems to keep the last-used texture, sigh
        if not isinstance(prim, IMDPrimDeformableVertexPool):
            self.texture_id = -1
