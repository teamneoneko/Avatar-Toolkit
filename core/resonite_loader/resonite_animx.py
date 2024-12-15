from __future__ import annotations
from os import replace
from types import FrameType

import lz4.block
from . import resonite_types
from . import common

import typing
import struct 
from io import BytesIO

KeyframeInterpolation: dict[str, int] = {
    "Hold": 1,
    "Linear": 2,
    "Tangent": 3,
    "CubicBezier": 4
}

class KeyFrame():
    time: resonite_types.float = resonite_types.float(0)
    interpolation: resonite_types.int = resonite_types.int(0)
    value: resonite_types.ResoType
    left_tan: resonite_types.ResoType
    right_tan: resonite_types.ResoType


    def __getattr__(self, name: str):
        if name == "interpolation":
            interp: int = 0
            if (self["left_tan"] != None and self["right_tan"] != None):
                interp = 3
            

            return resonite_types.int(interp)
        return super().__getattribute__(name)

    
    

    def __init__(self):
        pass
    

    def RequiresTangents(self) -> bool:
        if KeyframeInterpolation[self.interpolation.x] == "Tangent" or KeyframeInterpolation[self.interpolation.x] == "CubicBezier":
            return True
        return False

class ResoTrack(resonite_types.ResoType):
    node: resonite_types.string = resonite_types.string("")
    property: resonite_types.string = resonite_types.string("")
    Owner: AnimX
    FrameType: type[resonite_types.ResoType]
    keyframes: list[KeyFrame] = []

    def __init__(self,FrameType):
        self.FrameType = FrameType

    def write(self, data: BytesIO):
        self.node.write(data)
        self.property.write(data)
        common.write7bitEncoded_ulong(data, len(self.keyframes))

    def read(self, data:BytesIO):
        self.node.read(data)
        self.property.read(data)
        track_amount: int = int(common.read7bitEncoded_ulong(data))
        for i in range(0, track_amount):
            key: KeyFrame = KeyFrame()
            key.value = self.FrameType()
            self.keyframes.append(key)

    def removeKeyframe(self, time: float | int) -> bool:
        """Takes a time and removes one with the same time"""
        if (time < 0):
            raise IndexError("Keyframe time cannot be lower than 0. Value: " + str(time))
        if(type(time) == float):
            num: int = -1
            for num2 in range(0,len(self.keyframes)):
                if (self.keyframes[num2].time.x == float(time)):
                    num = num2
            
            if num == -1:
                return False

            self.keyframes.remove(self.keyframes[num])
            return True
        else:
            if (int(time) >= len(self.keyframes)):
                raise IndexError("Keyframe time cannot be bigger than the amount of keyframes. Value: " + str(time))
            self.keyframes.remove(self.keyframes[int(time)])
            


    
    def replaceKeyframe(self, keyframe: KeyFrame) -> bool:
        """Takes a keyframe and replaces one with the same time"""
        if (keyframe.time.x < 0):
            raise IndexError("Keyframe time cannot be lower than 0. Value: " + str(keyframe.time.x))
        

        num: int = 0

        if (keyframe.time.x == self.keyframes[self.GetKeyframeIndex(keyframe.time.x)].time.x):
            num = len(self.keyframes)
        else:
            return False

        self.keyframes[num] = keyframe
        return True
    
    def addKeyframe(self, keyframe: KeyFrame) -> int:
        if (keyframe.time.x < 0):
            raise IndexError("Keyframe time cannot be lower than 0. Value: " + str(keyframe.time.x))
        num: int 
        if (len(self.keyframes) == 0):
            num = 0
        elif (keyframe.time.x >= self.keyframes[-1].time.x):
            num = len(self.keyframes)
        else:
            num = self.GetKeyframeIndex(keyframe.time.x) + 1

        self.keyframes.insert(num, keyframe)
        
        return num
    
    def GetKeyframeIndex(self, time:float | int)-> int:
        if(type(time) == float):
            if (len(self.keyframes) > 0):
                num: int = 0
                if (self.keyframes[-1].time < float(time)):
                    num = len(self.keyframes)
                
                while (num < len(self.keyframes) and self.keyframes[num].time < time):
                    num += 1
                
                return num - 1
            
            return -1
        else:
            return int(time)


