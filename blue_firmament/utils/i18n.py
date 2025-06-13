"""
国际化实用工具
"""

import typing
import enum

from ..log.main import get_logger
logger = get_logger(__name__)

# setting
from ..data.settings.i18n import get_setting

# utils
from ..utils import dump_enum as get_enum_value

# libs
import gettext


LanguageEnum = Type[get_setting().language_enum]
DomainEnum = Type[get_setting().domain_enum]
DEFAULT_LANG = get_setting().default_lang
TRANSLATORS: Dict[LanguageEnum, Dict[DomainEnum, gettext.GNUTranslations]] = {}
'''翻译器实例，按照 lang, domain 存储'''


def get_translator(
    domain: DomainEnum | str, 
    language: LanguageEnum = DEFAULT_LANG, 
    localedir: str = None
) -> gettext.GNUTranslations:
    
    """
    获取翻译器实例

    :param domain: DomainEnum | str
        翻译领域
    :param language: LanguageEnum
        语言
    :param localedir: str
        自定义 locale 目录 \n
        如果没有传递，则使用配置中指定的目录 \n
        如果传递，且发现有重名的翻译器，则合并

    Usgae
    -----
    切换翻译器实例 ：
        通过 get_translator().install() 切换_()对应的翻译器实例或者在模块内自行声明

    Warning
    -------
    如果你希望合并翻译器，则必须先初始化默认翻译器实例，再获得自定义 localedir
    
    Docs
    ----
    https://git.hadream.ltd/anana/backend/gitlab-profile/-/wikis/Standard/Internationalization
    """
    customized_localedir = localedir is not None
    try:
        translator = TRANSLATORS[language][domain]
    except KeyError:
        if language not in TRANSLATORS:
            TRANSLATORS[language] = {}
    
        if domain not in TRANSLATORS[language]:
            if not localedir:
                localedir = get_setting().r_localedir
            
            translator = gettext.translation(
                get_enum_value(domain),
                localedir=localedir,
                languages=(get_enum_value(language), get_enum_value(DEFAULT_LANG))
            )
            TRANSLATORS[language][domain] = translator
    else:
        if customized_localedir:
            new_translator = gettext.translation(
                get_enum_value(domain),
                localedir=localedir,
                languages=(get_enum_value(language), get_enum_value(DEFAULT_LANG))
            )
            translator.add_fallback(new_translator)
    finally:
        return translator


def gettext_placeholder(message: str) -> str: 

    """
    gettext 占位符，用于标记需要翻译的字符串

    一般为`_`

    在翻译器实例安装后，会被替换为翻译后的字符串
    """
    return message


def pgettext_placeholder(context: str, message: str) -> str: 

    """
    pgettext 占位符，用于标记需要翻译的字符串，但带有场景值

    一般为`de_p`
    """
    return message


class TranslatableEnum(Enum):

    """
    可翻译 Enum

    在对 Enum 进行字符串格式化时，将成员值通过 i18n 翻译

    支持 context 模式，需要在指定`_context` \n
    设置成员时，使用 `_(<context>|<value>)`

    文档：https://git.hadream.ltd/anana/backend/common/-/wikis/Util/Enum#translatableenum
    """

    def __init__(self, 
        t: Optional[gettext.GNUTranslations] = None, 
        context: Optional[str] = None, 
        domain: Optional[DomainEnum] = None    
    ) -> None:
        
        """
        传入 t 或者 domain
        """

        self._translator = t
        self._context = context
        self._domain = domain

    @property
    def translator(self) -> gettext.GNUTranslations:
        if not self._translator:
            return get_translator(self._domain, DEFAULT_LANG)
        return self._translator

    def translate(self, lang: Optional[LanguageEnum] = None, domain: Optional[DomainEnum] = None) -> str:

        """
        如果配置了翻译器，则使用翻译器翻译成员值；否则直接返回成员值
        """
        if lang and domain:
            t = get_translator(domain, lang)
        else:
            t = self.translator

        if isinstance(t, gettext.GNUTranslations):
            if self._context:
                return t.pgettext(self._context, self._value_)
            return t.gettext(self._value_)
        else:
            return self._value_

    def __format__(self, *args) -> str:
        return self.translate()
    
    def __str__(self):
        return self.translate()
