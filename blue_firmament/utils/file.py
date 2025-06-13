
import json
import pkgutil


def load_json_file(
    file_path: str, encoding: str = "utf-8", package: str | None = None
) -> dict:

    """从文件系统加载JSON文件

    :param file_path: 文件路径
    :param encoding: 编码
    :param package: 包名；如果不为None，则使用pkgutil.get_data读取

    :return 转换为字典的JSON数据（异常返回空字典）
    """
    from ..log.main import get_logger
    logger = get_logger(__name__)
    
    try:
        if package:
            pkg_read_result = pkgutil.get_data(package, file_path)
            if pkg_read_result is None:
                logger.error('Load json file %s failed, file not found' % file_path)
                return {}
            data = json.loads(pkg_read_result.decode(encoding))
        else:
            data = json.load(open(file_path, "r", encoding=encoding))
        
        return data
    except IOError:
        logger.error('Load json file %s failed, IO error' % file_path)
        return {}
    except json.decoder.JSONDecodeError:
        logger.error('Load json file %s failed, unable to decode' % file_path)
        return {}

def save_json_file(file_path: str, data: dict, encoding: str = "utf-8"):

    json.dump(data, open(file_path, "w", encoding=encoding))
