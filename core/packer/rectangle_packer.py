
# thank you https://stackoverflow.com/a/71432759
from __future__ import annotations


from typing import Optional
from bpy.types import Image, Material


# Copyright (c) 2011, 2012, 2013, 2014, 2015, 2016 Jake Gordon and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

class Rectangle_Obj:
    x: int = 0
    y: int  = 0
    w: int = 0
    h: int = 0
    down: Rectangle_Obj = None
    used: bool = False
    right: Rectangle_Obj = None

    def __init__(self, x:int, y:int, w:int, h:int, down=None, used =False, right=None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.down = down
        self.used = used
        self.right = right 

    def split(self, w, h) -> Rectangle_Obj:
        self.used = True
        self.down = Rectangle_Obj(x=self.x, y=self.y + h, w=self.w, h=self.h - h)
        self.right = Rectangle_Obj(x=self.x + w, y=self.y, w=self.w - w, h=h)
        return self

    def find(self, w, h) -> Optional[Rectangle_Obj]:
        if self.used:
            return self.right.find(w, h) or self.down.find(w, h)
        elif (w <= self.w) and (h <= self.h):
            return self
        return None

class MaterialImageList:
    albedo: Image
    normal: Image
    emission: Image
    ambient_occlusion: Image
    height: Image
    roughness: Image
    fit: Rectangle_Obj
    material: Material
    
    def __init__(self):
        pass

    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0 


    


class BinPacker(object):
    root: Rectangle_Obj
    bin: list[MaterialImageList] = []
    def __init__(self, structure: list[MaterialImageList]):
        self.root = None
        self.bin = structure

    def fit(self):
        structure = self.bin
        structure_len = len(self.bin)
        w: int = 0
        h: int = 0
        if structure_len > 0:
            w = structure[0].w
            h = structure[0].h
        self.root = Rectangle_Obj(x=0, y=0, w=w, h=h)
        for img in structure:
            w = img.w 
            h = img.h
            node = self.root.find(w, h)
            if node:
                img.fit = node.split(w, h)
            else:
                img.fit = self.grow_node(w, h)
        return structure

    def grow_node(self, w, h) -> Optional[Rectangle_Obj]:
        can_grow_right = (h <= self.root.h)
        can_grow_down = (w <= self.root.w)

        should_grow_right = can_grow_right and (self.root.h >= (self.root.w + w))
        should_grow_down = can_grow_down and (self.root.w >= (self.root.h + h))

        if should_grow_right:
            return self.grow_right(w, h)
        elif should_grow_down:
            return self.grow_down(w, h)
        elif can_grow_right:
            return self.grow_right(w, h)
        elif can_grow_down:
            return self.grow_down(w, h)
        return None

    def grow_right(self, w, h) -> Optional[Rectangle_Obj]:
        self.root = Rectangle_Obj(
            used=True,
            x=0,
            y=0,
            w=self.root.w + w,
            h=self.root.h,
            down=self.root,
            right=Rectangle_Obj(x=self.root.w, y=0, w=w, h=self.root.h))
        node = self.root.find(w, h)
        if node:
            return node.split(w, h)
        return None

    def grow_down(self, w, h) -> Optional[Rectangle_Obj]:
        self.root = Rectangle_Obj(
            used=True,
            x=0,
            y=0,
            w=self.root.w,
            h=self.root.h + h,
            down=Rectangle_Obj(x=0, y=self.root.h, w=self.root.w, h=h),
            right=self.root
        )
        node = self.root.find(w, h)
        if node:
            return node.split(w, h)
        return None