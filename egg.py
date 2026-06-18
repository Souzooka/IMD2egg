from __future__ import annotations

from typing import TextIO

from imd import IMD, IMDPrimTexture
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

        textures = imd.get_all_textures()
        for texture in textures:
            Egg._write_texture(output_file, texture)

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
    def _convert_imd_coordinates(vec: Vec4):
        # NOTE: IMD's Up is Y-down
        match COORDINATE_SYSTEM:
            case "Z-up":
                vec.y, vec.z = vec.z, -vec.y
            case _:
                raise RuntimeError("Unsupported .egg coordinate system")
            
    @staticmethod
    def _write_with_indent(output_file: TextIO, msg: str, indent: int):
        output_file.write(" " * indent + msg)
