import os
import sys
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info
from distutils.command.build import build
import distutils
import subprocess
from multiprocessing import cpu_count
from ctypes.util import find_library
from setuptools import Extension
import platform
import glob

#Current version
version = "1.3.4"

"""
To release a new verison:

    1) Edit the version number above, then commit the change!

    2) Tag the release with git

    >>> python setup.py tag

    3) Rebuild to update version in library and rebuild docs

    >>> make
    >>> make docs

    4) Publish the release to PyPi,
    ensure this is done in a clean checkout with no other source changes!

    >>> python setup.py publish

    (If this fails, check ~/.pypirc and try upgrading pip: pip install -U pip setuptools)

TODO:
    Review possible dependencies to support image/video libraries
    - imageio or pillow for libpng, libtiff
    - ffmpeg-python or opencv-python for libavcodec
"""

#Run with "tag" arg to create a release tag
if sys.argv[-1] == 'tag':
    os.system("git tag -a %s -m 'version %s'" % (version, version))
    os.system("git push --tags")
    sys.exit()

#Run with "publish" arg to upload the release
if sys.argv[-1] == 'publish':
    os.system("twine upload dist/*")
    sys.exit()

def write_version():
    """
    Writes version info to version.cpp
    """
    f = open('src/version.cpp', 'a+')
    content = f.read()

    if not version in content:
        f.close()
        f = open('src/version.cpp', 'w')
        print("Writing new version: " + version)
        f.write('#include "version.h"\nconst std::string version = "%s";\n' % version)
    else:
        print("Version matches: " + version)

    f.close()

#From https://stackoverflow.com/a/28949827/866759
def check_libraries(libraries, headers):
    """check if the C module can be built by trying to compile a small
    program against the passed library with passed headers"""

    import tempfile
    import shutil

    import distutils.sysconfig
    import distutils.ccompiler
    from distutils.errors import CompileError, LinkError

    # write a temporary .c file to compile
    c_code = "int main(int argc, char* argv[]) { return 0; }"
    #Add headers
    for header in headers:
        c_code = "#include <" + header + ">\n" + c_code

    tmp_dir = tempfile.mkdtemp(prefix = 'tmp_comp__')
    bin_file_name = os.path.join(tmp_dir, 'test_comp')
    file_name = bin_file_name + '.c'
    with open(file_name, 'w') as fp:
        fp.write(c_code)

    # and try to compile it
    compiler = distutils.ccompiler.new_compiler()
    assert isinstance(compiler, distutils.ccompiler.CCompiler)
    distutils.sysconfig.customize_compiler(compiler)

    try:
        compiler.link_executable(
            compiler.compile([file_name]),
            bin_file_name,
            libraries=libraries,
        )
    except CompileError:
        print('Libraries ' + str(libraries) + ' test compile error')
        ret_val = False
    except LinkError:
        print('Libraries ' + str(libraries) + ' test link error')
        ret_val = False
    else:
        print('Libraries ' + str(libraries) + ' found and passed compile test')
        ret_val = True
    shutil.rmtree(tmp_dir)
    return ret_val

