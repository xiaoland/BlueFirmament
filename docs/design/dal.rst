DAL Design
======================

DataAccessObject provide ``select``, ``insert``, ``update``, ``delete`` methods to operate data.

``select``, ``insert`` and ``delete`` operate existing data, requires filters.

What ever the data source actually is, DAO provide a unified interface to operate data. \n
We design path, filters, modifiers and DAO to implement this target.

- Path: a tuple of string, tells where to execute the query.
- Filter: condition to filter the data to be executed the disire operation.
- Modifier: transform the result of query.
- Field: 
- Schema: 


With Task Context
-----------------
When return is scheme with task context, inject task context.
