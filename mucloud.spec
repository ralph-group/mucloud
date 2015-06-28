"""

This file is part of the MuCloud package.

Copyright (c) 2014-2015 Colin Jermain, Graham Rowlands

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


** This File does not need to be edited unless you are making an executable
out of MuCloud. In that case, change the source_path below to the appropriate
directory and use pyinstaller to make the executable.

"""
# -*- mode: python -*-

import os
global source_path

# Modify the path for your system
source_path = '/home/colin/Research/Software/mucloud/'

def relative_path(path=''):
  return os.path.join(os.path.abspath(source_path), path)

block_cipher = None

a = Analysis(['mucloud.py'],
             pathex=[relative_path()],
             hiddenimports=['Queue'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
a.binaries.append((
    'boto/endpoints.json',
    relative_path('env/lib/python2.7/site-packages/'
                  'boto/endpoints.json'),
    'DATA'
))
a.binaries.append((
    'boto/cacerts/cacerts.txt',
    relative_path('env/lib/python2.7/site-packages/'
                  'boto/cacerts/cacerts.txt'),
    'DATA'
))
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='mucloud',
          debug=False,
          strip=None,
          upx=True,
          console=True )
