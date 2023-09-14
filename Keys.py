from nacl.public import PrivateKey, Box, PublicKey
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
import zlib
from Crypto.Cipher import AES
from Crypto.Util import Padding
from Crypto.Util.Padding import unpad

#Keys
secretKey=PrivateKey.generate()
publicKey=secretKey.public_key
signingKey=SigningKey.generate()
verifyKey=signingKey.verify_key

def Signing(message):
    """
    Signature
    """
    return signingKey.sign(message)+verifyKey.encode()

def Verify(signedMessage):
    """
    Signature
    """
    try:
        vKey=VerifyKey(signedMessage[-32:])
        msg=vKey.verify(signedMessage[:-32])
    except Exception:   
        msg=''
    finally:
        return msg

def SharedKey(pk):
    return Box(secretKey,PublicKey(pk)).shared_key()

def Crc32(data):
    if type(data)==str:
        return zlib.crc32(data.encode('utf-8')).to_bytes(4,'big')
    else:
        return zlib.crc32(data).to_bytes(4,'big')
    

def AesCBC(data:bytes,key:bytes):
    '''
    return (initialization vector,encode data)
    '''
    cipher=AES.new(key,AES.MODE_CBC)
    cData=cipher.encrypt(Padding.pad(data,AES.block_size))
    return(cipher.iv,cData)

def DecodeAesCBC(encodeData,key):
    '''
    return '' if failed
    '''
    iv=encodeData[-16:]
    cipher=AES.new(key,AES.MODE_CBC,iv)
    decodeMsg=unpad(cipher.decrypt(encodeData[:-16]),AES.block_size)
    #Check hash
    msgHash=decodeMsg[-4:]
    newHash=Crc32(decodeMsg[:-4])#.decode('utf-8')
    if msgHash==newHash:
        return decodeMsg[:-4]
    else:
        return ''