if __name__ == "__main__":
    #Update version.cpp
    write_version()

    sqlite3_path = 'src/sqlite3'
    sqlite3_lib = [['sqlite3', {
                   'sources': [os.path.join(sqlite3_path, 'sqlite3.c')],
                   'include_dirs': [sqlite3_path],
                   'macros': None,
                   }
                  ]]

    _debug = False
    srcs = ['src/LavaVuPython_wrap.cxx']
    srcs += glob.glob('src/*.cpp')
    srcs += glob.glob('src/Main/*.cpp')
    srcs += glob.glob('src/jpeg/*.cpp')
    defines = [('USE_FONTS', '1')]
    cflags = []
    libs = [] #['sqlite3']
    ldflags = []
    inc_dirs = [sqlite3_path]
    import numpy
    inc_dirs += [numpy.get_include()]
    lib_dirs = []
    install = [] #Extra files to install in package root

    if _debug:
        defines += [('CONFIG', 'debug')]

    #OS Specific
    P = platform.system()
    if P == 'Windows':
        #Windows - includes all dependencies, (TODO: ffmpeg)
        srcs += ['src/png/lodepng.cpp']
        srcs += ['src/miniz/miniz.c']
        defines += [('HAVE_GLFW', '1')]
        #defines += [('HAVE_LIBPNG', 1)]
        inc_dirs += [os.path.join(os.getcwd(), 'src', 'windows', 'inc')]
        #32 or 64 bit python interpreter?
        if sys.maxsize > 2**32:
            LIBS = 'lib64'
        else:
            LIBS = 'lib32'
        lib_dirs += [os.path.join(os.getcwd(), 'src', 'windows', LIBS)]
        ldflags += ['/LIBPATH:' + os.path.join(os.getcwd(), 'src', 'windows', LIBS)]
        libs += ['opengl32', 'pthreadVC2', 'glfw3dll']
        install += [os.path.join('src', 'windows', LIBS, 'pthreadVC2.dll')]
        install += [os.path.join('src', 'windows', LIBS, 'glfw3.dll')]
    else:
        #POSIX only - find external dependencies
        cflags += ['-std=c++0x']
        # Optional external libraries - check if installed
        if find_library('png') and check_libraries(['png', 'z'], ['png.h', 'zlib.h']):
            defines += [('HAVE_LIBPNG', 1), ('USE_ZLIB', '1')]
            libs += ['png', 'z']
        else:
            srcs += ['src/png/lodepng.cpp']
            if find_library('z') and check_libraries(['z'], ['zlib.h']):
                defines += [('USE_ZLIB', '1')]
                libs += ['z']
            else:
                srcs += ['src/miniz/miniz.c']
        if find_library('tiff') and check_libraries(['tiff'], ['tiffio.h']):
            defines += [('HAVE_LIBTIFF', 1)]
            libs += ['tiff']
        if (find_library('avcodec') and find_library('avformat')
            and find_library('avutil')
            and check_libraries(['avcodec', 'avformat', 'avutil'],
                ['libavformat/avformat.h', 'libavcodec/avcodec.h', 'libavutil/mathematics.h',
                 'libavutil/imgutils.h'])):
            defines += [('HAVE_LIBAVCODEC', 1)]
            libs += ['avcodec', 'avformat', 'avutil']
            if find_library('swscale') and check_libraries(['swscale'], ['libswscale/swscale.h']):
                defines += [('HAVE_SWSCALE', 1)]
                libs += ['swscale']

        if P == 'Linux':
            #Linux X11 or EGL
            defines += [('HAVE_X11', '1')]
            libs += ['GL', 'dl', 'pthread', 'm', 'X11']
            #EGL for offscreen OpenGL without X11/GLX - works only with NVidia currently
            #if find_library('OpenGL') and find_library('EGL') and check_libraries(['OpenGL', 'EGL'], ['GL/gl.h']):
            #    defines += [('EGL', 1)]
        elif P == 'Darwin':
            #Mac OS X with Cocoa + CGL
            #srcs += ['src/Main/CocoaViewer.mm']
            #This hack is because setuptools can't handle .mm extension
            from shutil import copyfile
            copyfile('src/Main/CocoaViewer.mm', 'src/Main/CocoaViewer.m')
            srcs += ['src/Main/CocoaViewer.m']
            cflags += ['-ObjC++'] #Now have to tell compiler it's objective c++ as .m file indicates objective c
            defines += [('HAVE_CGL', '1')]
            cflags += ['-undefined suppress', '-flat_namespace'] #Swig, necessary?
            cflags += ['-Wno-unknown-warning-option', '-Wno-c++14-extensions', '-Wno-shift-negative-value']
            cflags += ['-FCocoa', '-FOpenGL', '-stdlib=libc++']
            libs += ['c++', 'dl', 'pthread',  'objc', 'm']
            os.environ['LDFLAGS'] = '-framework Cocoa -framework Quartz -framework OpenGL'
            #ldflags += ['-framework Cocoa', '-framework Quartz', '-framework OpenGL']

    lv = Extension('_LavaVuPython',
                    define_macros = defines,
                    include_dirs = inc_dirs,
                    libraries = libs,
                    library_dirs = lib_dirs,
                    extra_compile_args = cflags,
                    extra_link_args = ldflags,
                    sources = srcs)

    setup(name = 'lavavu',
          author            = "Owen Kaluza",
          author_email      = "owen.kaluza@monash.edu",
          url               = "https://github.com/OKaluza/LavaVu",
          version           = version,
          license           = "LGPL-3",
          description       = "Python interface to LavaVu OpenGL 3D scientific visualisation utilities",
          long_description  = 'See https://github.com/OKaluza/LavaVu/wiki for more info',
          packages          = ['lavavu'],
          install_requires  = ['numpy', 'jupyter-server-proxy;python_version>"2.7"'],
          platforms         = ['any'],
          entry_points      = {
              'gui_scripts': [
                  'LV = lavavu.__main__:main',
                  'LavaVu = lavavu.__main__:main'
              ]
          },
          package_data      = {'lavavu': glob.glob('lavavu/shaders/*.*') + glob.glob('lavavu/html/*.*') + ['lavavu/font.bin', 'lavavu/dict.json']},
          data_files        = [('lavavu', ['lavavu/font.bin', 'lavavu/dict.json']), ('', install)],
          include_package_data = True,
          classifiers = [
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
            'Operating System :: POSIX :: Linux',
            'Operating System :: MacOS',
            'Operating System :: Microsoft :: Windows',
            'Environment :: X11 Applications',
            'Environment :: MacOS X :: Cocoa',
            'Environment :: Win32 (MS Windows)',
            'Programming Language :: C++',
            'Topic :: Multimedia :: Graphics :: 3D Rendering',
            'Topic :: Scientific/Engineering :: Visualization',
            'Development Status :: 4 - Beta',
            #'Development Status :: 5 - Production/Stable',
            'Programming Language :: C++',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Framework :: Jupyter',
            'Framework :: IPython',
          ],
          ext_modules = [lv], libraries=sqlite3_lib
          )

