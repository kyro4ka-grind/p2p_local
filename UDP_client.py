from datetime import datetime
import time as t
from BalanceControl import*
from TCP_client import*
import Keys
import BaseUser
import statistics
import logging
import select

logging.basicConfig(level=logging.INFO, filename="log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
logging.info('Ip: '+BaseUser.ip)

class UDP_client:
    def __init__(self):
        self._regAnswers=[]
        '''
        Type: BalanceControl.Data
        '''
        self._clientsRequests={}
        '''
        {id:(numOfClients-action)}
        '''

    def Registration(self):
        """
        Registration new user in network
        """
        try:
            BaseUser.nickname=BaseUser.CompleteNickname(BaseUser.nickname)
            failIdTimes=0
            while True:
                BaseUser.id=BaseUser.GenerateId()
                creationTime=BaseUser.TimeToStr(datetime.utcnow())
                regMessage=Keys.Signing(BaseUser.Actions.Registration.value.to_bytes(1,'big')
                                                +BaseUser.id
                                                +bytes(Keys.publicKey)
                                                +BaseUser.nickname.encode('utf-8')
                                                +creationTime.encode('utf-8')
                                                +BaseUser.tcpPort.to_bytes(2,'big'))
                #Sending 5 sec
                logging.info('Registration: start sending')
                t1=datetime.utcnow()
                t2=datetime.utcnow()
                while (t2-t1).total_seconds()<5:
                    BaseUser.udpSock.sendto(regMessage,(BaseUser.MCAST_GRP, BaseUser.MCAST_PORT))
                    t2=datetime.utcnow()
                    t.sleep(0.5)
                t.sleep(0.6)
                logging.info('Registration: end sending')

                #Concluding
                numOfUsers=0
                if len(self._clientsRequests)!=0:
                    numOfUsers=statistics.fmean(el[0] for el in self._clientsRequests.values())
                majority=numOfUsers//2+1
                if numOfUsers==0:
                    logging.info('Registration: success')
                    return 0
                #Sum status for registration 50%+1
                regOk=0
                regIdFail=0
                regNickFail=0
                regAdressFail=0
                for el in self._clientsRequests.values():
                    if el[1]==BaseUser.Actions.Ok.value:
                        regOk+=1
                        continue
                    if el[1]==BaseUser.Actions.FailId.value:
                        regIdFail+=1
                        continue
                    if el[1]==BaseUser.Actions.FailNickname.value:
                        regNickFail+=1
                        continue
                    if el[1]==BaseUser.Actions.FailAdress.value:
                        regAdressFail+=1

                if regOk>=majority:
                    finalOkMsg=Keys.Signing(BaseUser.Actions.Ok.value.to_bytes(1,'big')+BaseUser.id)
                    BaseUser.udpSock.sendto(finalOkMsg,(BaseUser.MCAST_GRP, BaseUser.MCAST_PORT))
                    logging.info('Registration: success')
                    return 0
                if regIdFail>=majority:
                    BalanceControl.BalanceControl.clients.clear()
                    self._clientsRequests.clear()
                    self._regAnswers.clear()
                    logging.info('Registration: id fail')
                    failIdTimes+=1
                    if failIdTimes==3:
                        return -1
                    continue
                if regAdressFail>=majority:
                    logging.info('Registration: adress fail')
                    return 1
                if regNickFail>=majority:
                    logging.info('Registration: nick fail')
                    BalanceControl.BalanceControl.clients.clear()
                    return 2
                else:
                    logging.info('Registration: not enough users called')
                    return 3
        except Exception:
            logging.critical('Registration error: ',exc_info=True)

    def ListeningRegAnswer(self):
        """
        Listening registration answer
        """
        try:
            BaseUser.udpSock.setblocking(0)
            outputs=[]
            inputs=[BaseUser.udpSock]
            t1=datetime.utcnow()
            t2=datetime.utcnow()
            #Listening 5 sec
            logging.info('Listening reg answ: start listening')
            while (t2-t1).total_seconds()<5:
                t2=datetime.utcnow()
                readable,writeable,exceptional=select.select(inputs,outputs,inputs,1)
                for sock in readable:
                    (data,(ip,port))=sock.recvfrom(508)
                    logging.info('Listening reg answ: got answer')
                    self._regAnswers.insert(0,BalanceControl.Data(data,ip,port))
            BaseUser.udpSock.setblocking(1)
            logging.info('Listening reg answ: end listening')
        except Exception:
            logging.critical('Listening reg answ error: ',exc_info=True)

    def ProcessingRegAnswer(self):
        try:
            t1=datetime.utcnow()
            t2=datetime.utcnow()
            while (t2-t1).total_seconds()<5:
                t2=datetime.utcnow()
                if len(self._regAnswers)==0:
                    t.sleep(0.5)
                    continue
                #Take message
                buff=self._regAnswers.pop()
                publicKey=buff.data[-32:]
                sharedKey=Keys.SharedKey(publicKey)
                buff.data=Keys.DecodeAesCBC(buff.data[:-32],sharedKey)
                #Failed
                if buff.data=='':
                    logging.error('Proc reg answ: decode failed')
                    continue
                    
                #Take info
                status=buff.data[0]
                id=buff.data[1:33]
                nick=buff.data[33:65].decode('utf-8')
                numOfClients=int.from_bytes(buff.data[65:67],'big')
                port=int.from_bytes(buff.data[67:],'big')
                #Updating
                BalanceControl.BalanceControl.clients.update({id:BalanceControl.Client(buff.ip,port,buff.port,publicKey,nick,datetime.utcnow(),sharedKey)})
                self._clientsRequests.update({id:(numOfClients,status)})   
        except Exception:
            logging.critical('Processing reg answ error: ',exc_info=True)