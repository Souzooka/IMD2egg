from __future__ import annotations

import copy
from typing import TextIO

from imd import IMD, IMDPrimGroup, IMDPrimTexture, IMDPrimVertexPool
from util import Vec4

# Various constants yadayada
COORDINATE_SYSTEM = "Z-up"
INDENT_AMOUNT = 2


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

        Egg._write_with_indent(output_file, f"<Texture> {texture_id} {{\n", indent)
        indent += INDENT_AMOUNT

        Egg._write_with_indent(output_file, f"\"{texture_path}\"\n", indent)

        # TODO: Write any texture scalars here

        indent -= INDENT_AMOUNT
        Egg._write_with_indent(output_file, "}", indent)
        output_file.write("\n\n")

    @staticmethod
    def _write_group(output_file: TextIO, group: IMDPrimGroup, group_name: str, indent: int = 0):
        # Let's assume there's a texture in here...
        texture_id = 0
        for prim in group.get_prims():
            if isinstance(prim, IMDPrimTexture):
                texture_id = prim.texture_id
                break

        Egg._write_with_indent(output_file, f"<Group> {group_name} {{\n", indent)
        indent += INDENT_AMOUNT
        
        # I guess we'll just assume there's a vertex pool and write it for now
        for prim in group.get_prims():
            if isinstance(prim, IMDPrimVertexPool):
                Egg._write_vertex_pool(output_file, prim, f"{group_name}.verts", texture_id, indent)

        indent -= INDENT_AMOUNT
        Egg._write_with_indent(output_file, "}\n", indent)

    @staticmethod
    def _write_vertex_pool(output_file: TextIO, vertex_pool: IMDPrimVertexPool, pool_name: str, texture_id: int, indent: int = 0):
        Egg._write_with_indent(output_file, f"<VertexPool> {pool_name} {{\n", indent)
        indent += INDENT_AMOUNT

        for i, vertex in enumerate(vertex_pool.vertices):
            vec = Egg._convert_imd_coordinates(vertex.position)
            Egg._write_with_indent(output_file, f"<Vertex> {i} {{ {vec.x} {vec.y} {vec.z}\n", indent)
            indent += INDENT_AMOUNT
            Egg._write_with_indent(output_file, f"<UV> {{ {vertex.u} {vertex.v} }}\n", indent)
            indent -= INDENT_AMOUNT
            Egg._write_with_indent(output_file, "}\n", indent)
        indent -= INDENT_AMOUNT
        Egg._write_with_indent(output_file, "}\n", indent)

        # TODO: How do these vertices connect together...?
        # NOTE: These are probably always triangle strips...
        for i in range(0, len(vertex_pool.vertices)-2):
            Egg._write_with_indent(output_file, f"<Polygon> {{\n", indent)
            indent += INDENT_AMOUNT
            Egg._write_with_indent(output_file, f"<TRef> {{ {texture_id} }}\n", indent)
            Egg._write_with_indent(output_file, f"<RGBA> {{ 1.0 1.0 1.0 1.0 }}\n", indent)
            Egg._write_with_indent(output_file, f"<BFace> {{ 0 }}\n", indent)
            # Jank code to try and get more faces properly facing forward
            Egg._write_with_indent(output_file, f"<VertexRef> {{ {i+0} {i+1} {i+2} <Ref> {{ {pool_name} }} }}\n", indent)
            indent -= INDENT_AMOUNT
            Egg._write_with_indent(output_file, "}\n", indent)
        indent -= INDENT_AMOUNT

    @staticmethod
    def _convert_imd_coordinates(vec: Vec4):
        # NOTE: IMD's Up is Y-down
        vec = copy.copy(vec)
        match COORDINATE_SYSTEM:
            case "Z-up":
                vec.x, vec.y, vec.z = vec.x, -vec.z, -vec.y
            case _:
                raise RuntimeError("Unsupported .egg coordinate system")
        return vec
            
    @staticmethod
    def _write_with_indent(output_file: TextIO, msg: str, indent: int):
        output_file.write(" " * indent + msg)