class RawTrack(ResoTrack):
    interval: resonite_types.float = resonite_types.float(0)

    def __getattr__(self, name: str):
        if name == "interval":
            return self.Owner.interval.x
        return super().__getattribute__(name)

    def __init__(self, FrameType):
        super().__init__(FrameType)

    def write(self, data: BytesIO):
        super().write(data)
        self.interval.write(data)
        for key in self.keyframes:
            key.value.write(data)


    def read(self, data:BytesIO):
        super().read(data)
        self.interval.read(data)
        for key in self.keyframes:
            key.value.read(data)

    def addKeyframe(self, keyframe: KeyFrame) -> int:
        num: int = super().addKeyframe(keyframe)
        for i in range(0,len(self.keyframes)):
            self.keyframes[i].time = i
        return num
    def removeKeyframe(self, time: float | int) -> bool:
        success: bool = super().removeKeyframe(int(time))
        for i in range(0,len(self.keyframes)):
            self.keyframes[i].time = i
        return success


    

class DiscreteTrack(ResoTrack):
    
    def __init__(self, FrameType):
        super().__init__(FrameType)

    def write(self, data: BytesIO):
        super().write(data)


    def read(self, data:BytesIO):
        super().read(data)

    def addKeyframe(self, keyframe: KeyFrame) -> int:
        num: int = super().addKeyframe(keyframe)
        return num
    def removeKeyframe(self, time: float | int) -> bool:
        success: bool = super().removeKeyframe(time)
        return success
        



class CurveTrack(ResoTrack):
    interpolations: bool = False
    tangents: bool = False
    sharedinterpolation: resonite_types.int = resonite_types.int(-1)

    def __getattr__(self, name: str):
        if name == "interpolations":
            for key in self.keyframes:
                if key.interpolation.x  != self.sharedinterpolation.x:
                    return True 
        elif name == "tangents":
            for key in self.keyframes:
                if key.interpolation.x == 3 or key.interpolation.x == 4:
                    return True 
        return super().__getattribute__(name)

    def __init__(self, FrameType):
        super().__init__(FrameType)

    def write(self, data: BytesIO):
        super().write(data)
        resonite_types.byte((1 if self.interpolations else 0) | (2 if self.tangents else 0)).write(data)


        if(self.interpolations):
            for key in self.keyframes:
                key.interpolation.write(data)
        else:
            self.sharedinterpolation.write(data)

        for key in self.keyframes:
            if key.value == None:
                key.value = self.FrameType()
            key.value.write(data)
            key.time.write(data)
        
        if(self.tangents):
            for key in self.keyframes:
                key.left_tan.write(data)
                key.right_tan.write(data)

    def read(self, data:BytesIO):
        super().read(data)
        flags: int = struct.unpack("<B",data.read(1))[0]
        self.interpolations = (flags & 1) > 0
        self.tangents = (flags & 2) > 0

        print(str(self.interpolations))
        print(str(self.tangents))

        if(self.interpolations):
            for key in self.keyframes:
                key.interpolation.read(data)
        else:
            self.sharedinterpolation.read(data)

        for key in self.keyframes:
            print("key read!")
            if key.value == None:
                key.value = self.FrameType()
            key.value.read(data)
            key.time.read(data)
        
        if(self.tangents):
            for key in self.keyframes:
                if key.left_tan == None:
                    key.left_tan = self.FrameType()
                if key.right_tan == None:
                    key.right_tan = self.FrameType()
                key.left_tan.read(data)
                key.right_tan.read(data)
        



    

    


