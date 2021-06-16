#include <cstdio>
#include <filesystem>  // -std=c++17
#include <fstream>
#include <string>


namespace fs = std::filesystem;

namespace bsp_tool {

    // Bsp base class; gives an interface to read the .bsp file
    template<typename LumpHeaderStruct, int lump_count>
    class Bsp {
        public:
            std::fstream      _file;
            std::string       filename;
            int               format_version;
            LumpHeaderStruct  headers[lump_count];

            // NOTE: _read requires x to be initialised; as a result, x cannot be initialised with _read.
            template<typename T>
            void _read(T* x) { this->_file.read((char*) x, sizeof(*x)); };

            Bsp(const char filename[]) {
                this->filename = filename;
                this->_file.open(filename, std::ios::in | std::ios::binary);
                if (!this->_file) {
                    throw std::runtime_error("could not find .bsp file"); }
            };

            ~Bsp() {};

            // Vertex vertices[] = some_bsp::getLump<Vertex>(LUMP::VERTICES);
            // char raw_lump[] = some_bsp::getLump<char>(LUMP::VERTICES);
            template<typename T>
            T* getLump(int LUMP_index) {
                T* lump_entries;
                LumpHeaderStruct header = this->headers[LUMP_index];
                this->_file.seekg(header.offset, std::ios::beg);
                this->_file.read((char*) &lump_entries, header.length);
                return lump_entries;
            };

            // Vertex v; v = some_bsp::getLumpEntry<Vertex>(LUMP::VERTICES, 0);
            // char raw_snippet[1024]; raw_snippet = some_bsp::getLumpEntry<char>(LUMP::VERTICES, 0);
            template <typename T>
            T getLumpEntry(int LUMP_index, int entry_index) {
                T lump_entry;
                LumpHeaderStruct header = this->headers[LUMP_index];
                this->_file.seekg(header.offset + (sizeof(T) * entry_index), std::ios::beg);
                this->_read(&lump_entry);
                return lump_entry;
            };
    };


    namespace id_software {
        const int FILE_MAGIC = ('I' + ('B' << 8) + ('S' << 16) + ('P' << 24));
        struct LumpHeader { int offset, length; };

        class IdTechBsp : public Bsp<LumpHeader, 17> {
            public:
                using BspBaseClass = Bsp<LumpHeader, 17>;

                IdTechBsp(const char filename[]) : BspBaseClass(filename) {
                    this->_file.seekg(0, std::ios::beg);
                    int file_magic; this->_read(&file_magic);
                    if (file_magic != FILE_MAGIC) {
                        throw std::runtime_error("unexpected file magic for IBSP"); }
                    this->_read(&this->format_version);
                    this->_read(&this->headers);
                };

                ~IdTechBsp() {};
        };

        namespace quake {
            const int BSP_VERSION = 46;
            namespace LUMP {
                int ENTITIES     = 0,  VERTICES      = 10,
                    TEXTURES     = 1,  MESH_VERTICES = 11,
                    PLANES       = 2,  EFFECTS       = 12,
                    NODES        = 3,  FACES         = 13,
                    LEAVES       = 4,  LIGHTMAPS     = 14,
                    LEAF_FACES   = 5,  LIGHT_VOLUMES = 15,
                    LEAF_BRUSHES = 6,  VIS_DATA      = 16,
                    MODELS       = 7,
                    BRUSHES      = 8,
                    BRUSH_SIDES  = 9;
            }
        }
    }


    namespace valve_software {
        const int FILE_MAGIC = ('V' + ('B' << 8) + ('S' << 16) + ('P' << 24));
        struct LumpHeader { int offset, length, version, uncompressed_size; };

        // VBSP .bsp files have many variants
        // https://developer.valvesoftware.com/wiki/Source_BSP_File_Format
        // https://developer.valvesoftware.com/wiki/Source_BSP_File_Format/Game-Specific
        class ValveBsp : public Bsp<LumpHeader, 64> {
            public:
                int revision;

                using BspBaseClass = Bsp<LumpHeader, 64>;

                ValveBsp(const char filename[]) : BspBaseClass(filename) {
                    this->_file.seekg(0, std::ios::beg);
                    int file_magic = 0; this->_read(&file_magic);
                    if (file_magic != FILE_MAGIC) {
                        throw std::runtime_error("unexpected file magic for VBSP"); }
                    this->_read(&this->format_version);
                    this->_read(&this->headers);
                    this->_read(&this->revision);
                };

                ~ValveBsp() {};
        };


