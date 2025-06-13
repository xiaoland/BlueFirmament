"""Utils related to using exec.
"""

__all__ = [
    "build_func_sig"
]

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit


def build_func_sig(
    name: str,
    *params: tuple[str, Opt[str]],
    async_: bool = False,
) -> str:
    """
    :param params: func args, kwargs's name and annotation
    """
    params_str: str = ",".join(
        f"{i[0]}{':' + i[1] if i[1] is not None else ''}"
        for i in params
    )
    func_sig = f"{'async ' if async_ else ''}def {name}({params_str}):\n"

    return func_sig
