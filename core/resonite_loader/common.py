import ctypes
import typing
import struct 
from io import BytesIO

def ReadCSharp_str(data: BytesIO) -> str:
    charamount = read7bitEncoded_int(data)
    string: str = data.read(charamount).decode('utf-8', errors="replace")
    print("read string: "+string)
    return string

def WriteCSharp_str(data: BytesIO, string: str) -> str:
    write7bitEncoded_int(len(string))
    return data.write(string.encode("utf-8", errors="replace"))

def read7bitEncoded_ulong(data: BytesIO) -> int:
        num: int = int(0)
        num2: int = 0
        flag: bool = True
        
        while (flag):
            b: int = int(struct.unpack('<B', data.read(1))[0])
            flag = ((b & 128) > 0)
            num |= ((b & 127) << num2)
            num2 += 7
            if not flag:
                break

        return num

def read7bitEncoded_int(data: BytesIO) -> int:
        num: int= int(0)
        num2:int = int(0)
        while (num2 != 35):
            b: int = int(struct.unpack('<B', data.read(1))[0])
            num |= int(b & 127) << num2
            num2 += 7
            if ((b & 128) == 0):
                return num
        return -1

def write7bitEncoded_ulong(data: BytesIO, integer: int) -> None:
    while integer > int(0):
        b: int = ctypes.c_ubyte(integer & int(127))
        integer >>= 7
        if integer > int(0):
            b |= 128
        data.write(b)
        if integer <= int(0):
            return

def write7bitEncoded_int(data: BytesIO, value: int) -> None:
    num: int = int(value)
    while(num >= int(128)):
        data.write(int(num | int(128)))
        num >>= 7
    data.Write(int(num))