# www.gamedev.net/forums/topic/230012-eliminating-discontinuities-t-junctions-in-bsp/
# what impact would rewriting a bsp with fixed t-juncts have?
#
# source_sdk_2013/mp/src/utils/vbsp/writebsp.cpp
# source_sdk_2013/mp/src/utils/vbsp/map.cpp
#
# LUMP_PAKFILE is never compressed. ? really ?
# LUMP_GAME_LUMP is compressed in individual segments.
# The compressed size of a game lump can be determined by subtracting the
# current game lump's offset with that of the next entry. For this reason,
# the last game lump is always an empty dummy which only contains the offset.
# IMPLEMENT vmf_tool namespace class (visually cleaner attribute access)
#
# VIS: https://developer.valvesoftware.com/wiki/Source_BSP_File_Format#Visibility
# Areas lump (Lump 20) references the Areaportals lump (Lump 21) & is used with func_areaportal / func_areaportalwindow entities to define sections of the map that can be switched to render or not render.
# Portals (Lump 22), Clusters (Lump 23), PortalVerts (Lump 24), ClusterPortals (Lump 25), and ClipPortalVerts (Lump 41) lumps are used by the VVIS phase of the compile to ascertain which clusters can see which other clusters.
# A cluster is a player-enterable leaf volume in the map (see above). A "portal" is a polygon boundary between a cluster or leaf and an adjacent cluster or leaf.
# Most of this information is also used by the VRAD program to calculate static lighting, and then is removed from the bsp file
# CLUSTER LUMP VERY IMPORTANT
import collections
import enum
import itertools
import lzma
import struct
import time
import vector

import mods.tf2 as mod
#import invictus as mod
# which set to import is decided during import?

def read_lump(file, header_address):
    file.seek(header_address)
    offset = int.from_bytes(file.read(4), 'little')
    length = int.from_bytes(file.read(4), 'little')
    version = int.from_bytes(file.read(4), 'little')
    fourCC = int.from_bytes(file.read(4), 'little')
    if length != 0:
        if fourCC == 0:
            file.seek(offset)
            return file.read(length)
        else:
            file.seek(offset + 17) # SKIP lzma_header_t
            try:
                decompressed_lump = lzma.decompress(file.read(fourCC))
            except:
                raise RuntimeError(f'Error decompressing {lumpid.name}!')
            if len(decompressed_lump) != fourCC:
                raise RuntimeError(f'{lumpid.name} decompressed to {len(decompressed_lump)}, not {fourCC} as expected')
            else:
                return decompressed_lump

lump_header = collections.namedtuple('lump_header', ['offset', 'length' ,'version', 'fourCC'])

