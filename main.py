import sys

from imd import IMD

file_path = "TEST.IMD"

imd_file = None
try:
    imd_file = open(file_path, "rb")
except OSError:
    print(f"ERROR: Could not open \"{file_path}\" as file!")
    sys.exit(1)

imd = IMD.from_file(imd_file)
imd_file.close()

pass
