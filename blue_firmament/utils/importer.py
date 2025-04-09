# author: Lan_zhijiang
# desc: quick imports

import importlib
import pkgutil

# By Google Gemini
def import_modules(package_name, var_name):
    """
    导入指定包下的所有模块并提取`<var_name>`变量

    如果找不到某模块中的变量，会被忽略

    @params
        package_name: 包名，例如 "my_project.routers"

    @return
        所有*_router*变量的列表
    """
    modules = []
    for module in pkgutil.iter_modules([package_name]):
        # 过滤非包模块
        if not module.ispkg:
            module_name = f"{package_name.replace('/', '.')}.{module.name}"
            module = importlib.import_module(module_name)
            # 提取*endswith*变量
            for attr in dir(module):
                try:
                    target_var = getattr(module, attr)
                except AttributeError:
                    continue
                else:
                    modules.append(target_var)
    return modules