class bsp():
    def __init__(self, file):
        if not file.endswith('.bsp'):
            file += '.bsp'
        file.replace('\\', '/')
        split_file = file.rpartition('/')
        self.filename = split_file[-1]
        self.filepath = f'{split_file[0]}/'
        file = open(file, 'rb')
        if file.read(4) != b'VBSP':
            raise RuntimeError(f"{''.join(split_file)} is not a .bsp!")
        self.bytesize = len(file.read()) + 4
        self.lump_map = {}
        start_time = time.time()
        for ID in LUMP:
            data = read_lump(file, lump_address[ID])
            if data is not None:
                file.seek(lump_address[ID])
                self.lump_map[ID] = lump_header(*[int.from_bytes(file.read(4), 'little') for i in range(4)])
                setattr(self, 'RAW_' + ID.name, data)

        for LUMP, lump_class in mod.lump_classes:
            setattr(self, LUMP, [])
            RAW_LUMP = getattr(self, f"RAW_{LUMP}")
            for data in struct.iter_unpack(lump_class._format, RAW_LUMP):
                getattr(self, LUMP).append(lump_class(data))
            exec(f"del self.RAW_{LUMP}")

        file.close()
        unpack_time = time.time() - start_time
        print(f'Imported {self.filename} in {unpack_time:.2f} seconds')

    def verts_of(self, face): # why so many crazy faces?
        """vertex format [Position, Normal, TexCoord, LightCoord, Colour]"""
        texinfo = self.TEXINFO[face['texinfo']]
        texdata = self.TEXDATA[texinfo['texdata']]
        texvecs = texinfo['textureVecs']
        lightvecs = texinfo['lightmapVecs']
        verts, uvs, uv2s = [], [], []
        first_edge = face['firstedge']
        for surfedge in self.SURFEDGES[first_edge:first_edge + face['numedges']]:
            edge = self.EDGES[surfedge] if surfedge >= 0 else self.EDGES[-surfedge][::-1]
            verts.append(self.VERTICES[edge[0]])
            verts.append(self.VERTICES[edge[1]])
        #verts[::2] is faster. why is this approach used?
        # verts = [tuple(v) for v in verts]
        # verts = {v: None for v in verts}
        # verts = [list(v) for v in verts]
        verts = verts[::2]
        # github.com/VSES/SourceEngine2007/blob/master/src_main/engine/matsys_interface.cpp
        # SurfComputeTextureCoordinate & SurfComputeLightmapCoordinate
        for vert in verts:
            uv = [vector.dot(vert, texvecs[0][:-1]) + texvecs[0][3],
                  vector.dot(vert, texvecs[1][:-1]) + texvecs[1][3]]
            uv[0] /= texdata['view_width']
            uv[1] /= texdata['view_height']
            uvs.append(vector.vec2(*uv))
            uv2 = [vector.dot(vert, lightvecs[0][:-1]) + lightvecs[0][3],
                   vector.dot(vert, lightvecs[1][:-1]) + lightvecs[1][3]]
            uv2[0] -= face['LightmapTextureMinsinLuxels'][0]
            uv2[1] -= face['LightmapTextureMinsinLuxels'][1]
            try:
                uv2[0] /= face['LightmapTextureSizeinLuxels'][0]
                uv2[1] /= face['LightmapTextureSizeinLuxels'][1]
            except ZeroDivisionError:
                uv2 = [0, 0]
            uv2s.append(uv2)
        vert_count = len(verts)
        normal = [self.PLANES[face['planenum']]['normal']] * vert_count
        colour = [texdata['reflectivity']] * vert_count
        verts = list(zip(verts, normal, uvs, uv2s, colour))
        return verts

    def dispverts_of(self, face): # add format argument (lightmap uv, 2 uvs, etc)
        """vertex format [Position, Normal, TexCoord, LightCoord, Colour]
        normal is inherited from face
        returns rows, not tris"""
        verts = self.verts_of(face)
        if len(verts) != 4:
            raise RuntimeError('face does not have 4 corners (probably t-junctions)')
        if face['dispinfo'] == -1:
            raise RuntimeError('face is not a displacement!')
        dispinfo = self.DISP_INFO[face['dispinfo']]
        start = list(dispinfo['startPosition'])
        start = [round(x, 1) for x in start] # approximate match
        round_verts = []
        for vert in [v[0] for v in verts]:
            round_verts.append([round(x, 1) for x in vert])
        if start in round_verts: # "rotate"
            index = round_verts.index(start)
            verts = verts[index:] + verts[:index]
        A, B, C, D = [vector.vec3(*v[0]) for v in verts]
        Auv, Buv, Cuv, Duv = [vector.vec2(*v[2]) for v in verts]
        Auv2, Buv2, Cuv2, Duv2 = [vector.vec2(*v[3]) for v in verts]
        AD = D - A
        ADuv = Duv - Auv
        ADuv2 = Duv2 - Auv2
        BC = C - B
        BCuv = Cuv - Buv
        BCuv2 = Cuv2 - Buv2
        power = dispinfo['power']
        power2 = 2 ** power
        full_power = (power2 + 1) ** 2
        normal = [verts[0][1]] * full_power
        colour = [verts[0][4]] * full_power
        start = dispinfo['DispVertStart']
        stop = dispinfo['DispVertStart'] + full_power
        verts, uvs, uv2s = [], [], []
        for index, dispvert in enumerate(self.DISP_VERTS[start:stop]):
            t1 = index % (power2 + 1) / power2
            t2 = index // (power2 + 1) / power2
            baryvert = vector.lerp(A + (AD * t1), B + (BC * t1), t2)
            dispvert = [x * dispvert['dist'] for x in dispvert['vec']]
            verts.append([a + b for a, b in zip(baryvert, dispvert)])
            uvs.append(vector.lerp(Auv + (ADuv * t1), Buv + (BCuv * t1), t2))
            uv2s.append(vector.lerp(Auv2 + (ADuv2 * t1), Buv2 + (BCuv2 * t1), t2))
        verts = list(zip(verts, normal, uvs, uv2s, colour))
        return verts

    def export_lightmap(self):
        out_filename = self.filename + '.rgbe'
        print(f'Writing to {out_filename} ... ', end='')
        file = open(out_filename, 'wb')
        file.write(self.LIGHTING)
        file.close()
        print('Done!')

    def export_sprp_list(self):
        raise NotImplemented('not yet')
        out_filename = self.filename + '.props'
        print(f'Writing to {out_filename}...', end='')
        file = open(out_filename, 'wb')
        #TWO PARTS
        #LIST ALL PROPS ONCE, IN A SPECIFIC CODED ORDER
        #LIST ALL POSITIONS & ROTATIONS (MATCHED TO PREVIOUS CODES)
        #WRITE
        file.close()
        print(' Done!')

    def inject(self, bspfile, lump):
        """bspfile must be opened with 'rb+'"""
        try:
            lump = getattr(self, lump)
        except:
            raise RuntimeError("couldn't find lump")
        #find lump position in bspfile
        #write new lump
        #  sort dicts with map()?
        #  struct.iter_pack
        #save all data after to memory
        #truncate
        #put the end of the file back
        #change lump lengths and startpositions


    def export(self, outfile):
        """expects outfile to be a file with write bytes capability"""
        #converts all current lumps to raw counterparts
        outfile.write(b'VBSP')
        outfile.write((20).to_bytes(4, 'little'))
        offset = 0
        length = 0
        #USE THE LUMP MAP!
        #PRESERVE SOURCE FILE LUMP ORDER
        #dicts to raw lumps
        split_bytes = lambda y: map(lambda x: x.to_bytes(1, 'big'), y)

        pack_brushes = lambda x: struct.pack('3i', x['firstside'], x['numsides'], x['contents'])
        self.RAW_BRUSHES = b''.join(map(pack_brushes, self.BRUSHES))
        pack_brush_sides = lambda x: struct.pack('H3h', x['planenum'], x['texinfo'],
                                                        x['dispinfo'], x['bevel'])
        self.RAW_BRUSH_SIDES = b''.join(map(pack_brush_sides, self.BRUSHSIDES))
        if hasattr(self, 'CUBEMAPS'):
            pack_cubemaps = lambda x: struct.pack('4i', *x['origin'], x['size'])
            self.RAW_CUBEMAPS = b''.join(map(pack_brush_sides, self.BRUSHSIDES))
        if hasattr(self, 'DISP_INFO'):
            pack_disp_info = lambda x: struct.pack('3f4ifiH2i88c10I', *x['startPosition'],
                  x['DispVertStart'], x['DispTriStart'], x['power'], x['minTess'],
                  x['smoothingAngle'], x['contents'], x['MapFace'], x['LightmapAlphaStart'],
                  x['LightmapSamplePositionStart'], *map(split_bytes, x['EdgeNeighbours']),
                  *map(split_bytes, x['CornerNeighbours']), *x['AllowedVerts'])
            self.RAW_DISP_INFO = b''.join(map(pack_brush_sides, self.DISP_INFO))
            pack_disp_tris = lambda x: struct.pack('H', x)
            self.RAW_DISP_TRIS = b''.join(map(pack_disp_tris, self.DISP_TRIS))
            pack_disp_verts = lambda x: struct.pack('5f', *x['vec'], x['dist'], x['alpha'])
            self.RAW_DISP_VERTS = b''.join(map(pack_disp_verts, self.DISP_VERTS))
        pack_edges = lambda x: struct.pack('2h', *x)
        self.RAW_EDGES = b''.join(pack_edges, self.EDGES)
        self.RAW_ENTITIES = self.ENTITIES.encode('ascii')
        pack_faces = lambda x: struct.pack('H2bi4h4bif5i2HI', x['planenum'], x['side'],
              x['onNode'], x['firstedge'], x['numedges'], x['texinfo'], x['dispinfo'],
              x['surfaceFogVolumeID'], *x['styles'], x['lightofs'], x['area'],
              *x['LightmapTextureMinsinLuxels'], *['LightmapTextureSizeinLuxels'],
              x['origFace'], x['numPrims'], x['firstPrimID'], x['smoothingGroups'])
        self.RAW_FACES = b''.join(map(pack_faces, self.FACES))
        pack_leaf_faces = lambda x: struct.pack('H', x)
        self.RAW_LEAF_FACES = b''.join(map(pack_leaf_faces, self.LEAF_FACES))
        pack_leaves = lambda x: struct.pack('i8h4H2h', x['contents'],
              x['area'] << 7 + x['flags'], #'area' is 9 bits, and 'flags' is 7
              *x['mins'], *x['maxs'], x['firstleafface'], x['firstleafbrush'],
              x['numleafbrushes'], x['leafWaterDataID'], x['padding'])
        self.RAW_LEAVES = b''.join(map(pack_leaves, self.LEAVES))
        self.RAW_LIGHTING = self.LIGHTING
        if hasattr(self, 'LIGHTING_HDR'):
            self.RAW_LIGHTING_HDR = self.LIGHTING_HDR
        pack_nodes = lambda x: struct.pack('3i6h2H2h', x['planenum'], *x['children'],
              *x['mins'], *x['maxs'], x['firstface'], x['numfaces'], x['area'], x['padding'])
        self.RAW_NODES = b''.join(map(pack_nodes, self.NODES))
        self.RAW_ORIGINAL_FACES = b''.join(map(pack_faces, self.ORIGINAL_FACES))
        pack_planes = lambda x: struct.pack('4fi', x['normal'], x['dist'], x['type'])
        self.RAW_PLANES = b''.join(map(pack_planes, self.PLANES))
        pack_surfedges = lambda x: struct.pack('i', x)
        self.RAW_SURFEDES = b''.join(map(pack_surfedges, self.SURFEDGES))
        pack_texdata = lambda x: struct.pack('3f5i', *x['reflectivity'], x['texdata_st'],
              x['width'], x['height'], x['view_width'], x['view_height'])
        self.RAW_TEXDATA = b''.join(map(pack_texdata, self.TEXDATA))
        pack_texdata_st = lambda x: struct.pack('i', x)
        self.RAW_TEXDATA_STRING_TABLE = b''.join(map(pack_texdata_st, self.TEXDATA_STRING_TABLE))
        pack_texdata_sd = lambda x: struct.pack('128s', x.encode('ascii'))
        self.RAW_TEXDATA_STRING_DATA = b''.join(map(pack_texdata_sd, self.TEXDATA_STRING_DATA))
        pack_texinfo = lambda x: struct.pack('16f2i', *x['textureVecs'][0], *x['textureVecs'][1],
              *x['lightmapVecs'][0], *x['lightmapVecs'][1], x['flags'], x['texdata'])
        self.RAW_TEXINFO = b''.join(map(pack_texinfo, self.TEXINFO))
        pack_vertices = lambda x: struct.pack('3f', *x)
        self.RAW_VERTICES = b''.join(map(pack_vertices, self.VERTICES))
        pack_world_lights = lambda x: struct.pack('9f3i7f3i', *x['origin'], *x['intensity'],
              *x['normal'], x['cluster'], x['type'], x['style'], x['stopdot'], x['stopdot2'],
              x['exponent'], x['radius'], x['constant_attn'], x['quadratic_attn'],
              x['flags'], x['texinfo'], x['owner'])
        self.RAW_WORLD_LIGHTS = b''.join(map(pack_world_lights, self.WORLD_LIGHTS))
        if hasattr(self, 'WORLD_LIGHTS_HDR'):
            self.RAW_WORLD_LIGHTS_HDR = b''.join(map(pack_world_lights, self.WORLD_LIGHTS_HDR))
        #headers
        for ID in LUMP: #entities should be written last
            outfile.write(offset.to_bytes(4, 'little'))
            length = len(getattr(self, ID.name, 'RAW_' + ID.name)) #only lumps we have
            offset += length
            outfile.write(b'0000') #lump version (actually important)
            outfile.write(b'0000') #lump fourCC
        #lump orders and spacing are very important
        for ID in LUMP:
            #these cursor locations and datasize need to go into headers
            outfile.write(getattr(self, ID.name, 'RAW_' + ID.name))
        outfile.write(b'0001') #map revision

    def export_obj(self, outfile): #TODO: write .mtl for each vmt
        start_time = time.time()
        out_filename = outfile.name.split('/')[-1] if '/' in outfile.name else outfile.name.split('\\')[-1]
        total_faces = len(self.FACES)
        print(f'Exporting {self.filename} to {out_filename} ({total_faces} faces)')
        outfile.write('# bsp_tool.py generated model\n')
        outfile.write(f'# source file: {self.filename}\n')
        vs = []
        v_count = 1
        vts = []
        vt_count = 1
        vns = []
        vn_count = 1
        faces_by_material = {} # {material: [face, ...], ...}
        disps_by_material = {} # {material: [face, ...], ...}
        for face in self.FACES:
            material = self.TEXDATA_STRING_DATA[self.TEXDATA[self.TEXINFO[face['texinfo']]['texdata']]['texdata_st']]
            if face['dispinfo'] != -1:
                if material not in disps_by_material:
                    disps_by_material[material] = []
                disps_by_material[material].append(face)
            else:
                if material not in faces_by_material:
                    faces_by_material[material] = []
                faces_by_material[material].append(face)
        face_count = 0
        current_progress = 0.1
        print('0...', end='')

        for material in faces_by_material:
            outfile.write(f'usemtl {material}\n')
            for face in faces_by_material[material]:
                face_vs = self.verts_of(face)
                vn = face_vs[0][1]
                if vn not in vns:
                    vns.append(vn)
                    outfile.write(f'vn {vector.vec3(*vn):}\n')
                    vn = vn_count
                    vn_count += 1
                else:
                    vn = vns.index(vn) + 1
                f = []
                for vertex in face_vs:
                    v = vertex[0]
                    if v not in vs:
                        vs.append(v)
                        outfile.write(f'v {vector.vec3(*v):}\n')
                        v = v_count
                        v_count += 1
                    else:
                        v = vs.index(v) + 1
                    vt = vertex[2]
                    if vt not in vts:
                        vts.append(vt)
                        outfile.write(f'vt {vector.vec2(*vt):}\n')
                        vt = vt_count
                        vt_count += 1
                    else:
                        vt = vts.index(vt) + 1
                    f.append((v, vt, vn))
                outfile.write('f ' + ' '.join([f'{v}/{vt}/{vn}' for v, vt, vn in reversed(f)]) + '\n')
                face_count += 1
                if face_count >= total_faces * current_progress:
                    print(f'{current_progress * 10:.0f}...', end='')
                    current_progress += 0.1

        disp_no = 0
        outfile.write('g displacements\n')
        for material in disps_by_material:
            outfile.write(f'usemtl {material}\n')
            for displacement in disps_by_material[material]:
                outfile.write(f'o displacement_{disp_no}\n')
                disp_no += 1
                disp_vs = self.dispverts_of(displacement)
                normal = disp_vs[0][1]
                if normal not in vns:
                    vns.append(normal)
                    outfile.write(f'vn {vector.vec3(*normal):}\n')
                    normal = vn_count
                    vn_count += 1
                else:
                    normal = vns.index(normal) + 1
                f = []
                for v, vn, vt, vt2, colour in disp_vs:
                    obj_file.write(f'v {vector.vec3(*v):}\nvt {vector.vec2(*vt):}\n')
                power = bsp_file.DISP_INFO[displacement['dispinfo']]['power']
                disp_size = (2 ** power + 1) ** 2
                tris = disp_tris(range(disp_size), power)
                for a, b, c in zip(tris[::3], tris[1::3], tris[2::3]):
                    a = (a + v_count, a + vt_count, normal)
                    b = (b + v_count, b + vt_count, normal)
                    c = (c + v_count, c + vt_count, normal)
                    a, b, c = [map(str, i) for i in (c, b, a)]
                    obj_file.write(f"f {'/'.join(a)} {'/'.join(b)} {'/'.join(c)}\n")
                v_count += disp_size
                vt_count += disp_size
                face_count += 1
                if face_count >= total_faces * current_progress:
                    print(f'{current_progress * 10:.0f}...', end='')
                    current_progress += 0.1

        total_time = time.time() - start_time
        minutes = total_time // 60
        seconds = total_time - minutes * 60
        outfile.write(f'# file generated in {minutes:.0f} minutes {seconds:2.3f} seconds')
        print('Done!')

    def tf2m_compliance_test(self, mdls, vmts):
        passes = True
        cubemaps = False
        if self.LIGHTING.replace(b'\x00', b'') == b'':
            print(self.filename[:-4], 'is fullbright')
            passes = False
        try:
            getattr(self, 'CUBEMAPS')
            cubemaps = True
        except AttributeError:
            print(self.filename, 'has no cubemaps')
            #check all samples are in pakfile
            #warn if no HDR cubemaps are present
            #maps/mapname/texdir/texture_X_Y_Z.vmt
        if self.RAW_PAKFILE == b'PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00XZP1 0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':
            if cubemaps:
                print(f"{self.filename[:-4]}'s cubemaps are not compiled")
            else:
                print(self.filename[:-4], 'has no packed assets')
        else:
            if b'.vhv'in self.RAW_PAKFILE:
                print(f"{self.filename[:-4]}'s cubemaps are compiled and packed!")
        #if hasattr(self, 'LIGHTING_HDR'):
        #    check for HDR lightmaps
        for material_name in self.TEXDATA_STRING_DATA:
            short_name = material_name
            material_name = 'materials/' + material_name.lower() + '.vmt'
            if material_name not in vmts:
                print('{self.filename} references {short_name} and is', end=' ')
                if bytes(material_name, 'utf-8') in self.RAW_PAKFILE:
                    print('PACKED!')
                else:
                    print('NOT_PACKED!')
                    passes = False
        for entity in self.ENTITIES:
            if 'prop' in entity['classname']:
                referenced_mdls.append(entity['model'])
        print(referenced_mdls)
        return passes

