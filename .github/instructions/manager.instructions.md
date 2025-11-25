---
applyTo: "**/managers/**/*.py"
---

Read this instruction if you are going to write a manager.

## CommonManager

CommonManager are powerful built-in manager provided by blue_firmament, import it using `from blue_firmament.manager import CommonManager`.

It provides following abilities, use them if needed.

- Common methods for managing the data model.
- Preset handlers serves get, put, patch, delete operation of the managed data model over API.
- Serve methods as handler of API Endpoint.

### Config

Config CommonManager when initializing your manager class:

```python
from blue_firmament.manager import CommonManager
class YourManager(CommonManager[SchemeType, SchemePrimaryKeyType], ...set_your_config_items_here): ...
```

Config item are listed as follows:

- `scheme_cls`: the managing data model class
- `path_prefix`: Path prefixed to all this manager's TaskHandlers path. Sould not start with a slash.
- `preset_handler_config`: see [PresetHandlers](#preset-handlers)

Also you should pass these type args to CommonManager:

1. The data model type you are managing
2. The type of the managing data model's primary key

## Serve Methods as Handler of API Endpoint.

Use decorator `listen_to` from `blue_firmament.task` to wrap your method as a TaskHandler and it will be registered to manager level TaskRegistry.

### Managing the Data Model

- `property:_scheme_cls`: the managing data model.
- `property:_scheme`: the managing data model instance. If None, raise ValueError,
- `_get_scheme`: get the managing data model instance. If None, try to get data model from DAO if possible.
- `_get`: get a data model
- `_insert_item`: Insert an item to insertable field of the managing data model.
- `_delete_item`: Delete an item from insertable field of the managing data model.

### Preset Handlers

```python
from blue_firmament.manager import CommonManager, PresetHandlerConfig
class YourManager(CommonManager, preset_handler_config=PresetHandlerConfig(...)): ...
```

> You must config PresetHandlerConfig correctly to enable the preset handlers you want.

Enabled preset handlers will be added to manager level task registry.