        namespace orange_box {
            const int BSP_VERSION = 20;
            namespace LUMP {
                int ENTITIES              =  0,  DISPLACEMENT_LIGHTMAP_ALPHAS          = 32,
                    PLANES                =  1,  DISPLACEMENT_VERTICES                 = 33,
                    TEXDATA               =  2,  DISPLACEMENT_LIGHTMAP_SAMPLE_POSITION = 34,
                    VERTICES              =  3,  GAME_LUMP                             = 35,
                    VISIBILITY            =  4,  LEAF_WATER_DATA                       = 36,
                    NODES                 =  5,  PRIMITIVES                            = 37,
                    TEXINFO               =  6,  PRIMITIVE_VERTICIES                   = 38,
                    FACES                 =  7,  PRIMITIVE_INDICES                     = 39,
                    LIGHTING              =  8,  PAKFILE                               = 40,
                    OCCLUSION             =  9,  CLIP_PORTAL_VERTICES                  = 41,
                    LEAVES                = 10,  CUBEMAPS                              = 42,
                    FACE_IDS              = 11,  TEXDATA_STRING_DATA                   = 43,
                    EDGES                 = 12,  TEXDATA_STRING_TABLE                  = 43,
                    SURFEDGES             = 13,  OVERLAYS                              = 45,
                    MODELS                = 14,  LEAF_MIN_DIST_TO_WATER                = 46,
                    WORLD_LIGHTS          = 15,  FACE_MACRO_TEXTURE_INFO               = 47,
                    LEAF_FACES            = 16,  DISPLACEMENT_TRIANGLES                = 48,
                    LEAF_BRUSHES          = 17,  PHYSICS_COLLIDE_SURFACE               = 49,
                    BRUSHES               = 18,  WATER_OVERLAYS                        = 50,
                    BRUSH_SIDES           = 19,  LEAF_AMBIENT_INDEX_HDR                = 51,
                    AREAS                 = 20,  LEAF_AMBIENT_INDEX                    = 52,
                    AREA_PORTALS          = 21,  LIGHTING_HDR                          = 53,
                    UNUSED_22             = 22,  WORLD_LIGHTS_HDR                      = 54,
                    UNUSED_23             = 23,  LEAF_AMBIENT_LIGHTING_HDR             = 55,
                    UNUSED_24             = 24,  LEAF_AMBIENT_LIGHTING                 = 56,
                    UNUSED_25             = 25,  XZIP_PAKFILE                          = 57,
                    DISPLACEMENT_INFO     = 26,  FACES_HDR                             = 58,
                    ORIGINAL_FACES        = 27,  MAP_FLAGS                             = 59,
                    PHYSICS_DISPLACEMENT  = 28,  OVERLAY_FADES                         = 60,
                    PHYSICS_COLLIDE       = 29,  UNUSED_61                             = 61,
                    VERTEX_NORMALS        = 30,  UNUSED_62                             = 62,
                    VERTEX_NORMAL_INDICES = 31,  UNUSED_63                             = 63;
            }
        }
    }


    namespace respawn_entertainment {
        const int FILE_MAGIC = ('r' + ('B' << 8) + ('S' << 16) + ('P' << 24));
        struct LumpHeader { int offset, length, version, uncompressed_size; };

        class RespawnBsp : public Bsp<LumpHeader, 128> {
            public:
                std::fstream _external[128];
                int revision;

                using BspBaseClass = Bsp<LumpHeader, 128>;

                RespawnBsp(const char filename[]) : BspBaseClass(filename) {
                    this->_file.seekg(0, std::ios::beg);
                    int file_magic, lump_count; this->_read(&file_magic);
                    if (file_magic != FILE_MAGIC) {
                        throw std::runtime_error("unexpected file magic for rBSP"); }
                    this->_read(&this->format_version);
                    this->_read(&this->revision);
                    this->_read(&lump_count);
                    if (lump_count != 127) {
                        throw std::runtime_error("rBSP header does not contain '127'"); }
                    this->_read(&this->headers);
                    /* load external .bsp_lump files */
                    fs::path bsp_lump(".bsp_lump"), bsp_path(filename), current_file;
                    int LUMP_index; std::string LUMP_hex_index;
                    for (auto file : fs::directory_iterator(bsp_path.parent_path())) {
                        current_file = file.path();
                        if (current_file.extension() == bsp_lump) {
                            if (current_file.stem().stem() == bsp_path.filename()) {
                                LUMP_hex_index = current_file.stem().extension().string();
                                LUMP_index = std::stoi(LUMP_hex_index.substr(1, std::string::npos), 0, 16);
                                this->_external[LUMP_index] = std::fstream(current_file.string());
                            }
                        }
                    }
                };