def disp_tris(verts, power):
    """takes flat array of verts and arranges them in a patterned triangle grid
    expects verts to be an array of length ((2 ** power) + 1) ** 2"""
    power2 = 2 ** power
    power2A = power2 + 1
    power2B = power2 + 2
    power2C = power2 + 3
    tris = []
    for line in range(power2):
        line_offset = power2A * line
        for block in range(2 ** (power - 1)):
            offset = line_offset + 2 * block
            if line % 2 == 0: # |\|/|
                tris.append(verts[offset + 0])
                tris.append(verts[offset + power2A])
                tris.append(verts[offset + 1])

                tris.append(verts[offset + power2A])
                tris.append(verts[offset + power2B])
                tris.append(verts[offset + 1])

                tris.append(verts[offset + power2B])
                tris.append(verts[offset + power2C])
                tris.append(verts[offset + 1])

                tris.append(verts[offset + power2C])
                tris.append(verts[offset + 2])
                tris.append(verts[offset + 1])
            else: #|/|\|
                tris.append(verts[offset + 0])
                tris.append(verts[offset + power2A])
                tris.append(verts[offset + power2B])

                tris.append(verts[offset + 1])
                tris.append(verts[offset + 0])
                tris.append(verts[offset + power2B])

                tris.append(verts[offset + 2])
                tris.append(verts[offset + 1])
                tris.append(verts[offset + power2B])

                tris.append(verts[offset + power2C])
                tris.append(verts[offset + 2])
                tris.append(verts[offset + power2B])
    return tris


