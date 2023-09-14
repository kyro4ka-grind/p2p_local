import socket
import time
import BalanceControl
import BaseUser
import concurrent.futures as pool
import logging
import Keys
from datetime import datetime
import FileManager
import selectors

users=[]
class TCP_client:
    def __init__(self):
        #Socket
        self._myConnections=BaseUser.CreateSocketsPull()
        '''
        {addr:(sock,lastActivityTime)}
        '''
        self._recvData={}
        '''
        {socket:data}
        '''
        self.sel=selectors.DefaultSelector()

    def Accepting(self):
                logging.info('Accepting: start accepting')
                tcpSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcpSock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                tcpSock.bind((BaseUser.ip,BaseUser.tcpPort))
                tcpSock.setblocking(0)
                tcpSock.listen(100)
                self.sel.register(tcpSock,selectors.EVENT_READ,0)

                while True:
                    if BaseUser.EndProgram:
                        logging.info('Accepting: stop accepting')
                        return
                    events=self.sel.select(5)
                    for key,mask in events:
                        if key.fileobj==tcpSock:
                            connection,addr=key.fileobj.accept()
                            #Check ip
                            for el in BalanceControl.BalanceControl.clients.values():
                                if addr[0]==el.ip:
                                    connection.setblocking(0)
                                    self.sel.register(connection,selectors.EVENT_READ,self.Listening)
                                    self._recvData.update({connection:bytes()})
                                    logging.info('Accepting: user conected')
                                else:
                                    logging.info('Accepting: user rejected')
                                    connection.close()
                        else:
                            try:
                                key.data(key.fileobj,key.fileobj.recv(1024))
                                continue
                            except Exception:
                                key.fileobj.close()
                                self.sel.unregister(key.fileobj)
                                logging.info('Listening: listening ended')
                                del self._recvData[key.fileobj]
                                break
            
    def Listening(self,client:socket.socket,data):
        try:
            self._recvData[client]+=data
        except Exception:
            logging.critical('Tcp listening: ',exc_info=True)

    def ProcessingRequest(self):
            logging.info('Tcp proc: start tcp processing')
            while True:
                try:
                    #End program
                    if BaseUser.EndProgram:
                        logging.info('Tcp proc: stop tcp processing')
                        return
                    #Got data if ready
                    buff=''
                    '''
                    (data,socket)
                    '''
                    for el in self._recvData:
                        dataBuff=self._recvData[el]
                        if (dataBuff!=bytes())and(chr(dataBuff[-1])=='\n'):
                            buff=(dataBuff[:-1],el)
                            self._recvData[el]=bytes()
                    if buff=='':
                        time.sleep(1)
                        continue

                    #Check id
                    id=buff[0][:32]
                    client=BalanceControl.BalanceControl.clients.get(id)
                    if client==None:
                        logging.info('Tcp proc: id check fail')
                        self.sel.unregister(buff[1])
                        buff[1].shutdown(socket.SHUT_RDWR)
                        buff[1].close()
                        del self._recvData[buff[1]]
                        continue

                    #Find shared key
                    sharedKey=client.sharedKey

                    #Decode msg
                    buff=(Keys.DecodeAesCBC(buff[0][32:],sharedKey),buff[1])
                    #Decode error
                    if buff[0]=='':
                        logging.error('Tcp proc: decode msg error')
                        self.sel.unregister(buff[1])
                        buff[1].shutdown(socket.SHUT_RDWR)
                        buff[1].close()
                        del self._recvData[buff[1]]
                        continue

                    #Action
                    action=buff[0][0]
                    logging.info('Tcp proc: came action')
                    
                    #Get users
                    if action==BaseUser.Actions.GetUsers.value:
                        clientSize=125#id[32]+ip[7]+port[2]+pk[32]+nick[32]+CrTime[24]
                        numOfClients=len(buff[0])/clientSize
                        logging.info('Tcp proc: got clients')
                        clients=buff[0]
                        count=0
                        endIndex=0
                        while count<numOfClients:
                            id=clients[endIndex:endIndex+32]
                            ip=BaseUser.BytesToIp(clients[endIndex+32:endIndex+35])
                            port=int.from_bytes(clients[endIndex+35:endIndex+37],'big')
                            publicKey=clients[endIndex+37:endIndex+69]
                            nick=clients[endIndex+69:endIndex+101].decode('utf-8')
                            wasInTouch=BaseUser.StrToTime(clients[endIndex+101:endIndex+125].decode('utf-8'))
                            endIndex+=clientSize
                            #Check client
                            if BalanceControl.BalanceControl.clients.get(id)==None:
                                sharedKey=Keys.SharedKey(publicKey)
                                client=BalanceControl.Client(ip,port,0,publicKey,nick,wasInTouch,sharedKey)
                                BalanceControl.BalanceControl.clients.update({id:client})
                                logging.info('Tcp proc: clients have been updated')
                        del self._recvData[buff[1]]
                        continue
                    
                    #Send msg
                    if action==BaseUser.Actions.SendMsg.value:
                        msg=buff[0][1:].decode('utf-8')
                        FileManager.WriteToFile(client.nickname,msg,client.nickname)
                        logging.info('Tcp proc: get tcp msg')
                        continue

                    #Unknown request
                    else:
                        logging.info('Tcp proc: unknown request')
                        self.sel.unregister(buff[1])
                        buff[1].shutdown(socket.SHUT_RDWR)
                        buff[1].close()
                        del self._recvData[buff[1]]
                        continue
                    
                except Exception:
                    logging.error('Tcp proc: ',exc_info=True)
                    continue

    def WriteMessage(self,nickname:str,msg:str):
        try:
            #Check nickname
            ip=''
            port=0
            sharedKey=''
            nickname=BaseUser.CompleteNickname(nickname)
            for el in BalanceControl.BalanceControl.clients.values():
                if el.nickname==nickname:
                    ip=el.ip
                    port=el.port
                    sharedKey=el.sharedKey
                    break
            if ip=='':
                logging.info('WriteMessage: nickname not found')
                return -1
            #Check my connections
            sock=''
            for el in self._myConnections:
                #Connection already established
                if el==(ip,port):
                    sock=self._myConnections.get(el)[0]
                    self._myConnections.update({el:(sock,datetime.utcnow())})
                    break
            #No connections to this client
            if sock=='':
                #Find free sock
                for el in self._myConnections:
                    #Free sock
                    if isinstance(el,int):
                        sock=self._myConnections.get(el)[0]
                        del self._myConnections[el]
                        self._myConnections.update({(ip,port):(sock,datetime.utcnow())})
                        break
            if sock=='':
                #Releasing socket
                minTime=datetime.utcnow()
                addr=0
                for el in self._myConnections:
                    conBuff=self._myConnections.get(el)
                    if conBuff[1]>=minTime:
                        sock=conBuff[0]
                        minTime=conBuff[1]
                        addr=el
                del self._myConnections[addr]
                self._myConnections.update({(ip,port):(sock,datetime.utcnow())})
            #Encode msg
            msgBuff=msg
            msg=BaseUser.Actions.SendMsg.value.to_bytes(1,'big')+msg.encode('utf-8')
            iv,msg=Keys.AesCBC(msg+Keys.Crc32(msg),sharedKey)
            #Sending msg
            try:
                sock.send(BaseUser.id+msg+iv+'\n'.encode('utf-8'))
                logging.info('Write message: sucessful sended')
            except OSError:
                try:
                    sock.connect((ip,port))
                    sock.send(BaseUser.id+msg+iv+'\n'.encode('utf-8'))
                    logging.info('Write message: sucessful conected and sended')
                except TimeoutError:
                    logging.info('Write message: cant connect, timeout error')
                    return -2
            #Writing message to a file
            FileManager.WriteToFile(nickname,msgBuff,BaseUser.nickname)
            return 1
        except:
            logging.critical('Write message: ',exc_info=True)