class BezierTrack(ResoTrack):
    """PLACE HOLDER CLASS, DO NOT USE"""


    def __init__(self, FrameType):
        super().__init__(FrameType)
        """PLACE HOLDER METHOD, DO NOT USE"""
        #raise Exception("BezierTrack track type is unsupported in resonite's code")

    def write(self, data: BytesIO):
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")
    def read(self, data:BytesIO):
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")
    
    def removeKeyframe(self, keyframe: KeyFrame) -> bool:
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")

    def replaceKeyframe(self, keyframe: KeyFrame) -> bool:
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")
    def addKeyframe(self, keyframe: KeyFrame) -> int:
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")
    
    def GetKeyframeIndex(self, time:float)-> int:
        """PLACE HOLDER METHOD, DO NOT USE"""
        raise Exception("BezierTrack track type is unsupported in resonite's code")
#This is weird, but thank you python - @989onan
TrackTypes: list[type] = [
    RawTrack,
    DiscreteTrack,
    CurveTrack,
    BezierTrack
]
    
#TODO: add all types here
#wooooo - @989onan
elementTypes: list[type[resonite_types.ResoType]] = [
    resonite_types.bool,
    resonite_types.bool2,
    resonite_types.bool3,
    resonite_types.bool4,
    resonite_types.byte,
    resonite_types.ushort,
    resonite_types.uint,
    resonite_types.ulong,
    resonite_types.sbyte,
    resonite_types.short,
    resonite_types.int,
    resonite_types.long,
    resonite_types.int2,
    resonite_types.int3,
    resonite_types.int4,
    resonite_types.uint2,
    resonite_types.uint3,
    resonite_types.uint4,
    resonite_types.long2,
    resonite_types.long3,
    resonite_types.long4,
    resonite_types.float,
    resonite_types.float2,
    resonite_types.float3,
    resonite_types.float4,
    resonite_types.floatQ,
    resonite_types.float2x2,
    resonite_types.float3x3,
    resonite_types.float4x4,
    resonite_types.double,
    resonite_types.double2,
    resonite_types.double3,
    resonite_types.double4,
    resonite_types.doubleQ,
    resonite_types.double2x2,
    resonite_types.double3x3,
    resonite_types.double4x4,
    resonite_types.color,
    resonite_types.color32,
    resonite_types.string
    ]


