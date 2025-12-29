"""
缓存模块
提供材质处理缓存和节点组缓存功能
"""

import bpy


class MaterialCache:
    """材质处理缓存 - 避免重复处理相同材质"""
    _processed_materials = {}

    @classmethod
    def clear(cls):
        cls._processed_materials.clear()

    @classmethod
    def is_processed(cls, material):
        return material.name in cls._processed_materials

    @classmethod
    def mark_processed(cls, material, result):
        cls._processed_materials[material.name] = result

    @classmethod
    def get_result(cls, material):
        return cls._processed_materials.get(material.name, 0)


class NodeGroupCache:
    """节点组缓存 - 避免重复排序和查询"""
    _sorted_groups = None
    _last_count = 0

    @classmethod
    def get_sorted_shader_node_groups(cls):
        current_count = len(bpy.data.node_groups)
        if cls._sorted_groups is None or cls._last_count != current_count:
            cls._sorted_groups = sorted(
                [ng for ng in bpy.data.node_groups if ng.type == 'SHADER'],
                key=lambda x: x.name
            )
            cls._last_count = current_count
        return cls._sorted_groups

    @classmethod
    def invalidate(cls):
        cls._sorted_groups = None
        cls._last_count = 0
