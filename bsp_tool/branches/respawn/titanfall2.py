import enum
import io
import struct

from .. import base
from . import titanfall


BSP_VERSION = 37

# https://developer.valvesoftware.com/wiki/Source_BSP_File_Format/Game-Specific#Titanfall
# TitanFall|2 has b"rBSP" file-magic and 128 lumps
# ~72 of the 128 lumps appear in .bsp_lump files
# the naming convention for these files is: "<bsp.filename>.<LUMP_HEX_ID>.bsp_lump"
# where <LUMP_HEX_ID> is a lowercase four digit hexadecimal string
# e.g. mp_drydock.004a.bsp_lump (Lump #74: VertexUnlitTS)
# entities are stored across 5 different .ent files per .bsp
# the 5 files are: env, fx, script, snd, spawn
# e.g. mp_drydock_env.ent
# presumably all this file splitting has to do with streaming data into memory


class LUMP(enum.Enum):
    ENTITIES = 0x0000
    PLANES = 0x0001
    TEXDATA = 0x0002
    VERTICES = 0x0003
    LIGHTPROBE_PARENT_INFOS = 0x0004
    SHADOW_ENVIRONMENTS = 0x0005
    LIGHTPROBE_BSP_NODES = 0x0006
    LIGHTPROBE_BSP_REF_IDS = 0x0007
    UNUSED_8 = 0x0008
    UNUSED_9 = 0x0009
    UNUSED_10 = 0x000A
    UNUSED_11 = 0x000B
    UNUSED_12 = 0x000C
    UNUSED_13 = 0x000D
    MODELS = 0x000E
    UNUSED_15 = 0x000F
    UNUSED_16 = 0x0010
    UNUSED_17 = 0x0011
    UNUSED_18 = 0x0012
    UNUSED_19 = 0x0013
    UNUSED_20 = 0x0014
    UNUSED_21 = 0x0015
    UNUSED_22 = 0x0016
    UNUSED_23 = 0x0017
    ENTITY_PARTITIONS = 0x0018
    UNUSED_25 = 0x0019
    UNUSED_26 = 0x001A
    UNUSED_27 = 0x001B
    UNUSED_28 = 0x001C
    PHYSICSCOLLIDE = 0x001D
    VERTEX_NORMALS = 0x001E
    UNUSED_31 = 0x001F
    UNUSED_32 = 0x0020
    UNUSED_33 = 0x0021
    UNUSED_34 = 0x0022
    GAME_LUMP = 0x0023
    LEAF_WATERDATA = 0x0024  # unused
    UNUSED_37 = 0x0025
    UNUSED_38 = 0x0026
    UNUSED_39 = 0x0027
    PAKFILE = 0x0028  # zip file, contains cubemaps
    UNUSED_41 = 0x0029
    CUBEMAPS = 0x002A
    TEXDATA_STRING_DATA = 0x002B
    TEXDATA_STRING_TABLE = 0x002C
    UNUSED_45 = 0x002D
    UNUSED_46 = 0x002E
    UNUSED_47 = 0x002F
    UNUSED_48 = 0x0030
    UNUSED_49 = 0x0031
    UNUSED_50 = 0x0032
    UNUSED_51 = 0x0033
    UNUSED_52 = 0x0034
    UNUSED_53 = 0x0035
    WORLDLIGHTS = 0x0036
    WORLDLIGHTS_PARENT_INFO = 0x0037
    UNUSED_56 = 0x0038
    UNUSED_57 = 0x0039
    UNUSED_58 = 0x003A
    UNUSED_59 = 0x003B
    UNUSED_60 = 0x003C
    UNUSED_61 = 0x003D
    PHYSICSLEVEL = 0x003E  # length 0, version 6?
    UNUSED_63 = 0x003F
    UNUSED_64 = 0x0040
    UNUSED_65 = 0x0041
    TRICOLL_TRIS = 0x0042
    UNUSED_67 = 0x0043
    TRICOLL_NODES = 0x0044
    TRICOLL_HEADERS = 0x0045
    PHYSTRIS = 0x0046  # unused
    VERTS_UNLIT = 0x0047        # VERTS_RESERVED_0
    VERTS_LIT_FLAT = 0x0048     # VERTS_RESERVED_1  # unused?
    VERTS_LIT_BUMP = 0x0049     # VERTS_RESERVED_2
    VERTS_UNLIT_TS = 0x004A     # VERTS_RESERVED_3
    VERTS_BLINN_PHONG = 0x004B  # VERTS_RESERVED_4  # unused
    VERTS_RESERVED_5 = 0x004C  # unused
    VERTS_RESERVED_6 = 0x004D  # unused
    VERTS_RESERVED_7 = 0x004E  # unused
    MESH_INDICES = 0x004F
    MESHES = 0x0050
    MESH_BOUNDS = 0x0051
    MATERIAL_SORT = 0x0052
    LIGHTMAP_HEADERS = 0x0053
    LIGHTMAP_DATA_DXT5 = 0x0054  # unused
    CM_GRID = 0x0055
    CM_GRIDCELLS = 0x0056
    CM_GEO_SETS = 0x0057
    CM_GEO_SET_BOUNDS = 0x0058
    CM_PRIMS = 0x0059
    CM_PRIM_BOUNDS = 0x005A
    CM_UNIQUE_CONTENTS = 0x005B
    CM_BRUSHES = 0x005C
    CM_BRUSH_SIDE_PLANE_OFFSETS = 0x005D
    CM_BRUSH_SIDE_PROPS = 0x005E
    CM_BRUSH_TEX_VECS = 0x005F
    TRICOLL_BEVEL_STARTS = 0x0060
    TRICOLL_BEVEL_INDICES = 0x0061
    LIGHTMAP_DATA_SKY = 0x0062
    CSM_AABB_NODES = 0x0063
    CSM_OBJ_REFS = 0x0064
    LIGHTPROBES = 0x0065
    STATIC_PROP_LIGHTPROBE_INDEX = 0x0066
    LIGHTPROBE_TREE = 0x0067
    LIGHTPROBE_REFS = 0x0068
    LIGHTMAP_DATA_REAL_TIME_LIGHTS = 0x0069
    CELL_BSP_NODES = 0x006A
    CELLS = 0x006B
    PORTALS = 0x006C
    PORTAL_VERTS = 0x006D
    PORTAL_EDGES = 0x006E
    PORTAL_VERT_EDGES = 0x006F
    PORTAL_VERT_REFS = 0x0070
    PORTAL_EDGE_REFS = 0x0071
    PORTAL_EDGE_ISECT_EDGE = 0x0072
    PORTAL_EDGE_ISECT_AT_VERT = 0x0073
    PORTAL_EDGE_ISECT_HEADER = 0x0074
    OCCLUSION_MESH_VERTS = 0x0075
    OCCLUSION_MESH_INDICES = 0x0076
    CELL_AABB_NODES = 0x0077
    OBJ_REFS = 0x0078
    OBJ_REF_BOUNDS = 0x0079
    LIGHTMAP_DATA_REAL_TIME_LIGHT_PAGE = 0x007A
    LEVEL_INFO = 0x007B
    SHADOW_MESH_OPAQUE_VERTS = 0x007C
    SHADOW_MESH_ALPHA_VERTS = 0x007D
    SHADOW_MESH_INDICES = 0x007E
    SHADOW_MESH_MESHES = 0x007F


