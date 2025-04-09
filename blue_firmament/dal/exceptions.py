'''Exceptions of BlueFirmament DAL Module'''

class DALException(Exception):
    '''Base Exception for DAL'''
    pass


class DuplicateRecord(DALException):
    '''重复记录
    
    场景
    ^^^^^^
    - 要求指获得一个符合条件的数据记录，但找到多个
    '''
    
    pass


class NotFound(DALException):

    '''未找到记录
    '''
