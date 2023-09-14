import enum
import nacl.utils
import socket
from datetime import datetime
import struct
import BalanceControl
import FileManager
import selectors

def CreateSocket():
    pass

def CompleteNickname(nick:str):
    '''
    complete nickname with spaces up to 32 bytes
    '''
    while len(nick)<32:
        nick+=' '
    return nick

def TruncateNickname(nick:str):
    '''
    truncate nickname to original size
    '''
    indexEndSymb=32
    for i in range(32):
        if nick[i]==' ':
            indexEndSymb=i
            break
    return nick[:indexEndSymb]

def CheckCorrectNickname(nick:str):
    '''
    nickname must not contain spaces
    '''
    for el in nick:
        if el==' ':
            return 0
    return 1             
    
def GenerateId():
    return nacl.utils.random(32)

def Extract_ip():
        try:
            sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            sock.connect(('192.0.0.0', 0))
            Ip = sock.getsockname()[0]
        except Exception:
            Ip = '127.0.0.1'
        sock.close()
        return Ip

def BytesToIp(ip:bytes):
    return ip[0]+'.'+ip[2]+'.'+ip[2]+'.'+ip[3]

def IpToBytes(ip:str):
    ipBytes=bytes()
    num=''
    for el in ip:
        if el=='.':
            ipBytes+=int(num).to_bytes(1,'big')
            num=''
            continue
        num+=el
    ipBytes+=int(num).to_bytes(1,'big')
    return ipBytes

def TimeToStr(time:datetime):
    return time.strftime('%d-%m-%y %H-%M-%S.%f')

def StrToTime(time:str):
    return datetime.strptime(time,'%d-%m-%y %H-%M-%S.%f')

###############User information###############
EndProgram=False
#Socket selectors
sockSel=selectors.DefaultSelector()
#Input nickname
nickname=''
id=bytes()
#Adress
ip=Extract_ip()
udpPort=1234
tcpPort=1235
tcpServicePort=1236
serverAdress=('', 5005)
MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5005
#Sockets
#Udp
udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
udpSock.bind(('',udpPort))
udpSock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 5)
#Udp multicast listening sock
listeningSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listeningSock.bind(serverAdress)
group = socket.inet_aton(MCAST_GRP)
mreq = struct.pack('4sL', group, socket.INADDR_ANY)
listeningSock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,mreq)
#Tcp accepting/listening sock

#Tcp sending socks
def CreateSocketsPull(sizeSocketsPull=10,startPort=1237):
    myConnections={}
    for i in range(sizeSocketsPull):
        sockBuff=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockBuff.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sockBuff.bind((ip,startPort+i))
        myConnections.update({i:(sockBuff,0)})
    return myConnections
#Time
creationTime=0

def Exit():
    '''
    Exit program handler
    '''
    #Close sockets
    udpSock.close()
    listeningSock.close()
    #Write messages in Old
    for el in BalanceControl.BalanceControl.clients.values():
        FileManager.MoveToOld(el.nickname)
    exit()

class Actions(enum.Enum):
    """
    User actions
    """
    Registration=0
    RegRequest=1
    RegAnswer=2
    SendingNumOfUsers=3
    FailId=4
    FailNickname=5
    Ok=6
    FailAdress=7
    Clients=8
    SendMsg=9
    GetUsers=10
    RequestForUsers=11