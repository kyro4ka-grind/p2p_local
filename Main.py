from UDP_client import*
from BalanceControl import*
from TCP_client import*
import BaseUser
import concurrent.futures as pool
import os
import SendingFile

ClearConsole=lambda:print('\033c',end='')

def Registration(e:pool.ThreadPoolExecutor):
    udp=UDP_client()
    reg=e.submit(udp.Registration)
    e.submit(udp.ListeningRegAnswer)
    e.submit(udp.ProcessingRegAnswer)
    return reg.result()

def Working(e:pool.ThreadPoolExecutor,tcp:TCP_client):
    bc=BalanceControl.BalanceControl()
    e.submit(bc.MulticastListening)
    e.submit(bc.MulticastProcessing)
    e.submit(bc.MulticastSending)
    e.submit(tcp.Accepting)
    e.submit(tcp.ProcessingRequest)

def PrintUserList():
    count=0
    if len(BalanceControl.BalanceControl.clients)==0:
        return 0
    for el in BalanceControl.BalanceControl.clients.values():
        count+=1
        print(str(count)+'. Никнейм: '+BaseUser.TruncateNickname(el.nickname))
    print('\n')
    return 1

def UserInterface():
    with pool.ThreadPoolExecutor(max_workers=5) as e:
        tcp=TCP_client()
        print('Привет')
        while True:
            BaseUser.nickname=input('Введи желаемое имя пользователя\nДлина до 32 символов, к тому же не должно быть пробелов: ')
            if (len(BaseUser.nickname)>32)or(len(BaseUser.nickname)<1):continue
            if BaseUser.CheckCorrectNickname(BaseUser.nickname)==0:continue
            print('Начинаю регистрацию пользователя '+BaseUser.nickname+'...')
            regResult=Registration(e)
            if regResult==0:
                print('Регистрация прошла успешно!')
                Working(e,tcp)
                break
            if regResult==1:
                print('Регистрация не удалась: ошибка адреса, возможно вы уже в сети на этом устройстве.')
                exit()
            if regResult==2:
                print('Регистрация не удалась: ошибка никнейма.')
                continue
            if regResult==3:
                print('Регистрация не удалась: проблема сети.')
                exit()
            if regResult==-1:
                print('Регистрация не удалась: возможно кто-то подслушивает.')
                exit()
        while True:
            action=input('\nЧто будем делать?\n'
                    +'1. Просмотр списка пользователей.\n'
                    +'2. Отправить пользователю сообщение.\n'
                    +'3. Отправить пользователю файл.\n'
                    +'4. Получить файл от пользователя.\n'
                    +'5. Просмотреть историю сообщений от пользователей в сети\n'
                    +'6. Просмотреть старые переписки\n'
                    +'7. Выйти из приложения.\n'
                    +'Введите число: ')
            ClearConsole()
            try:
                action=int(action)
            except ValueError:
                print('Введите число (1-7).')
                continue
            if action==1:
                print('Пользователи в сети:')
                if PrintUserList()==0:
                    print('В сети нет никого, никого кроме вас...\n')
                continue
            if action==2:
                print('Пользователи в сети:')
                if PrintUserList()==0:
                    print('В сети нет никого, никого кроме вас...\n')
                    continue
                nickname=input('Введите имя пользователя в сети: ')
                msg=input('Введите сообщение: ')
                result=tcp.WriteMessage(nickname,msg)
                if result==-1:
                    print('На данный момент пользователя с таким ником нет в сети.')
                    continue
                if result==-2:
                    print('Не удалось установить соединение с пользователем.')
                    continue
                if result==1:
                    print('Сообщение успешно отправлено!')
                continue
            if action==3:
                print('Пользователи в сети:')
                if PrintUserList()==0:
                    print('В сети нет никого, никого кроме вас...\n')
                    continue
                nickname=input('Введите имя пользователя в сети: ')
                filepath=input('Введите путь до отправляемого файла\nЕсли он хранится в папке программы, то нажмите Enter: ')
                filename=input('Введите имя файла\nОно должно быть с расширением: ')
                #Check nickname
                recId=''
                for el in BalanceControl.BalanceControl.clients:
                    client=BalanceControl.BalanceControl.clients.get(el)
                    if client.nickname==BaseUser.CompleteNickname(nickname):
                        recId=el
                        break
                if recId=='':
                    print('Пользователь с таким никнеймом сейчас не в сети.')
                    continue
                result=-1
                if filepath=='':result=SendingFile.SendFile(filename,recId)
                else:result=SendingFile.SendFile(filename,recId,filepath)
                if result==1:print('Файл был успешно отправлен.')
                if result==0:print('Неверно указан путь.')
                if result==-1:print('Произошла ошибка при отправки файла.')
                continue
            if action==4:
                SendingFile.Accepting()
                continue
            if action==5:
                print('Пользователи в сети:')
                if PrintUserList()==0:
                    print('В сети нет никого, никого кроме вас...\n')
                    continue
                messages=FileManager.ReadFromFile(input('Введите никнейм пользователя в сети: '))
                ClearConsole()
                if messages==0:print('В сети нет пользователя с таким никнеймом.\n')
                if messages==-1:print('Сообщений пока нет.\n')
                for el in messages:print(el.decode('utf-8'))
                continue
            if action==6:
                #Check Old directory
                if not os.path.isdir('Old'):
                    print('Старых сообщений пока нет.\n')
                    continue
                #How will be searching
                print('1.Поиск по никнейму.\n'
                      +'2.Поиск по списку из переписок.\n')
                try:action=int(input('Введите число: '))
                except ValueError:
                    print('Необходимо ввести число.')
                    continue
                #Input nickname and search in old files
                if action==1:
                    nickname=input('Введите имя пользователя, старые сообщения с которым вы хотите просмотреть: ')
                    choosenDirectories=FileManager.ChooseOldDirectories(nickname)
                    ClearConsole()
                    if len(choosenDirectories)==0:
                        print('Старых сообщений пока нет.\n')
                        continue
                    for i in range(len(choosenDirectories)):
                        print(str(i+1)+'. '+choosenDirectories[i])
                    try:num=int(input('\nВведите цифру, для конкректного выбора истории сообщений: '))
                    except ValueError:
                        print('Необходимо ввести число.')
                        continue
                    ClearConsole()
                    if num>len(choosenDirectories)or num<0:
                        print('Введено некорректное число.')
                        continue
                    messages=FileManager.ReadFromOld(choosenDirectories[num-1])
                #Take directories list and choose 1 file
                if action==2:
                    oldDirecories=os.listdir('Old')
                    ClearConsole()
                    for i in range(len(oldDirecories)):
                        print(str(i+1)+'. '+oldDirecories[i])
                    try:
                        num=int(input('\nВведите цифру, для конкректного выбора истории сообщений: '))
                    except ValueError:
                        print('Необходимо ввести число.')
                        continue
                    ClearConsole()
                    if num>len(oldDirecories)or num<0:
                        print('Введено некорректное число.')
                        continue
                    messages=FileManager.ReadFromOld(oldDirecories[num-1])
                #Print messages
                for el in messages:print(el.decode('utf-8'))
                continue
            if action==7:
                print('Отключаюсь...')
                BaseUser.EndProgram=True
                BaseUser.Exit()
            print('Введите число (1-7).')

ClearConsole()
UserInterface()