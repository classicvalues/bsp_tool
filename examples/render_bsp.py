﻿import colorsys
import ctypes
import itertools
import math
import time
import struct
import sys
# third-party imports
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
from OpenGL.GLU import *
from sdl2 import *
# local imports
import utils.camera
sys.path.insert(0, '../')
import bsp_tool
from vector import *

utils.camera.sensitivity = 2

def clamp(x, minimum=0, maximum=1):
    return maximum if x > maximum else minimum if x < minimum else x

def calcTriFanIndices(vertices, startIndex):
    "polygon to triangle fan (indices only) - by Exactol"
    indices = []
    for i in range(1, len(vertices) - 1):
        indices += [startIndex, startIndex + i, startIndex + i + 1]
    return indices

def main(width, height, bsp):
    SDL_Init(SDL_INIT_VIDEO)
    window = SDL_CreateWindow(bytes(bsp.filename, 'utf-8'), SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, width, height, SDL_WINDOW_OPENGL) #| SDL_WINDOW_BORDERLESS) #SDL_WINDOW_FULLSCREEN
    glContext = SDL_GL_CreateContext(window)
    # GL SETUP
    glClearColor(0, .5, 1, 0)
    glEnable(GL_CULL_FACE)
    glEnable(GL_DEPTH_TEST)
    glFrontFace(GL_CW)
    glPointSize(4)
    glPolygonMode(GL_BACK, GL_LINE)
    gluPerspective(90, width / height, 0.1, 4096 * 4)

    # BSP => VERTEX BUFFER OBJECTS
    conversion_start = time.time()
    all_faces = []
    all_faces_map = [] # [(start, length), ...]
    start = 0
    for face in bsp.FACES:
        if face.disp_info == -1:
            f_verts = bsp.verts_of(face) # add to vertex buffer here and fan the indices
            out = f_verts[:3]
            f_verts = f_verts[3:]
            for vert in f_verts:
                out += [out[0], out[-1], vert]
            f_verts = out
            f_verts_len = len(f_verts)
            all_faces_map.append((start, f_verts_len))
            start += f_verts_len
        else: # face is a displacement
            power = bsp.DISP_INFO[face.disp_info].power
            f_verts = bsp.dispverts_of(face)
            f_verts = bsp_tool.disp_tris(f_verts, power)
            f_verts_len = len(f_verts)
            all_faces_map.append((start, f_verts_len))
            start += f_verts_len
        all_faces += f_verts
    slow_faces = all_faces.copy()
    all_faces = list(itertools.chain(*itertools.chain(*all_faces)))
    all_faces_size = len(all_faces)

    vertices = all_faces
    indices = range(all_faces_size)

    conversion_end = time.time()
    print(bsp.filename.upper(), end=' ')
    print(f"{bsp.bytesize // 1024:,}KB BSP", end=" >>> ")
    print(f"{len(vertices) // 9:,} TRIS", end=" & ")
    print(f"{(len(vertices) * 4) // 1024:,}KB VRAM")
    print(f"Converted to geometry in {(conversion_end - conversion_start) * 1000:,.3f}ms")
    print()

    VERTEX_BUFFER, INDEX_BUFFER = glGenBuffers(2)
    # VERTICES
    glBindBuffer(GL_ARRAY_BUFFER, VERTEX_BUFFER)
    glBufferData(GL_ARRAY_BUFFER, len(vertices) * 4, np.array(vertices, dtype=np.float32), GL_STATIC_DRAW)
    # INDICES
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, INDEX_BUFFER)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(indices) * 4, np.array(indices, dtype=np.uint64), GL_STATIC_DRAW)

    # SHADER SELECTION
    shader_folder = "shaders/"
    render_mode = "flat"
    major, minor = glGetIntegerv(GL_MAJOR_VERSION), glGetIntegerv(GL_MINOR_VERSION)
    print(f"OpenGL Version {major}.{minor}")
    if major >= 4: #450
        USING_ES = False
        shader_folder += "450_CORE"    
    elif major == 3: # if GLSL 450 not supported, use GLES 300
        USING_ES = True
        shader_folder += "300_ES"
    else:
        raise NotImplementedError("GLSL Version ({major, minor}) is unsupported (too low)!")

    # SHADER COMPILATION
    compile_shader = lambda filename, shader_type: compileShader(open(filename, "rb"), shader_type)
    # brush_shader
    vert_shader = compile_shader(f"{shader_folder}/brush.v", GL_VERTEX_SHADER)
    frag_shader = compile_shader(f"{shader_folder}/brush_{render_mode}.f", GL_FRAGMENT_SHADER)
    brush_shader = compileProgram(vert_shader, frag_shader)
    glLinkProgram(brush_shader)
    # mesh_shader (rBSP: TitanFall2 & Apex Legends)
