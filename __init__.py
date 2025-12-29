"""
Blender材质着色器批量替换插件 - 模块化版本

该插件允许用户在选定的对象或集合上批量替换材质中的着色器，
并保持原有节点间的链接关系。

功能特点：
- 批量替换选中对象或集合的材质着色器
- 智能保持节点链接关系
- 提供高级选项配置
- 支持中文界面
- 提供着色器选择下拉菜单
- 智能连接处理：根据接口语义自动连接
- 高级连接规则功能：可断开重新连接，可设置自定义连接规则
- 支持按节点标签/名称或节点类型两种匹配方式
"""

# 插件元数据
from . import operators, properties, ui, node_config, translations
from bpy.utils import register_class, unregister_class
import bpy
bl_info = {
    "name": "材质着色器批量替换工具",
    "author": "Homura59",
    "version": (1, 3, 5),
    "blender": (4, 3, 0),
    "location": "3D视图 > 侧边栏 > 材质替换工具",
    "description": "批量替换材质中的着色器，支持智能连接处理和高级连接规则",
    "doc_url": "https://space.bilibili.com/37603900",
    "warning": "",
    "category": "Material",
}


def register():
    """注册插件"""
    # 首先注册 properties 模块中的类
    properties.register()

    # 然后注册其他类
    operator_classes = (
        operators.MATERIAL_OT_add_connection_rule,
        operators.MATERIAL_OT_remove_connection_rule,
        operators.MATERIAL_OT_disconnect_all_connections,
        operators.MATERIAL_OT_reconnect_with_rules,
        operators.MATERIAL_OT_batch_replace_shader,
    )

    for cls in operator_classes:
        try:
            register_class(cls)
        except ValueError as e:
            print(f"注册失败 {cls.__name__}: {e}")

    ui_classes = (
        ui.MATERIAL_UL_connection_rule_list,
        ui.MATERIAL_PT_shader_replacer_panel,
        ui.MATERIAL_PT_shader_replacer_material
    )

    for cls in ui_classes:
        try:
            register_class(cls)
        except ValueError as e:
            print(f"注册失败 {cls.__name__}: {e}")

    # 将属性设置到场景
    from bpy.types import Scene
    from .properties import ShaderReplacerProperties
    Scene.shader_replacer_props = bpy.props.PointerProperty(
        type=ShaderReplacerProperties)

    # 注册节点配置
    node_config.register()

    # 注册翻译
    bpy.app.translations.register(__name__, translations.translations_dict)

    print("材质着色器批量替换插件 v1.3.5 注册完成")


def unregister():
    """注销插件"""
    # 注销翻译
    try:
        bpy.app.translations.unregister(__name__)
    except:
        pass

    from bpy.types import Scene
    if hasattr(Scene, "shader_replacer_props"):
        delattr(Scene, "shader_replacer_props")

    # 注销节点配置
    node_config.unregister()

    # UI类
    ui_classes = (
        ui.MATERIAL_PT_shader_replacer_material,
        ui.MATERIAL_PT_shader_replacer_panel,
        ui.MATERIAL_UL_connection_rule_list,
    )

    for cls in ui_classes:
        try:
            unregister_class(cls)
        except RuntimeError as e:
            print(f"注销失败 {cls.__name__}: {e}")

    # 操作符类
    operator_classes = (
        operators.MATERIAL_OT_batch_replace_shader,
        operators.MATERIAL_OT_reconnect_with_rules,
        operators.MATERIAL_OT_disconnect_all_connections,
        operators.MATERIAL_OT_remove_connection_rule,
        operators.MATERIAL_OT_add_connection_rule,
    )

    for cls in operator_classes:
        try:
            unregister_class(cls)
        except RuntimeError as e:
            print(f"注销失败 {cls.__name__}: {e}")

    # 最后注销 properties 模块中的类
    properties.unregister()

    print("材质着色器批量替换插件已注销")


if __name__ == "__main__":
    register()
