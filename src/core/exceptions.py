"""
自定义异常类
"""


class NewsAgentException(Exception):
    """基础异常类"""
    pass


class DatabaseException(NewsAgentException):
    """数据库相关异常"""
    pass


class CrawlerException(NewsAgentException):
    """爬虫相关异常"""
    pass


class AnalyzerException(NewsAgentException):
    """分析器相关异常"""
    pass


class ConfigException(NewsAgentException):
    """配置相关异常"""
    pass


class NotFoundException(NewsAgentException):
    """资源未找到异常"""
    pass


class ValidationException(NewsAgentException):
    """数据验证异常"""
    pass


class ServiceException(NewsAgentException):
    """服务层异常"""
    pass
