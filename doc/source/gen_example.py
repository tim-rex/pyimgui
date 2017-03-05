# -*- coding: utf-8 -*-
from inspect import cleandoc
import os

import glfw
import OpenGL.GL as gl
from PIL import Image
import imageio
import numpy

import imgui
from imgui.impl import GlfwImpl


io = imgui.get_io()


new_frame = imgui.new_frame

mouse_pos = (-1, -1)
mouse_down = 0


def _clear_mouse():
    global mouse_pos
    global mouse_down

    mouse_pos = (-1, -1)
    mouse_down = 0


def _new_frame_patched():
    global mouse_pos
    global mouse_down

    io.mouse_pos = mouse_pos
    io.mouse_down[0] = mouse_down

    return new_frame()


def _patch_imgui():
    if imgui.new_frame == new_frame:
        imgui.new_frame = _new_frame_patched

    _clear_mouse()


def simulate_click(x, y, state):
    global mouse_pos
    global mouse_down

    mouse_pos = x, y
    mouse_down = state


def render_snippet(
    source,
    file_path,
    title="",
    width=200,
    height=200,
    auto_window=False,
    auto_layout=False,
    animated=False,
    output_dir='.',
    click=None,
):
    _patch_imgui()

    code = compile(source, '<str>', 'exec')
    window_name = "minimal ImGui/GLFW3 example"

    if not glfw.init():
        print("Could not initialize OpenGL context")
        exit(1)

    # OS X supports only forward-compatible core profiles from 3.2
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)
    # note: creating context without window is tricky so made window invisible
    glfw.window_hint(glfw.VISIBLE, False)

    window = glfw.create_window(
        int(width), int(height), window_name, None, None
    )

    glfw.make_context_current(window)

    if not window:
        glfw.terminate()
        print("Could not initialize Window")
        exit(1)

    imgui_ctx = GlfwImpl(window)
    imgui_ctx.enable()
    glfw.poll_events()

    # render target for framebuffer
    texture = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, None)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)

    # create new framebuffer
    offscreen_fb = gl.glGenFramebuffers(1)
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, offscreen_fb)
    # attach texture to framebuffer
    gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, texture, 0)

    image_list = []

    # note: Clicking simulation is hacky as fuck and it
    #       requires at least three frames to be rendered:
    #       * 1st with mouse in position but without button pressed.
    #       * 2nd in roughly same posiotion of mouse to turn on hover
    #         mouse button starts to press but still does not trigger click.
    #       * 3rd in the same position with button pressed still to finally
    #         trigger the "clicked" state.
    # note: If clicking simulation is not required we draw only one frame.
    for m_state in ([None] if not click else [False, True, True, True]):

        # note: Mouse click MUST be simulated before new_frame call!
        if click:
            imgui_ctx.io.mouse_draw_cursor = True
            simulate_click(click[0], click[1], m_state)
        else:
            # just make sure mouse state is clear
            _clear_mouse()

        imgui_ctx.new_frame()

        with imgui.styled(imgui.STYLE_ALPHA, 1):
            imgui.core.set_next_window_size(0, 0)

            if auto_layout:
                imgui.set_next_window_size(width - 10, height - 10)
                imgui.set_next_window_centered()

            if auto_window:
                imgui.set_next_window_size(width - 10, height - 10)
                imgui.set_next_window_centered()
                # note: title may be unicode and since we are building docs
                #       on py27 there is a need for encoding it.
                imgui.begin("Example: %s" % title.encode())

            exec(code, locals(), globals())

            if auto_window:
                imgui.end()

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, offscreen_fb)

        gl.glClearColor(1, 1, 1, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()

        # retrieve pixels from framebuffer and write to file
        pixels = gl.glReadPixels(0, 0, width, height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        image = Image.frombytes('RGBA', (width, height), pixels)
        # note: glReadPixels returns lines "bottom to top" but PIL reads bytes
        #       top to bottom
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        image_list.append(image)

    if animated:
        path = os.path.join(output_dir, file_path)

        imageio.mimsave(
            path,
            [numpy.asarray(im, dtype=numpy.uint8) for im in image_list]
        )
    else:
        image_list[-1].save(os.path.join(output_dir, file_path))

    glfw.terminate()


if __name__ == "__main__":
    example_source = cleandoc(
        """
        current = 2
        imgui.begin("Example: combo widget")

        clicked, current = imgui.combo(
            "combo", current, ["first", "second", "third"]
        )

        imgui.end()
        """
    )

    render_snippet(
        example_source,
        'example_snippet.gif',
        height=200,
        width=200,
        animated=True,
        auto_layout=True,
        click=(80, 40)
    )

