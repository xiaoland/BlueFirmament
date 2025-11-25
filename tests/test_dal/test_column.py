"""Tests for dal/column.py and dal/model.py"""

from blue_firmament.dal import Column, column, DALModel
from blue_firmament.dal.query_components.filters import EqFilter, ContainsFilter, NotEqFilter, InFilter, IsFilter
from blue_firmament.dal.query_components.modifiers import OrderModifier
from blue_firmament.dal.query_components.operators import NotOperator


def test_column_basic():
    """Test basic Column creation"""
    col = Column[int](name='test_col')
    assert col.name == 'test_col'
    assert col.column_name == 'test_col'


def test_column_sql_properties():
    """Test Column SQL-specific properties"""
    col = column(
        primary_key=True,
        auto_increment=True,
        column_type='INTEGER',
    )
    col._set_name('_id')
    
    assert col.primary_key is True
    assert col.auto_increment is True
    assert col.column_type == 'INTEGER'
    assert col.is_key() is True


def test_column_nullable():
    """Test Column nullable property"""
    col_nullable = column(nullable=True)
    col_not_null = column(nullable=False)
    
    assert col_nullable.nullable is True
    assert col_not_null.nullable is False


def test_column_unique():
    """Test Column unique constraint"""
    col = column(unique=True)
    assert col.unique is True


def test_column_foreign_key():
    """Test Column foreign key"""
    col = column(foreign_key='departments._id')
    assert col.foreign_key == 'departments._id'
    assert col.is_key() is False  # foreign key is not a key in this model


def test_column_dal_query_methods():
    """Test Column DAL query methods (equals, contains, etc.)"""
    col = Column[str](name='status', in_model_name='status')
    
    # Test equals
    eq = col.equals('active')
    assert isinstance(eq, EqFilter)
    
    # Test contains
    contains = col.contains('a', 'b')
    assert isinstance(contains, ContainsFilter)
    
    # Test not_equals
    neq = col.not_equals('inactive')
    assert isinstance(neq, NotEqFilter)
    
    # Test in_
    in_filter = col.in_(['active', 'pending'])
    assert isinstance(in_filter, InFilter)
    
    # Test not_in_
    not_in = col.not_in_(['deleted', 'archived'])
    assert isinstance(not_in, tuple)
    assert isinstance(not_in[0], NotOperator)
    assert isinstance(not_in[1], InFilter)
    
    # Test is_
    is_filter = col.is_(True)
    assert isinstance(is_filter, IsFilter)
    
    # Test is_not
    is_not = col.is_not(None)
    assert isinstance(is_not, tuple)
    assert isinstance(is_not[0], NotOperator)
    assert isinstance(is_not[1], IsFilter)
    
    # Test order_by
    order = col.order_by()
    assert isinstance(order, OrderModifier)
    
    order_desc = col.order_by(desc=True)
    assert isinstance(order_desc, OrderModifier)


def test_dal_model_path():
    """Test DALModel dal_path configuration"""
    class User(DALModel, dal_path=('users',)):
        pass
    
    assert User.dal_path() == ('users',)
    assert User.has_dal_path() is True


def test_dal_model_table_name():
    """Test DALModel table_name from dal_path"""
    class User(DALModel, dal_path=('schema', 'users')):
        pass
    
    assert User.table_name() == 'users'
    assert User.schema_name() == 'schema'


def test_dal_model_with_columns():
    """Test DALModel with Column fields"""
    class User(DALModel, dal_path=('users',)):
        _id: Column[int] = column(primary_key=True, auto_increment=True)
        name: Column[str] = column(column_type='VARCHAR(255)', nullable=False)
        email: Column[str] = column(unique=True)
    
    # Test DAL path
    assert User.dal_path() == ('users',)
    
    # Test fields
    assert User._id.primary_key is True
    assert User._id.auto_increment is True
    assert User.name.nullable is False
    assert User.email.unique is True


def test_dal_model_explicit_table_name():
    """Test DALModel with explicit table_name"""
    class User(DALModel, table_name='user_accounts'):
        pass
    
    assert User.table_name() == 'user_accounts'
    assert User.dal_path() == ('user_accounts',)
