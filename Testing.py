import struct
from graphviz import Digraph
import os
import xxhash
import Keys
from datetime import datetime
import math

path='C:\\Users\\Zuzu\\Desktop\\Games\\Hogwarts Legacy\\Phoenix\\Content\\Paks'
filename='pakchunk10-WindowsNoEditor.ucas'
os.chdir(path)
with open(filename,mode='rb') as file:
    fileSize=os.path.getsize(filename)
    fileSizeBuff=fileSize
    if fileSize>10_485_760:#10mb
        packageSize=math.ceil(fileSize/10240)
        packageSize-=packageSize%16+5
    print('Размер файла: '+str(fileSize)+' байт или '
          +str(fileSize/1024/1024/1024)+' гб')
    print('Размер пакета: '+str(packageSize)+' байт')
    time=datetime.now()
    while fileSize>0:
        buff=file.read(packageSize)
        fileSize-=packageSize
        crc32=Keys.Crc32(buff)
    # crc32=Keys.Crc32(file.read())
    time2=datetime.now()
    secs=(time2-time).seconds
    print('Хеширование файла заняло: '+str(secs)+' секунд')
    print('Скорость хеширования составила: '+str(fileSizeBuff/secs)+' байт/сек или '
          +str((fileSizeBuff/1024/1024/1024)/secs)+' гб/сек')