lump_header_address = {LUMP_ID: (16 + i * 16) for i, LUMP_ID in enumerate(LUMP)}


# classes for lumps (alphabetical order) [X / 128] + 2 special lumps (54 unused)
class StaticPropv13(base.Struct):  # sprp GAME_LUMP (0023)
    # definition worked out by BobtheBob
    # Vector          origin;
    # Vector          angles;
    # char            unknown_1[4];
    # unsigned short  mdl_name;
    # unsigned char   solid_mode;
    # unsigned char   flags;
    # /* uncertain past this point */
    # char            unknown_2[4];
    # float           forced_fade_scale;
    # Vector          lighting_origin;
    # char            cpu_level.min;           // usually -1
    # char            cpu_level.max;
    # char            gpu_level.min;
    # char            gpu_level.max;
    # color32         diffuse_modulation;      // this seems to really always just be 0000
    # unsigned short  collision_flags.add;     // new!
    # unsigned short  collision_flags.remove;  // new!
    __slots__ = ["origin", "angles", "unknown_1", "mdl_name", "solid_mode", "flags",
                 "unknown_2", "forced_fade_scale", "lighting_origin", "cpu_level",
                 "gpu_level", "diffuse_modulation", "collision_flags"]
    _format = "6f4bH2B4b4f8b2H"  # 64 bytes
    _arrays = {"origin": [*"xyz"], "angles": [*"yzx"], "unknown_1": 4, "unknown_2": 4,
               "lighting_origin": [*"xyz"], "cpu_level": ["min", "max"],
               "gpu_level": ["min", "max"], "diffuse_modulation": [*"rgba"],
               "collision_flags": ["add", "remove"]}


