from datetime import datetime
from datetime import time
import time as t
import Keys
import BaseUser
import logging
from Crypto.Random import get_random_bytes
import FileManager
import socket

class Data:
    """
    Received information
    """
    def __init__(self,data,ip,port):
        self.data=data
        self.ip=ip
        self.port=port

class Client:
    """
    Client information
    """
    REG_BUFF_LIFETIME=time(0,0,15)
    USER_LIFETIME=time(0,0,20)

    def __init__(self,ip,port,regPort,pKey,nickname,creationTime,sKey=''):
        self.ip=ip
        self.port=port
        self.regPort=regPort
        self.publicKey=pKey
        self.sharedKey=sKey
        self.nickname=nickname
        self.wasInTouch=creationTime

class BalanceControl:
    """
    Control list users balance in the network
    {id:Client}
    """
    clients={}

    def __init__(self):
        self._regBuff={}
        self._dataQueue=[]

    def MulticastSending(self):
            logging.info('Mcst sending: start sending')
            while True:
                try:
                    t.sleep(5)
                    if len(BalanceControl.clients)==0:continue
                    msg=Keys.Signing(BaseUser.Actions.SendingNumOfUsers.value.to_bytes(1,'big')
                                +BaseUser.id
                                +(len(BalanceControl.clients)).to_bytes(2,'big'))
                    BaseUser.udpSock.sendto(msg,(BaseUser.MCAST_GRP, BaseUser.MCAST_PORT))
                    self.CheckLifetime()
                except Exception:
                    logging.info('Mcst sending: stop sending')
                    return

    def MulticastListening(self):
            logging.info('Mcst listening: start listening')
            while True:
                try:
                    data,(ip,port)=BaseUser.listeningSock.recvfrom(508)
                    if (ip==BaseUser.ip)and(port==BaseUser.udpPort):continue
                    logging.info('Mcst listening: message received')
                    self._dataQueue.insert(0,Data(data,ip,port))
                except Exception:
                    logging.info('Mcst listening: stop listening')
                    return

    def MulticastProcessing(self):
            logging.info('Mcst proc: start processing')
            while True:
                try:
                    if BaseUser.EndProgram:
                        logging.info('Mcst proc: stop processing')
                        return
                    if len(self._dataQueue)==0:
                        t.sleep(1)
                        continue
                    #Take message
                    buff=self._dataQueue.pop()
                    #Verify message
                    buff.data=Keys.Verify(buff.data)
                    #Failed verify
                    if buff.data=='':
                        logging.error('Mcst proc: signing data failed')
                        continue
                    #Take action
                    action=buff.data[0]
                    logging.info('Mcst proc: came action')
                    id=buff.data[1:33]

                    #Processing registration request
                    if action==BaseUser.Actions.Registration.value:
                        publicKey=buff.data[33:65]
                        nick=buff.data[65:97].decode('utf-8')
                        creationTime=BaseUser.StrToTime(buff.data[97:121].decode('utf-8'))
                        port=int.from_bytes(buff.data[121:],'big')
                        #Fail flags
                        flagFailId=False
                        flagFailAdress=False
                        flagFailNick=False

                        #Check regBuff
                        for el in self._regBuff:
                            client=self._regBuff.get(el)
                            if (client.wasInTouch==creationTime)and(el==id):
                                continue
                            #Id
                            if el==id:
                                #Old older
                                if client.wasInTouch<creationTime:
                                    flagFailId=True
                                else:
                                    del self._regBuff[el]
                                    continue
                            #Adress
                            if (client.ip==buff.ip) and (client.port==port):
                                #Old older
                                if client.wasInTouch<creationTime:
                                    flagFailAdress=True
                                else:
                                    del self._regBuff[el]
                                    continue
                            #Nickname
                            if client.nickname==nick:
                                #Old older
                                if client.wasInTouch<creationTime:
                                    flagFailNick=True
                                else:
                                    del self._regBuff[el]
                                    continue
                        #Status
                        status=''
                        if flagFailId:
                            logging.info('Mcst proc: flagFailId')
                            status=BaseUser.Actions.FailId.value
                        else:
                            if flagFailAdress:
                                logging.info('Mcst proc: flagFailAdress')
                                status=BaseUser.Actions.FailAdress.value
                            else:
                                if flagFailNick:
                                    logging.info('Mcst proc: flagFailNick')
                                    status=status=BaseUser.Actions.FailNickname.value
                                else:
                                    #Check clients
                                    logging.info('Mcst proc: no flags')
                                    status=self.CheckClientsForReg(id,nick,buff.ip,port)

                        sharedKey=Keys.SharedKey(publicKey)
                        if status==BaseUser.Actions.Ok.value:
                            self._regBuff.update({id:Client(buff.ip,port,buff.port,publicKey,nick,creationTime,sharedKey)})
                            logging.info('Mcst proc: regBuff updated')
                        
                        answer=(status.to_bytes(1,'big')
                                    +BaseUser.id
                                    +BaseUser.nickname.encode('utf-8')
                                    +(len(BalanceControl.clients)+1).to_bytes(2,'big')
                                    +BaseUser.tcpPort.to_bytes(2,'big'))
                        crc32=Keys.Crc32(answer)
                        iv,answer=Keys.AesCBC(answer+crc32,sharedKey)
                        answer+=iv+bytes(Keys.publicKey)
                        BaseUser.udpSock.sendto(answer,(buff.ip,buff.port))
                        continue
                    
                    #Processing code OK
                    if action==BaseUser.Actions.Ok.value:
                        new=self._regBuff.get(id)
                        if (new!=None)and(new.ip==buff.ip)and(new.regPort==buff.port):
                            #Shared key
                            new.sharedKey=Keys.SharedKey(new.publicKey)
                            BalanceControl.clients.update({id:new})
                            logging.info('Mcst proc: client added')
                            del self._regBuff[buff.data[1:33]]
                        continue
                    
                    #Client identification
                    client=BalanceControl.clients.get(id)
                    if (client==None)or(client.ip!=buff.ip)or(client.regPort!=buff.port):
                        logging.info('Mcst proc: the request from unknown client has been rejected')
                        continue
                    addr=(client.ip,client.port)

                    #Sending num of users
                    if action==BaseUser.Actions.SendingNumOfUsers.value:
                        try:
                            BalanceControl.clients[id].wasInTouch=datetime.utcnow()
                            numOfClients=int.from_bytes(buff.data[33:],'big')
                            if numOfClients>len(BalanceControl.clients):
                                action=BaseUser.Actions.RequestForUsers.value.to_bytes(1,'big')
                                #Encode message
                                msg=get_random_bytes(11)
                                msg=msg+Keys.Crc32(msg)
                                iv,msg=Keys.AesCBC(msg,client.sharedKey)
                                #Send
                                BaseUser.udpSock.send(action+BaseUser.id+msg+iv)
                                logging.info('Mcst proc: clients request sended')
                            continue
                        except:
                            logging.error('Mcst proc: ',exc_info=True)
                            continue

                    #Get request for users
                    if (action==BaseUser.Actions.RequestForUsers.value):
                        buff=Keys.DecodeAesCBC(buff.data[1:],client.sharedKey)
                        #Decode failed
                        if buff=='':
                            logging.info('Mcst proc: decode failed')
                            continue
                        clients=BaseUser.Actions.GetUsers.value.to_bytes(1,'big')
                        for el in BalanceControl.clients:
                            client=BalanceControl.clients.get(el)
                            #This user
                            if (el==id):continue
                            clients+=(el
                                    +BaseUser.IpToBytes(client.ip)
                                    +client.port.to_bytes(2,'big')
                                    +client.publicKey
                                    +client.nickname.encode('utf-8')
                                    +BaseUser.TimeToStr(client.wasInTouch).encode('utf-8'))
                        #Encode & send clients
                        clients=clients+Keys.Crc32(clients)
                        iv,clients=Keys.AesCBC(clients,sharedKey)
                        #Create sock
                        tcpServiceSock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        tcpServiceSock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                        tcpServiceSock.bind((BaseUser.ip,BaseUser.tcpServicePort))    
                        tcpServiceSock.connect(addr)
                        #Send
                        tcpServiceSock.send(BaseUser.id+clients+iv+'\n'.encode('utf-8'))
                        logging.info('Tcp proc: sending clients')
                        tcpServiceSock.shutdown(socket.SHUT_RDWR)
                        tcpServiceSock.close()
                        continue
                    
                    #Unknown request
                    else:
                        logging.info('Mcst proc: unknown request: '+str(action))
                        continue
                except Exception:
                    logging.critical('Mcst proc error: ',exc_info=True)
                    continue

    def CheckClientsForReg(self,id,nick,ip,port):
        try:
            status=BaseUser.Actions.Ok.value
            #Id
            if (BalanceControl.clients.get(id)==None) and (BaseUser.id!=id):
                #Adress
                if (BaseUser.ip==ip) and (BaseUser.tcpPort==port):
                    status=BaseUser.Actions.FailAdress.value
                    return status
                else:
                    for el in BalanceControl.clients.values():
                        if (el.ip==ip) and (el.port==port):
                            status=BaseUser.Actions.FailAdress.value
                            return status
                #Nickname
                if BaseUser.nickname==nick:
                    status=BaseUser.Actions.FailNickname.value
                    return status
                else:
                    for el in BalanceControl.clients.values():
                        if el.nickname==nick:
                            status=BaseUser.Actions.FailNickname.value
                            return status
            else:
                status=BaseUser.Actions.FailId.value
            return status
        except:
            logging.critical('Check clients for reg: ',exc_info=True)

    def CheckLifetime(self):
        """
        regBuff clients live 15 sec
        clients live 20 sec
        """
        try:
            deleteList=[]
            #Check reg buff
            for el in self._regBuff:
                if abs((datetime.utcnow()-self._regBuff.get(el).wasInTouch).seconds)>Client.REG_BUFF_LIFETIME.second:
                    deleteList.append(el)
            #Deleting
            for el in deleteList:
                del self._regBuff[el]
            deleteList.clear()
            #Check clients
            for el in BalanceControl.clients:
                if (abs(datetime.utcnow()-BalanceControl.clients.get(el).wasInTouch)).seconds>Client.USER_LIFETIME.second:
                    deleteList.append(el)
            #Deleting
            for el in deleteList:
                nickname=BalanceControl.clients.get(el).nickname
                FileManager.MoveToOld(nickname)
                del BalanceControl.clients[el]
                logging.info('Check lifetime: client deleted')
        except Exception:
            logging.critical('Check lifetime: ',exc_info=True)