import ctypes
import typing
from io import BytesIO
import struct
from . import common

class ResoType():
    

    

    def __init__(self):
        pass

    def write(self, data: BytesIO):
        pass

    def read(cls, data: BytesIO):
        pass

#These below are collection of the basic resonite typing made from C#. This is in order to store data in a sane way and decode/encode it.

class color(ResoType):
    r: float = 0
    g: float = 0
    b: float = 0
    a: float = 0


    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<ffff", self.r, self.g, self.b, self.a))
        
    def read(self,data):
        self.r, self.g, self.b, self.a = struct.unpack("<ffff", data.read(4*4))[0]


class color32(ResoType):
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 0


    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<BBBB", self.r, self.g, self.b, self.a))
        
    def read(self,data):
        self.r, self.g, self.b, self.a = struct.unpack("<BBBB", data.read(4))[0]

class string(ResoType):
    x: str

    def __str__(self) -> str:
        return self.x

    def __init__(self,value=""):
        self.x = value
    
    def write(self, data: BytesIO):
        common.WriteCSharp_str(data,self.x)
        
    def read(self,data):
        
        self.x = common.ReadCSharp_str(data)


class byte(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<B", self.x))
        
    def read(self,data):
        self.x = struct.unpack("<B", data.read(1))[0]

class sbyte(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<b", self.x))
        
    def read(self,data):
        self.x = struct.unpack("<b", data.read(1))[0]

class ushort(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<H", self.x))
        
    def read(self,data):
        self.x = struct.unpack("<H", data.read(2))[0]

class short(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<h", self.x))
        
    def read(self,data):
        self.x = struct.unpack("<h", data.read(2))[0]

class bool(ResoType):
    x: bool = False


    def __bool__(self) -> bool:
        return self.x
    def __init__(self,value=False):
        self.x = value
    
    def write(self, data: BytesIO):
        data.write(struct.pack("?", self.x))
        
    def read(self,data):
        self.x = struct.unpack("?", data.read(1))[0]

class bool2(bool):
    y: bool = False

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        byte: ctypes.c_ubyte = ctypes.c_ubyte(struct.unpack("<B",data.read(1))[0])
        self.x = (byte & 1) > 0
        self.y = (byte & 2) > 0

    def createflags(self) -> ctypes.c_byte:
        flags: ctypes.c_ubyte = ctypes.c_ubyte(0)
        flags |= (1 if self.x else 0)
        flags |= (2 if self.y else 0)
        return flags
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<B", self.createflags()))
        

class bool3(bool2):
    z: bool = False
    
    def __init__(self):
        pass

    def read(self,data):
        byte: ctypes.c_ubyte = ctypes.c_ubyte(struct.unpack("<B",data.read(1))[0])
        self.x = (byte & 1) > 0
        self.y = (byte & 2) > 0
        self.z = (byte & 4) > 0

    def createflags(self) -> ctypes.c_byte:
        flags: ctypes.c_ubyte = ctypes.c_ubyte(0)
        flags |= (1 if self.x else 0)
        flags |= (2 if self.y else 0)
        flags |= (3 if self.z else 0)
        return flags
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<B", self.createflags()))
    

class bool4(bool3):
    w: bool = False

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        byte: ctypes.c_ubyte = ctypes.c_ubyte(struct.unpack("<B",data.read(1))[0])
        self.x = (byte & 1) > 0
        self.y = (byte & 2) > 0
        self.z = (byte & 4) > 0
        self.w = (byte & 8) > 0

    def createflags(self) -> ctypes.c_ubyte:
        flags: ctypes.c_ubyte = ctypes.c_ubyte(0)
        flags |= (1 if self.x else 0)
        flags |= (2 if self.y else 0)
        flags |= (4 if self.z else 0)
        flags |= (8 if self.w else 0)
        return flags
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<B", self.createflags()))
    


class int(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value

    def read(self,data: BytesIO):
        self.x = struct.unpack("<i", data.read(4))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<i", self.x))

class int2(int):
    y: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.y = struct.unpack("<i", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<i", self.y))

class int3(int2):
    z: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.z = struct.unpack("<i", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<i", self.z))
    
class int4(int3):
    w: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.w = struct.unpack("<i", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<i", self.w))






class uint(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value

    def read(self,data: BytesIO):
        self.x = struct.unpack("<I", data.read(4))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<I", self.x))

class uint2(uint):
    y: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.y = struct.unpack("<I", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<I", self.y))

class uint3(uint2):
    z: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.z = struct.unpack("<I", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<I", self.z))
    
class uint4(uint3):
    w: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().write(data)
        self.w = struct.unpack("<I", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<I", self.w))





class ulong(ResoType):
    x: int = 0

    def __int__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value

    def read(self,data: BytesIO):
        self.x = struct.unpack("<Q", data.read(8))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<Q", self.x))


class long(ResoType):
    x: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.x = struct.unpack("<q", data.read(8))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<q", self.x))

class long2(long):
    y: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.y = struct.unpack("<q", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<q", self.y))

class long3(long2):
    z: int = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.z = struct.unpack("<q", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<q", self.z))
    
class long4(long3):
    w: int = 0

    def __init__(self):
        pass

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.w = struct.unpack("<q", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<q", self.w))








class double(ResoType):
    x: float = 0

    def __float__(self):
        return self.x

    def __init__(self,value=0):
        self.x = value

    def read(self,data: BytesIO):
        self.x = struct.unpack("<d", data.read(8))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<d", self.x))

class double2(double):

    y: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.y = struct.unpack("<d", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<d", self.y))

class double3(double2):
    z: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.z = struct.unpack("<d", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<d", self.z))
    
class double4(double3):
    w: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.w = struct.unpack("<d", data.read(8))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<d", self.w))

class double2x2(ResoType):
    m00: float = 0
    m01: float = 0
    m10: float = 0
    m11: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m10,self.m11 = struct.unpack("<dddd", data.read(8*(2*2)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<dddd", self.m00,self.m01, self.m10,self.m11))


class double3x3(double2x2):
    m02: float = 0
    m12: float = 0
    m22: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m02,self.m10,self.m11,self.m12,self.m20,self.m21,self.m22 = struct.unpack("<ddddddddd", data.read(8*(3*3)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<ddddddddd", self.m00,self.m01,self.m02,self.m10,self.m11,self.m12,self.m20,self.m21,self.m22))


class double4x4(double3x3):
    m03: float = 0
    m13: float = 0
    m23: float = 0
    m33: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m02,self.m03,self.m10,self.m11,self.m12,self.m13,self.m20,self.m21,self.m22,self.m23,self.m30,self.m31,self.m32,self.m33 = struct.unpack("<dddddddddddddddd", data.read(8*(4*4)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<dddddddddddddddd", self.m00,self.m01,self.m02,self.m03,self.m10,self.m11,self.m12,self.m13,self.m20,self.m21,self.m22,self.m23,self.m30,self.m31,self.m32,self.m33))

class doubleQ(double4):

    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        super().write(data)
    
    @classmethod
    def read(cls, data: BytesIO):
        super().read(data)





class float(ResoType):
    x: float = 0

    def __float__(self):
        return self.x

    def __init__(self, value=0):
        self.x = value

    def read(self,data: BytesIO):
        self.x = struct.unpack("<f", data.read(4))[0]
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<f", self.x))

class float2(float):

    y: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.y = struct.unpack("<f", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<f", self.y))

class float3(float2):
    z: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.z = struct.unpack("<f", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<f", self.z))
    
class float4(float3):
    w: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        super().read(data)
        self.w = struct.unpack("<f", data.read(4))[0]
    
    def write(self, data: BytesIO):
        super().write(data)
        data.write(struct.pack("<f", self.w))

class float2x2(ResoType):
    m00: float = 0
    m01: float = 0
    m10: float = 0
    m11: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m10,self.m11 = struct.unpack("<ffff", data.read(4*(2*2)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<ffff", self.m00,self.m01, self.m10,self.m11))


class float3x3(float2x2):
    m02: float = 0
    m12: float = 0
    m22: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m02,self.m10,self.m11,self.m12,self.m20,self.m21,self.m22 = struct.unpack("<fffffffff", data.read(4*(3*3)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<fffffffff", self.m00,self.m01,self.m02,self.m10,self.m11,self.m12,self.m20,self.m21,self.m22))


class float4x4(float3x3):
    m03: float = 0
    m13: float = 0
    m23: float = 0
    m33: float = 0

    def __init__(self):
        pass

    def read(self,data: BytesIO):
        self.m00,self.m01,self.m02,self.m03,self.m10,self.m11,self.m12,self.m13,self.m20,self.m21,self.m22,self.m23,self.m30,self.m31,self.m32,self.m33 = struct.unpack("<ffffffffffffffff", data.read(4*(4*4)))
    
    def write(self, data: BytesIO):
        data.write(struct.pack("<ffffffffffffffff", self.m00,self.m01,self.m02,self.m03,self.m10,self.m11,self.m12,self.m13,self.m20,self.m21,self.m22,self.m23,self.m30,self.m31,self.m32,self.m33))

class floatQ(float4):

    def __init__(self):
        pass
    
    def write(self, data: BytesIO):
        super().write(data)
    
    @classmethod
    def read(cls, data: BytesIO):
        super().read(data)