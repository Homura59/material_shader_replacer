"""
错误处理模块
提供统一的错误处理机制
"""


class MSRError(Exception):
    """MSR基础错误类"""
    pass


class ShaderNotFoundError(MSRError):
    """着色器未找到错误"""
    pass


class ConnectionError(MSRError):
    """连接错误"""
    pass


class ValidationError(MSRError):
    """验证错误"""
    pass


def safe_link(links, source_socket, target_socket):
    """安全地创建节点连接"""
    try:
        links.new(source_socket, target_socket)
        return True
    except Exception:
        return False


def safe_remove_node(nodes, node):
    """安全地删除节点"""
    try:
        nodes.remove(node)
        return True
    except (ReferenceError, RuntimeError):
        return False