                ~RespawnBsp() {};

                // Vertex v[] = some_bsp::getExternalLump<Vertex>(LUMP::VERTICES);
                // char raw_lump[] = some_bsp::getExternalLump<char>(LUMP::VERTICES);
                template<typename T>
                T* getExternalLump(int LUMP_index) {
                    T* lump_entries;
                    std::fstream external_lump = this->_external[LUMP_index];
                    external_lump.seekg(0, std::ios::beg);
                    external_lump >> lump_entries;
                    return lump_entries;
                };

                // Vertex v = some_bsp::getExternalLumpEntry<Vertex>(LUMP::VERTICES, 0);
                // char raw_snippet[1024] = some_bsp::getExternalLumpEntry<char>(LUMP::VERTICES, 0);
                template <typename T>
                T getExternalLumpEntry(int LUMP_index, int entry_index) {
                    T lump_entry;
                    std::fstream external_lump = this->_external[LUMP_index];
                    external_lump.seekg(sizeof(T) * entry_index, std::ios::beg);
                    external_lump.read((char*) &lump_entry, sizeof(T));
                    return lump_entry;
                };
        };


        namespace titanfall {
            const int BSP_VERSION = 29;
            namespace LUMP {
                int ENTITIES               = 0x00,  UNUSED_64                           = 0x40,
                    PLANES                 = 0x01,  UNUSED_65                           = 0x41,
                    TEXDATA                = 0x02,  TRICOLL_TRIS                        = 0x42,
                    VERTICES               = 0x03,  UNUSED_67                           = 0x43,
                    UNUSED_04              = 0x04,  TRICOLL_NODES                       = 0x44,
                    UNUSED_05              = 0x05,  TRICOLL_HEADERS                     = 0x45,
                    UNUSED_06              = 0x06,  PHYSICS_TRIANGLES                   = 0x46,
                    UNUSED_07              = 0x07,  VERTS_UNLIT                         = 0x47,
                    UNUSED_08              = 0x08,  VERTS_LIT_FLAT                      = 0x48,
                    UNUSED_09              = 0x09,  VERTS_LIT_BUMP                      = 0x49,
                    UNUSED_10              = 0x0A,  VERTS_UNLIT_TS                      = 0x4A,
                    UNUSED_11              = 0x0B,  VERTS_RESERVED_4                    = 0x4B,
                    UNUSED_12              = 0x0C,  VERTS_RESERVED_5                    = 0x4C,
                    UNUSED_13              = 0x0D,  VERTS_RESERVED_6                    = 0x4D,
                    MODELS                 = 0x0E,  VERTS_RESERVED_7                    = 0x4E,
                    UNUSED_15              = 0x0F,  MESH_INDICES                        = 0x4F,
                    UNUSED_16              = 0x10,  MESHES                              = 0x50,
                    UNUSED_17              = 0x11,  MESH_BOUNDS                         = 0x51,
                    UNUSED_18              = 0x12,  MATERIAL_SORT                       = 0x52,
                    UNUSED_19              = 0x13,  LIGHTMAP_HEADERS                    = 0x53,
                    UNUSED_20              = 0x14,  LIGHTMAP_DATA_DXT5                  = 0x54,
                    UNUSED_21              = 0x15,  CM_GRID                             = 0x55,
                    UNUSED_22              = 0x16,  CM_GRID_CELLS                       = 0x56,
                    UNUSED_23              = 0x17,  CM_GEO_SETS                         = 0x57,
                    ENTITY_PARTITIONS      = 0x18,  CM_GEO_SET_BOUNDS                   = 0x58,
                    UNUSED_25              = 0x19,  CM_PRIMITIVES                       = 0x59,
                    UNUSED_26              = 0x1A,  CM_PRIMITIVE_BOUNDS                 = 0x5A,
                    UNUSED_27              = 0x1B,  CM_UNIQUE_CONTENTS                  = 0x5B,
                    UNUSED_28              = 0x1C,  CM_BRUSHES                          = 0x5C,
                    PHYSICS_COLLIDE        = 0x1D,  CM_BRUSH_SIDE_PLANE_OFFSETS         = 0x5D,
                    VERTEX_NORMALS         = 0x1E,  CM_BRUSH_SIDE_PROPS                 = 0x5E,
                    UNUSED_31              = 0x1F,  CM_BRUSH_TEX_VECS                   = 0x5F,
                    UNUSED_32              = 0x20,  TRICOLL_BEVEL_STARTS                = 0x60,
                    UNUSED_33              = 0x21,  TRICOLL_BEVEL_INDICES               = 0x61,
                    UNUSED_34              = 0x22,  LIGHTMAP_DATA_SKY                   = 0x62,
                    GAME_LUMP              = 0x23,  CSM_AABB_NODES                      = 0x63,
                    LEAF_WATER_DATA        = 0x24,  CSM_OBJ_REFS                        = 0x64,
                    UNUSED_37              = 0x25,  LIGHTPROBES                         = 0x65,
                    UNUSED_38              = 0x26,  STATIC_PROP_LIGHTPROBE_INDEX        = 0x66,
                    UNUSED_39              = 0x27,  LIGHTPROBE_TREE                     = 0x67,
                    PAKFILE                = 0x28,  LIGHTPROBE_REFS                     = 0x68,
                    UNUSED_41              = 0x29,  LIGHTMAP_DATA_REAL_TIME_LIGHTS      = 0x69,
                    CUBEMAPS               = 0x2A,  CELL_BSP_NODES                      = 0x6A,
                    TEXDATA_STRING_DATA    = 0x2B,  CELLS                               = 0x6B,
                    TEXDATA_STRING_TABLE   = 0x2C,  PORTALS                             = 0x6C,
                    UNUSED_45              = 0x2D,  PORTAL_VERTS                        = 0x6D,
                    UNUSED_46              = 0x2E,  PORTAL_EDGES                        = 0x6E,
                    UNUSED_47              = 0x2F,  PORTAL_VERT_EDGES                   = 0x6F,
                    UNUSED_48              = 0x30,  PORTAL_VERT_REFS                    = 0x70,
                    UNUSED_49              = 0x31,  PORTAL_EDGE_REFS                    = 0x71,
                    UNUSED_50              = 0x32,  PORTAL_EDGE_ISECT_EDGE              = 0x72,
                    UNUSED_51              = 0x33,  PORTAL_EDGE_ISECT_AT_VERT           = 0x73,
                    UNUSED_52              = 0x34,  PORTAL_EDGE_ISECT_HEADER            = 0x74,
                    UNUSED_53              = 0x35,  OCCLUSION_MESH_VERTS                = 0x75,
                    WORLDLIGHTS            = 0x36,  OCCLUSION_MESH_INDICES              = 0x76,
                    WORLDLIGHT_PARENT_INFO = 0x37,  CELL_AABB_NODES                     = 0x77,
                    UNUSED_56              = 0x38,  OBJ_REFS                            = 0x78,
                    UNUSED_57              = 0x39,  OBJ_REF_BOUNDS                      = 0x79,
                    UNUSED_58              = 0x3A,  LIGHTMAP_DATA_REAL_TIME_LIGHTS_PAGE = 0x7A,
                    UNUSED_59              = 0x3B,  LEVEL_INFO                          = 0x7B,
                    UNUSED_60              = 0x3C,  SHADOW_MESH_OPAQUE_VERTS            = 0x7C,
                    UNUSED_61              = 0x3D,  SHADOW_MESH_ALPHA_VERTS             = 0x7D,
                    PHYSICS_LEVEL          = 0x3E,  SHADOW_MESH_INDICES                 = 0x7E,
                    UNUSED_63              = 0x3F,  SHADOW_MESH_MESHES                  = 0x7F;
            }
        }
    }