if __name__=='__main__':
    import argparse
    # --game -G [tf2/hl2/vindictus]
    # --obj -o [outfiledir/outfile] // defaults to sourcedir
    ## 3 error levels -W -Warn
    # -W strict // stop if cannot load ANY chunk
    # -W X // stop after X failed chunk loads
    # -W lazy // ignore any and all chunks that cannot be loaded
    # --stats [options] // list various stats into a .csv file
    #                   // take an example .csv?
    # can you think of any other options?
    import sys
    if len(sys.argv) > 1: # drag drop obj converter
        for map_path in sys.argv[1:]:
            bsp_file = bsp(map_path)
            start = time.time()
            obj_file = open(map_path + '.obj', 'w')
            bsp_file.export_obj(obj_file)
            obj_file.close()
            conversion_time = time.time() - start
            print(f'Converting {bsp_file.filename} took {conversion_time // 60:.0f}:{conversion_time % 60:.3f}')
    else:
        ... # do nothing (or uncomment tests)
##        harvest = bsp('E:/Steam/SteamApps/common/Team Fortress 2/tf/maps/koth_harvest_final')
##        import json
##        leaf_file = open('koth_harvest_leaf_lump.json', 'w')
##        leaf_file.write('[' + ',\n'.join([json.dumps(leaf) for leaf in harvest.LEAVES]) + ']')
##        leaf_file.close()
##        print('Leaves written to file!')
