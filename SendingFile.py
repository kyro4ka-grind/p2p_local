import socket
import os
import selectors
from datetime import datetime
import logging
import math
import BaseUser
import Keys
import BalanceControl

def BytesInInt(num:int):
    return math.ceil(num.bit_length()/8)

def SendFile(filename,recId,filePath=os.getcwd(),recPort=1444,sendingPort=1333):
    try:
        sendingSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sendingSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sendingSock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1_048_576)#1mb
        sendingSock.bind((BaseUser.ip,sendingPort))

        directoryPath=os.getcwd()
        if not os.path.isdir(filePath):return 0
        else:
            os.chdir(filePath)
            with open(filename,mode='rb') as file:
                fileSize=os.path.getsize(filename)
                #Go back into directory    
                os.chdir(directoryPath)
                filesizeBytes=BytesInInt(fileSize)
                lenPayLoad=985-len(filename)-filesizeBytes
                greetings=(len(filename).to_bytes(1,'big')
                           +filename.encode('utf-8')
                           +filesizeBytes.to_bytes(1,'big')
                           +fileSize.to_bytes(filesizeBytes,'big')
                           +file.read(lenPayLoad))
                #Encode
                client=BalanceControl.BalanceControl.clients.get(recId)
                sharedKey=client.sharedKey
                recIp=client.ip
                iv,greetings=Keys.AesCBC(greetings+Keys.Crc32(greetings),sharedKey)
                greetings=BaseUser.id+greetings
                #Send file
                sendingSock.connect((recIp,recPort))
                print('Отправляем: '+str(fileSize/1024/1024)+' мб...')
                #Sending
                packageSize=1003
                if fileSize>10_485_760:#10mb
                    packageSize=math.ceil(fileSize/10240)
                    packageSize-=packageSize%16+5#crc32+1(for aes block size 16)
                print('Размер отправляемых пакетов: '+str(packageSize))
                #Greetings
                sended=sendingSock.send(greetings+iv)
                #Main
                remainedSend=fileSize-lenPayLoad
                while remainedSend>packageSize:
                    buff=file.read(packageSize)
                    iv,msg=Keys.AesCBC(buff+Keys.Crc32(buff),sharedKey)
                    sended+=sendingSock.send(msg+iv)
                    remainedSend-=packageSize
                buff=file.read()
                iv,msg=Keys.AesCBC(buff+Keys.Crc32(buff),sharedKey)
                sended+=sendingSock.send(msg+iv)
                sendingSock.shutdown(socket.SHUT_RDWR)
                sendingSock.close()
                print('Отправлено: '+str(sended/1024/1024)+' мб.')
            return 1
    except:
         logging.critical('SendingFile: ',exc_info=True)
         return -1

#Data
sel=selectors.DefaultSelector()
connectionData={}
'''
{connection:recvSize,file,alreadyBeen,sharedKey,time}
'''
buffData={}
'''
{connection:data}
'''
def Accepting(recvPort=1444):
    try:
        acceptingSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        acceptingSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        acceptingSock.bind((BaseUser.ip,recvPort))
        acceptingSock.setblocking(0)
        acceptingSock.listen(1)
        sel.register(acceptingSock, selectors.EVENT_READ, RecvFile)
        startTime=datetime.utcnow()
        print('Слушаю...')
        while True:
            events=sel.select(5)
            if len(events)>0:
                startTime=datetime.utcnow()
            #End listening
            if (datetime.utcnow()-startTime).seconds==10:
                print('Прослушивание завершено.')
                sel.unregister(acceptingSock)
                acceptingSock.close()
                break
            for key,mask in events:
                if key.fileobj==acceptingSock:
                    connection,addr=key.fileobj.accept()
                    for el in BalanceControl.BalanceControl.clients.values():
                        if addr[0]==el.ip:
                            connection.setblocking(0)
                            connectionData.update({connection:(1040,0,False,0,0)})
                            buffData.update({connection:bytes()})
                            sel.register(connection,selectors.EVENT_READ,RecvFile)
                            print('Пользователь '+BaseUser.TruncateNickname(el.nickname)+' подключился.')
                        else:
                            logging.info('Accepting: user rejected')
                            connection.close()
                else:
                    buff=key.fileobj.recv(connectionData[key.fileobj][0])
                    if buff:
                        buffData[key.fileobj]+=buff
                        if len(buffData[key.fileobj])<connectionData[key.fileobj][0]:continue
                        key.data(key.fileobj)
                        continue
                    if buffData[key.fileobj]:
                        con=connectionData[key.fileobj]
                        if len(buffData[key.fileobj])<=con[0]:
                            con[1].write(Keys.DecodeAesCBC(buffData[key.fileobj],con[3]))
                        else:
                            con[1].write(Keys.DecodeAesCBC(buffData[key.fileobj][:con[0]],con[3]))
                            con[1].write(Keys.DecodeAesCBC(buffData[key.fileobj][con[0]:],con[3]))
                    sel.unregister(key.fileobj)
                    connectionData[key.fileobj][1].close()
                    print('Было потрачено: '+str((datetime.now()-connectionData[key.fileobj][4]).seconds)+' секунд.')
                    del connectionData[key.fileobj]
                    del buffData[key.fileobj]
                    print('Пользователь отключился.\nФайл успешно получен.')
                    return
    except:
        logging.critical('Accepting: ',exc_info=True)

def RecvFile(connection:socket.socket):
    try:
        connect=connectionData[connection]
        if connect[2]:
            if len(buffData[connection])>connect[0]:
                connect[1].write(Keys.DecodeAesCBC(buffData[connection][:connect[0]],connect[3]))
                buffData[connection]=buffData[connection][connect[0]:]
                return
            connect[1].write(Keys.DecodeAesCBC(buffData[connection],connect[3]))
            buffData[connection]=bytes()
        else:
            buff=buffData[connection]
            recId=buff[:32]
            client=BalanceControl.BalanceControl.clients.get(recId)
            sharedKey=client.sharedKey
            nickname=BaseUser.TruncateNickname(client.nickname)
            #Attempt to create file
            mainDirectory=os.getcwd()
            if not os.path.isdir(nickname):
                os.mkdir(nickname)
                os.chdir(nickname)
                os.mkdir('Messages')
                os.mkdir('Files')
                #Go back
                os.chdir(mainDirectory)
            #Create file
            os.chdir(nickname)
            os.chdir('Files')

            buff=Keys.DecodeAesCBC(buff[32:],sharedKey)
            lenFilename=buff[0]
            filename=buff[1:lenFilename+1].decode('utf-8')
            lenFilesize=buff[lenFilename+1]
            filesize=int.from_bytes(buff[lenFilename+2:lenFilename+2+lenFilesize],'big')
            print('Ожидается: '+str(filesize/1024/1024)+' мб.')
            file=open(filename,mode='ab')
            #Go back
            os.chdir(mainDirectory)
            file.write(buff[lenFilename+2+lenFilesize:])
            if filesize>10_485_760:#10mb
                recvBuffer=math.ceil(filesize/10240)
                recvBuffer-=recvBuffer%16-16
                print('Буфер получения: '+str(recvBuffer)+' байт.')
                connectionData.update({connection:(recvBuffer,file,True,sharedKey,datetime.now())})
            else:connectionData.update({connection:(1024,file,True,sharedKey,datetime.now())})
            buffData[connection]=bytes()
    except:
        logging.critical('RecvFile: ',exc_info=True)
        sel.unregister(connection)
        del connectionData[connection]
        connection.close()
        print('При получении возникла ошибка.')