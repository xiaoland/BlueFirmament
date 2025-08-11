import abc
from typing import Optional as Opt

from blue_firmament.dal import DALPath


class DALQueryComponent(abc.ABC):

    @abc.abstractmethod
    def dump_to_sql(self) -> str:
        """序列化为SQL语句
        """

    def dump_to_postgrest(self) -> tuple[
        str, tuple | dict | None
    ]:
        """Serialize to a call to postgrest lib's RequestBuilder.

        :returns: (RequestBuilder method, parameters)

        Parameters：
        - tuple as positional arguments
        - dict as keyword arguments
        - None for no parameters
        """

    @abc.abstractmethod
    def dump_to_postgrest_str(self) -> str:
        """Serialize to PostgREST query part in string.

        Syntax: `<field>.<filter_name>.<value>`,
        - use `()` for in filters with multiple values,
        - use `{}` for contains(By) filters with multiple values.

        Filter names:
        - eq: equal
        - neq: not equal
        - is: is (true, false, null)
        - in: in (multiple values)
        - cs: contains (multiple values)
        - cb: contained by (multiple values)
        """

    def __repr__(self):
        return f"{self.__class__.__name__}"

    @property
    def dal_path(self) -> Opt[DALPath]:
        """Get filter's scheme's DAL path.
        """
        return None