# special vertices
class VertexBlinnPhong(base.Struct):  # LUMP 75 (004B)
    __slots__ = ["position_index", "normal_index", "unknown"]
    _format = "4I"  # 16 bytes
    _arrays = {"unknown": [*"ab"]}


# classes for special lumps (alphabetical order)
class GameLump_SPRP:  # unique to Titanfall|2
    def __init__(self, raw_sprp_lump: bytes, StaticPropClass: object):
        self._static_prop_format = StaticPropClass._format
        sprp_lump = io.BytesIO(raw_sprp_lump)
        mdl_name_count = int.from_bytes(sprp_lump.read(4), "little")
        mdl_names = struct.iter_unpack("128s", sprp_lump.read(128 * mdl_name_count))
        setattr(self, "mdl_names", [t[0].replace(b"\0", b"").decode() for t in mdl_names])
        prop_count, unknown1, unknown2 = struct.unpack("3i", sprp_lump.read(12))
        self.unknown1, self.unknown2 = unknown1, unknown2
        prop_size = struct.calcsize(StaticPropClass._format)
        props = struct.iter_unpack(StaticPropClass._format, sprp_lump.read(prop_count * prop_size))
        setattr(self, "props", list(map(StaticPropClass, props)))
        # TODO: check if are there any leftover bytes at the end?

    def as_bytes(self) -> bytes:
        return b"".join([int.to_bytes(len(self.prop_names), 4, "little"),
                         *[struct.pack("128s", n) for n in self.prop_names],
                         int.to_bytes(len(self.leafs), 4, "little"),
                         *[struct.pack("H", L) for L in self.leafs],
                         *struct.pack("3I", len(self.props), self.unknown1, self.unknown2),
                         *[struct.pack(self._static_prop_format, *p.flat()) for p in self.props]])


# {"LUMP_NAME": {version: LumpClass}}
BASIC_LUMP_CLASSES = titanfall.BASIC_LUMP_CLASSES.copy()

LUMP_CLASSES = titanfall.LUMP_CLASSES.copy()
LUMP_CLASSES.update({"VERTS_BLINN_PHONG": {0: VertexBlinnPhong}})

SPECIAL_LUMP_CLASSES = titanfall.SPECIAL_LUMP_CLASSES.copy()

GAME_LUMP_CLASSES = {"sprp": {13: lambda raw_lump: GameLump_SPRP(raw_lump, StaticPropv13)}}

# branch exclusive methods, in alphabetical order:
methods = [*titanfall.methods]
