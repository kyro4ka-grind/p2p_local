import os
import logging
import BalanceControl
from datetime import datetime
import BaseUser
import shutil

def WriteToFile(nick,msg,nickFrom):
    '''
    Write user messages to bin file\n
    if he is online now
    '''
    try:
        nick=BaseUser.TruncateNickname(nick)
        nickFrom=BaseUser.TruncateNickname(nickFrom)
        mainDirectory=os.getcwd()
        #Attempt to create file
        if not os.path.isdir(nick):
            os.mkdir(nick)
            os.chdir(nick)
            os.mkdir('Messages')
            os.mkdir('Files')
            #Go back
            os.chdir(mainDirectory)
        #Write into file
        os.chdir(nick)
        os.chdir('Messages')
        with open('messages.bin',mode='ab',buffering=0) as file:
            file.write((nickFrom+' ('+str(datetime.now())+'):\t'+msg+'\n').encode('utf-8'))
        #Go back    
        os.chdir(mainDirectory)
    except:
        logging.critical('WriteToFile: ',exc_info=True)

def ReadFromFile(nick):
    '''
    Read user messages from bin file\n
    if he is online
    '''
    try:
        nick=BaseUser.CompleteNickname(nick)
        #Check user status
        flag=False
        for el in BalanceControl.BalanceControl.clients.values():
            if el.nickname==nick:
                flag=True
                break
        #User offline
        if flag==False:return 0
        nick=BaseUser.TruncateNickname(nick)
        #Open directory and read file
        mainDirectory=os.getcwd()
        #No messages
        if not os.path.isdir(nick):return -1
        os.chdir(nick)
        os.chdir('Messages')
        with open('messages.bin',mode='rb',buffering=0) as file:
            #Go back    
            os.chdir(mainDirectory)
            return file.readlines()
    except:
        logging.critical('ReadFromFile: ',exc_info=True)

def MoveToOld(nickname):
    '''
    When another user became offline\n
    move his messages to Old directory\n
    and add datetime to file name
    '''
    try:
        nickname=BaseUser.TruncateNickname(nickname)
        #Check Old directory
        if not os.path.isdir('Old'):
            os.mkdir('Old')
        #Check nickname directory
        if not os.path.isdir(nickname):
            return
        #Rename file
        newFilename=nickname+' ('+BaseUser.TimeToStr(datetime.now())+')'
        os.rename(nickname,newFilename)
        #Move file
        shutil.move(newFilename,'Old')
    except:
        logging.critical('ReplaceToOld: ',exc_info=True)

def ChooseOldDirectories(nickname):
    try:
        oldDirecories=os.listdir('Old')
        choosenDirectories=[]
        for filename in oldDirecories:
            nicknameBuff=''
            for symb in filename:
                if symb==' ':
                    if nicknameBuff==nickname:
                        choosenDirectories.append(filename)
                    break
                nicknameBuff+=symb
        return choosenDirectories
    except:
        logging.critical('ChooseOldDirectories: ',exc_info=True)

def ReadFromOld(filename):
    try:
        mainDirectory=os.getcwd()
        os.chdir('Old')
        os.chdir(filename)
        os.chdir('Messages')
        with open('messages.bin',mode='rb',buffering=0) as file:
                #Go back    
                os.chdir(mainDirectory)
                return file.readlines()
    except:
        logging.critical('ReadFromOld: ',exc_info=True)