most_recent_AnimX_vers: int = 1
import lzma#HALLLOOOYAH HALLOYAH!! - @989onan
class AnimX():


    """
    To use Raw Track properly, please set interval (seconds between frames) after reading/creating.\n
    Represents data to be written to or read from an AnimX file. 
    """

    file_version: resonite_types.int = resonite_types.int()
    track_amount: resonite_types.int = resonite_types.int()
    global_duration: resonite_types.float = resonite_types.float()
    name: resonite_types.string = resonite_types.string()

    tracks: list[ResoTrack] = []

    interval: resonite_types.float = resonite_types.float(1/25) #default value

    def __init__(self):
        pass

    @classmethod
    def decompress_lzma(cls,data, format, filters) -> list:
        results = []
        while True:
            decomp = lzma.LZMADecompressor(format, None, filters)
            try:
                res = decomp.decompress(data)
            except lzma.LZMAError:
                if results:
                    break  # Leftover data is not a valid LZMA/XZ stream; ignore it.
                else:
                    raise  # Error on the first iteration; bail out.
            results.append(res)
            data = decomp.unused_data
            if not data:
                break
            if not decomp.eof:
                raise lzma.LZMAError("Compressed data ended before the end-of-stream marker was reached")
        return b"".join(results)
    
    def read(self, file: str) -> bool:
        """
        Takes an absolute file path and reads a binary animx file with it, and populates this class object with the data.
        """
        with open(file, 'rb') as filecontents:
            data: BytesIO = BytesIO(filecontents.read())
            magic_word = common.ReadCSharp_str(data)
            if magic_word != 'AnimX':
                print("AnimX != "+magic_word)
                return False
            self.file_version.read(data)
            if self.file_version.x > 1:
                raise Exception("AnimX version is higher than the supported one")
            
            self.track_amount.x = common.read7bitEncoded_ulong(data)
            self.global_duration.read(data)
            print("track amont: "+str(self.track_amount.x))
            print("file vers: "+str(self.file_version.x))

            self.name.read(data)
            print("name: "+self.name.x)
            
            match (struct.unpack('<B', data.read(1))[0]):
                case 0:
                    pass
                case 1:
                    from lz4.frame import decompress #why do you have to be a wheel? - @989onan
                    data =  BytesIO(decompress(data.read()))
                case 2:
                    
                    filters = [
                        {"id" : lzma.FILTER_LZMA1, #idfk man - @989onan
                            "dict_size" : 2097152,
                            "lc" : 3,
                            "lp" : 0,
                            "pb" : 2, # private static int posStateBits = 2; //<-froox engine derived.
                            "mode" : lzma.MODE_NORMAL,
                            "nice_len" : 32, # private static int numFastBytes = 32; //<-froox engine derived.
                            "mf" : lzma.MF_BT4,
                        },
                    ]
                    data.read(5) #fuck off headers - @989onan
                    data.read(8) #fuck off stream headers - @989onan
                    data.read(8) #fuck off stream headers - @989onan
                    filelmza: bytes = bytes(AnimX.decompress_lzma(data.read(), lzma.FORMAT_RAW, filters))
                    
                    print(f"decompressed bytes: {filelmza[:100]}")
                    data = BytesIO(filelmza)
                case _:
                    raise Exception("Invalid encoding")
            
            for i in range(0,self.track_amount.x):
                trackType2: int = 0
                num4: int = 0
                if (self.file_version == 0):
                    b: int = int(struct.unpack('<B', data.read(1))[0])
                    num3: int = int(b & 1)
                    trackType: int = 0
                    if (num3 != 0):
                        if (num3 != 1):
                            raise Exception("[InvalidDataException]: Invalid track type data: " + str(b))
                        trackType = 2
                    else:
                        trackType = 0
                    trackType2 = trackType
                    num4 = b >> 1
                else:
                    trackType2 = int(struct.unpack('<B', data.read(1))[0])
                    num4 = int(struct.unpack('<B', data.read(1))[0])
                try:
                    animationTrack = AnimX.GetTrackType(trackType2, elementTypes[num4], data)
                    animationTrack.Owner = self
                    self.tracks.append(animationTrack)
                except:
                    raise Exception("[InvalidDataException]: element type exception, beyond range: "+str(num4))

        return True

    def write(self, file: str) -> bool:
        """
        Takes an absolute file path and writes a binary animx file into it's contents, replacing them using this class's data.
        """
        with open(file, 'rb') as filecontents:
            data: BytesIO = BytesIO(filecontents)
            common.WriteCSharp_str(data, 'AnimX')
            self.file_version.x = most_recent_AnimX_vers #we wanna write an up to date file version type.
            self.file_version.write(data)
            
            self.track_amount.x = len(self.tracks)
            common.write7bitEncoded_ulong(self.track_amount.x)
            self.global_duration.write(data)


            self.name.write(data)

            data.write(struct.pack('<B', 0)) #default encoding, so we don't have to use lzma.
            
            
            for i in range(0,self.track_amount.x):

                data.write(struct.pack('<B', TrackTypes.index(type(self.tracks[i]))))
                data.write(struct.pack('<B', elementTypes.index(self.tracks[i].FrameType)))
                self.tracks[i].write(data)

        return True

    @classmethod
    def GetTrackType(cls, trackType2: int, value_type: type[resonite_types.ResoType], data: BytesIO) -> ResoTrack:
        Track = TrackTypes[trackType2](value_type)
        print(type(Track))
        print(value_type)
        Track.read(data)
        return Track
    