    /* Common Methods */

    /* Game Lump */
    struct GameLumpHeader { char id[4]; unsigned short flags, version; int offset, length; };

    // Gets the sub-headers in the internal game lumps of a bsp file
    template<typename BSPVariant>
    struct GameLumpHeader* getGameLumpHeaders(BSPVariant bsp) {
        bsp._file.seekg(bsp.headers[35].offset);  // NOTE: LUMP::GAME_LUMP is usually 35
        int game_lump_count;
        bsp._read(&game_lump_count);
        struct GameLumpHeader game_lump_headers[game_lump_count];
        bsp._read(&game_lump_headers);
        return game_lump_headers;
        // TODO: don't return the address of a local variable
    };

    // Gets the sub-headers in the external game lump of a RespawnBsp file
    struct GameLumpHeader* getExternalGameLumpHeaders(respawn_entertainment::RespawnBsp bsp) {
        int game_lump_count;
        bsp._external[35].seekg(0, std::ios::beg);
        bsp._external[35].read((char*) &game_lump_count, sizeof(game_lump_count));
        struct GameLumpHeader game_lump_headers[game_lump_count];
        bsp._external[35].read((char*) &game_lump_headers, sizeof(game_lump_headers));
        return game_lump_headers;
        // TODO: don't return the address of a local variable
    };
}