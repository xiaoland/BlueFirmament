"""Test exec module of utils package.
"""

from blue_firmament.utils import exec_


async def test_build_func_sig():

    namespaces = {}
    body = "    return 0"

    sig1 = exec_.build_func_sig(
        "f1", 
        ('self', None),
        ('arg2', 'int'),
    )
    sig2 = exec_.build_func_sig(
        "f2", 
        async_=True,
    )
    
    exec(sig1+body, globals().copy(), namespaces)
    exec(sig2+body, globals().copy(), namespaces)
    
    assert namespaces['f1'](None, 1) == 0
    assert await namespaces['f2']() == 0