##    vert_shader = compile_shader(f"{shader_folder}/mesh.v", GL_VERTEX_SHADER)
##    frag_shader = compile_shader(f"{shader_folder}/mesh_{render_mode}.v", GL_VERTEX_SHADER)
##    mesh_shader = compile_program(vert_shader, frag_shader)
##    glLinkProgram(mesh_shader)
    del vert_shader, frag_shader
    
    # SHADER VERTEX FORMAT
    glEnableVertexAttribArray(0) # brush vertexPosition
    glEnableVertexAttribArray(1) # brush vertexNormal
    glEnableVertexAttribArray(2) # brush vertexTexcoord
    glEnableVertexAttribArray(3) # brush vertexLightmapCoord
    glEnableVertexAttribArray(4) # brush reflectivityColour
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 52, GLvoidp(0))
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_TRUE,  52, GLvoidp(12))
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 52, GLvoidp(24))
    glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, 52, GLvoidp(32))
    glVertexAttribPointer(4, 3, GL_FLOAT, GL_FALSE, 52, GLvoidp(40))

    # SHADER UNIFORMS
    if USING_ES:
        glUseProgram(brush_shader)
        attrib_position = glGetAttribLocation(brush_shader, 'vertexPosition')
        attrib_normal = glGetAttribLocation(brush_shader, 'vertexNormal')
        attrib_texture_uv = glGetAttribLocation(brush_shader, 'vertexTexCoord')
        attrib_lightmap_uv = glGetAttribLocation(brush_shader, 'vertexLightCoord')
        attrib_colour_uv = glGetAttribLocation(brush_shader, 'vertexColour')
        # get MVP matrix location
        # mesh_shader
        glUseProgram(0)

    # INPUT STATE
    keys = []
    mousepos = vec2()
    view_init = vec3(0, 0, 32), None, 128
    VIEW_CAMERA = utils.camera.freecam(*view_init)

    # SDL EVENT STATE
    event = SDL_Event()
    SDL_GL_SetSwapInterval(0)
    SDL_CaptureMouse(SDL_TRUE)
    SDL_SetRelativeMouseMode(SDL_TRUE)
    SDL_SetWindowGrab(window, SDL_TRUE)
    SDL_WarpMouseInWindow(window, width // 2, height // 2)

    end_of_previous_tick = time.time()
    tickrate = 120
    while True:
        while SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == SDL_QUIT or event.key.keysym.sym == SDLK_ESCAPE and event.type == SDL_KEYDOWN:
                SDL_GL_DeleteContext(glContext)
                SDL_DestroyWindow(window)
                SDL_Quit()
                return bsp # let the user play with the bsp after we're done
            # KEYBOARD INPUT
            if event.type == SDL_KEYDOWN:
                if event.key.keysym.sym not in keys:
                    keys.append(event.key.keysym.sym)
            if event.type == SDL_KEYUP:
                while event.key.keysym.sym in keys:
                    keys.remove(event.key.keysym.sym)
            # MOUSE INPUT
            if event.type == SDL_MOUSEMOTION:
                mousepos += vec2(event.motion.xrel, event.motion.yrel)
                SDL_WarpMouseInWindow(window, width // 2, height // 2)
            if event.type == SDL_MOUSEWHEEL:
                VIEW_CAMERA.speed += event.wheel.y * 32
            if event.type == SDL_MOUSEBUTTONDOWN:
                if event.button.button not in keys:
                    keys.append(event.button.button)
            if event.type == SDL_MOUSEBUTTONUP:
                while event.button.button in keys:
                    keys.remove(event.button.button)

        # PROCESS TICK
        dt = time.time() - end_of_previous_tick
        while dt >= 1 / tickrate:
            VIEW_CAMERA.update(mousepos, keys, 1 / tickrate)
            # HANDLE KEYPRESSES
            if SDLK_BACKQUOTE in keys: # ~ = print data for debugging
                print(">>> PRINT RELEVANT DATA HERE <<<")
                while SDLK_BACKQUOTE in keys:
                    keys.remove(SDLK_BACKQUOTE)
            if SDLK_r in keys: # R = reset camera
                VIEW_CAMERA = utils.camera.freecam(*view_init)
            if SDLK_LSHIFT in keys: # LShift = Camera speed +
                VIEW_CAMERA.speed += 5
            if SDLK_LCTRL in keys: # LCtrl = Camera speed -
                VIEW_CAMERA.speed -= 5
            dt -= 1 / tickrate # if dt >= 2/tickrate: simulate another tick
            end_of_previous_tick = time.time()

        # RENDER PASS
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()
        VIEW_CAMERA.set()

        glUseProgram(brush_shader)
        glDrawArrays(GL_TRIANGLES, 0, len(vertices))

        # CENTER MARKER
        glUseProgram(0)
        glBegin(GL_LINES)
        glColor(1, 0, 0)
        glVertex(0, 0, 0)
        glVertex(128, 0, 0)
        glColor(0, 1, 0)
        glVertex(0, 0, 0)
        glVertex(0, 128, 0)
        glColor(0, 0, 1)
        glVertex(0, 0, 0)
        glVertex(0, 0, 128)
        glEnd()

        glPopMatrix()
        SDL_GL_SwapWindow(window)

if __name__ == '__main__':
    width, height = 1280, 720

    mod = bsp_tool.team_fortress2
    folder = "D:/SteamLibrary/steamapps/common/Team Fortress 2/tf/maps/"
    filename = "cp_cloak.bsp"

##    mod = bsp_tool.titanfall2
##    folder = "E:/Mod/Titanfall2/"
##    filename = "mp_glitch/maps/mp_glitch.bsp"
    
    bsp = bsp_tool.bsp(folder + filename, mod)
    
    try:
        bsp_file = main(1280, 720, bsp)
    except Exception as exc:
        SDL_Quit()
        raise exc
