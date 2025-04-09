"""sub package Schema tests for Blue Firmament."""

import unittest
import blue_firmament.scheme
import blue_firmament.scheme.business


class TestSchema(unittest.TestCase):
    """Basic test cases."""

    def test_schema_basic(self):
        """Test schema basic
        
        If pass
        ^^^
        - 正常解析内置字段
        - 可以设置字段默认值
        """

        class MyScheme(blue_firmament.scheme.BaseScheme):
            _table_name = 'my_table'
            
            _id: int = blue_firmament.scheme.Field(is_primary_key=True)
            name: str = 'default_name'

        schema_instance = MyScheme(
            _id=1
        )

        self.assertEqual(MyScheme.__table_name__, 'my_table')
        self.assertEqual(schema_instance._id, 1)
        self.assertEqual(schema_instance.name, 'default_name')

    def test_business_scheme(self):
        """Test business scheme.
        
        If pass
        ^^^
        - 模型可继承
        """

        class MyBusinessScheme(blue_firmament.scheme.business.BusinessScheme[int]):
            _table_name = 'my_business_table'
            
            name: str = 'default_name'
        
        business_schema_instance = MyBusinessScheme(
            _id=1
        )

        self.assertEqual(business_schema_instance._id, 1)
        self.assertEqual(MyBusinessScheme.__table_name__, 'my_business_table')
        self.assertEqual(business_schema_instance.name, 'default_name')


if __name__ == "__main__":
    unittest.main()
