'''Manager of BlueFirmament'''

import typing

from session.common import CommonSession
from scheme import BaseScheme


SchemeType = typing.TypeVar('SchemeType', bound=BaseScheme)
class Manager(typing.Generic[SchemeType]):

    __SCHEME_CLS__: typing.Type[SchemeType]

    def __init__(self, session: CommonSession) -> None:
        
        self._session = session
        self._scheme: typing.Optional[SchemeType] = None

    async def get_scheme(self,
        from_primary_key: typing.Any = None,
    ) -> SchemeType:
        
        '''获取本管理器管理的数据模型的实例

        :param from_primary_key: 主键值，不为None则在无实例时从主键获取
        '''
        
        if not self._scheme:
            if from_primary_key:
                self._scheme = await self._session.dao.select_a_scheme_from_primary_key(
                    self.__SCHEME_CLS__, from_primary_key
                )
            else:
                raise ValueError('scheme is not initialized and no getter method provided')

        return self._scheme
    
    def set_scheme(self,
        scheme: SchemeType,
    ) -> None:
        
        '''设置本管理器管理的数据模型的实例

        :param scheme: 数据模型实例
        '''
        self._scheme = scheme
