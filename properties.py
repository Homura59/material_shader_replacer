"""属性定义模块
定义插件所需的所有属性
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty
)
from .node_config import (
    get_available_shaders,
    get_available_shaders_for_specific,
    get_all_node_types  # 新增：获取所有节点类型
)


class ConnectionRuleItem(PropertyGroup):
    """连接规则项"""

    # 源节点匹配方式
    source_match_mode: EnumProperty(
        name="源节点匹配方式",
        description="选择如何匹配源节点",
        items=[
            ('LABEL', "按标签/名称", "通过节点的标签或名称进行匹配"),
            ('TYPE', "按节点类型", "通过节点类型进行匹配"),],
        default='LABEL'
    )

    source_node_label: StringProperty(
        name="源节点标签/名称",
        description="源节点的标签或名称（用于匹配节点）",
        default=""
    )

    source_node_type: EnumProperty(
        name="源节点类型",
        description="源节点的类型",
        items=get_all_node_types  # 修改：使用所有节点类型
    )

    source_socket_index: IntProperty(
        name="源接口索引",
        description="源节点的输出接口索引（从0开始）",
        default=0,
        min=0
    )

    # 目标节点匹配方式
    target_match_mode: EnumProperty(
        name="目标节点匹配方式",
        description="选择如何匹配目标节点",
        items=[
            ('LABEL', "按标签/名称", "通过节点的标签或名称进行匹配"),
            ('TYPE', "按节点类型", "通过节点类型进行匹配"),
        ],
        default='LABEL'
    )

    target_node_label: StringProperty(
        name="目标节点标签/名称",
        description="目标节点的标签或名称（用于匹配节点）",
        default=""
    )

    target_node_type: EnumProperty(
        name="目标节点类型",
        description="目标节点的类型",
        items=get_all_node_types  # 修改：使用所有节点类型
    )

    target_socket_index: IntProperty(
        name="目标接口索引",
        description="目标节点的输入接口索引（从0开始）",
        default=0,
        min=0
    )


class ConnectionSnapshotItem(PropertyGroup):
    """单个连接快照项 - 记录一个具体的连接"""

    material_name: StringProperty(
        name="材质名称",
        description="连接所属的材质名称",
        default=""
    )

    from_node_name: StringProperty(
        name="源节点名称",
        description="源节点的名称",
        default=""
    )

    from_node_type: StringProperty(
        name="源节点类型",
        description="源节点的类型（如 BSDF_PRINCIPLED）",
        default=""
    )

    from_socket_name: StringProperty(
        name="源接口名称",
        description="源节点的输出接口名称（如 'Surface'）",
        default=""
    )

    from_socket_index: IntProperty(
        name="源接口索引",
        description="源节点的输出接口索引",
        default=0,
        min=0
    )

    from_socket_type: StringProperty(
        name="源接口类型",
        description="源接口的类型（如 'SHADER'）",
        default=""
    )

    to_node_name: StringProperty(
        name="目标节点名称",
        description="目标节点的名称",
        default=""
    )

    to_node_type: StringProperty(
        name="目标节点类型",
        description="目标节点的类型",
        default=""
    )

    to_socket_name: StringProperty(
        name="目标接口名称",
        description="目标节点的输入接口名称",
        default=""
    )

    to_socket_index: IntProperty(
        name="目标接口索引",
        description="目标节点的输入接口索引",
        default=0,
        min=0
    )

    to_socket_type: StringProperty(
        name="目标接口类型",
        description="目标接口的类型",
        default=""
    )

    replace_mode: StringProperty(
        name="替换模式",
        description="记录断开连接时的替换模式",
        default=""
    )

    shader_type: StringProperty(
        name="着色器类型",
        description="记录断开连接的着色器类型",
        default=""
    )


class ShaderReplacerProperties(PropertyGroup):
    """插件属性定义"""

    # 内置着色器选择器（不支持中文的EnumProperty）
    builtin_shader: EnumProperty(
        name="内置着色器",
        description="选择Blender内置的着色器节点",
        items=[
            ('NONE', '-- 未选择 --', '不使用内置着色器'),
            ('BSDF_PRINCIPLED', '原理化BSDF', '基础PBR着色器'),
            ('BSDF_DIFFUSE', '漫射BSDF', '漫反射着色器'),
            ('BSDF_GLOSSY', '光泽BSDF', '光泽着色器'),
            ('BSDF_TRANSPARENT', '透明BSDF', '透明着色器'),
            ('BSDF_GLASS', '玻璃BSDF', '玻璃着色器'),
            ('BSDF_TRANSLUCENT', '半透明BSDF', '半透明着色器'),
            ('BSDF_REFRACTION', '折射BSDF', '折射着色器'),
            ('BSDF_TOON', '卡通BSDF', '卡通着色器'),
            ('BSDF_SHEEN', '光泽BSDF', '光泽着色器'),
            ('EMISSION', '自发光', '自发光着色器'),
            ('SUBSURFACE_SCATTERING', '次表面散射', '次表面散射'),
            ('VOLUME_ABSORPTION', '体积吸收', '体积吸收'),
            ('VOLUME_SCATTER', '体积散射', '体积散射'),
            ('VOLUME_PRINCIPLED', '原理化体积', '原理化体积着色器'),
            ('MIX_SHADER', '混合着色器', '混合两个着色器'),
            ('ADD_SHADER', '相加着色器', '相加两个着色器'),
        ],
        default='NONE',
        update=lambda self, context: self._on_builtin_shader_changed()
    )

    # 替换特定着色器时的内置着色器选择
    specific_builtin_shader: EnumProperty(
        name="特定内置着色器",
        description="选择要替换的内置着色器",
        items=[
            ('NONE', '-- 未选择 --', '不使用内置着色器'),
            ('BSDF_PRINCIPLED', '原理化BSDF', '基础PBR着色器'),
            ('BSDF_DIFFUSE', '漫射BSDF', '漫反射着色器'),
            ('BSDF_GLOSSY', '光泽BSDF', '光泽着色器'),
            ('BSDF_TRANSPARENT', '透明BSDF', '透明着色器'),
            ('BSDF_GLASS', '玻璃BSDF', '玻璃着色器'),
            ('BSDF_TRANSLUCENT', '半透明BSDF', '半透明着色器'),
            ('BSDF_REFRACTION', '折射BSDF', '折射着色器'),
            ('BSDF_TOON', '卡通BSDF', '卡通着色器'),
            ('BSDF_SHEEN', '光泽BSDF', '光泽着色器'),
            ('EMISSION', '自发光', '自发光着色器'),
            ('SUBSURFACE_SCATTERING', '次表面散射', '次表面散射'),
            ('VOLUME_ABSORPTION', '体积吸收', '体积吸收'),
            ('VOLUME_SCATTER', '体积散射', '体积散射'),
            ('VOLUME_PRINCIPLED', '原理化体积', '原理化体积着色器'),
            ('MIX_SHADER', '混合着色器', '混合两个着色器'),
            ('ADD_SHADER', '相加着色器', '相加两个着色器'),
        ],
        default='NONE',
        update=lambda self, context: self._on_specific_builtin_shader_changed()
    )

    shader_type_manual: BoolProperty(
        name="手动输入",
        description="使用手动文本输入",
        default=False
    )
    specific_shader_manual: BoolProperty(
        name="手动输入",
        description="使用手动文本输入",
        default=False
    )
    target_node_type_manual: BoolProperty(
        name="手动输入",
        description="使用手动文本输入",
        default=False
    )
    shader_type_text: StringProperty(
        name="着色器名称",
        description="输入着色器或节点组名称",
        default=""
    )

    # 用于 prop_search 的节点组选择器
    shader_nodegroup: PointerProperty(
        name="节点组",
        description="选择一个着色器节点组",
        type=bpy.types.NodeTree,
        poll=lambda self, node_tree: node_tree.type == 'SHADER',
        update=lambda self, context: self._on_shader_nodegroup_changed()
    )
    specific_shader_text: StringProperty(
        name="特定着色器",
        description="输入要替换的着色器名称",
        default=""
    )

    # 用于 prop_search 的特定节点组选择器
    specific_nodegroup: PointerProperty(
        name="特定节点组",
        description="选择要替换的特定节点组",
        type=bpy.types.NodeTree,
        poll=lambda self, node_tree: node_tree.type == 'SHADER',
        update=lambda self, context: self._on_specific_nodegroup_changed()
    )
    target_node_type_text: StringProperty(
        name="节点类型",
        description="输入节点类型名称",
        default=""
    )

    # 选择要替换为的着色器
    shader_type: EnumProperty(
        name="选择着色器",
        description="从列表中选择要替换为的着色器",
        items=get_available_shaders
    )

    # 替换模式
    replace_mode: EnumProperty(
        name="替换模式",
        description="选择替换模式",
        items=[
            ('ALL', "替换所有着色器", "替换材质中的所有着色器节点"),
            ('SPECIFIC', "替换特定着色器", "仅替换指定的着色器节点"),
            ('MATERIAL', "替换特定材质着色器", "仅替换指定材质中的着色器"),
            ('MATERIAL_SPECIFIC', "替换特定材质中的特定着色器", "在指定材质中仅替换特定的着色器")
        ],
        default='ALL'
    )

    # 特定材质选择器（用于prop_search）
    target_material: PointerProperty(
        name="目标材质",
        description="选择要替换的特定材质",
        type=bpy.types.Material
    )

    # 材质模式下的特定着色器选择 - 内置着色器
    material_specific_builtin_shader: EnumProperty(
        name="材质特定内置着色器",
        description="选择要替换的特定内置着色器（材质模式）",
        items=get_available_shaders_for_specific,
        update=lambda self, context: self._on_material_specific_builtin_shader_changed()
    )

    # 材质模式下的特定着色器选择 - 节点组
    material_specific_nodegroup: PointerProperty(
        name="材质特定节点组",
        description="选择要替换的特定节点组（材质模式）",
        type=bpy.types.NodeTree,
        poll=lambda self, node_tree: node_tree.type == 'SHADER',
        update=lambda self, context: self._on_material_specific_nodegroup_changed()
    )

    # 特定着色器选择（下拉菜单）
    specific_shader_type: EnumProperty(
        name="特定着色器",
        description="选择要替换的特定着色器",
        items=get_available_shaders_for_specific
    )

    # 自动连接选项
    auto_connect: BoolProperty(
        name="自动连接",
        description="自动连接新着色器到其他节点",
        default=True
    )

    # 高级选项
    advanced_options: BoolProperty(
        name="高级选项",
        description="显示高级选项",
        default=False
    )

    # 连接规则列表
    connection_rules: CollectionProperty(
        type=ConnectionRuleItem
    )

    # 当前选中的连接规则索引
    active_rule_index: IntProperty(
        default=0
    )

    # 目标选择
    target_type: EnumProperty(
        name="目标类型",
        description="选择替换目标类型",
        items=[
            ('OBJECTS', "选中对象", "替换选中对象的材质"),
            ('COLLECTION', "活动集合", "替换活动集合中所有对象的材质")
        ],
        default='OBJECTS'
    )

    # 互斥选择逻辑：当选择内置着色器时，清空节点组选择
    def _on_builtin_shader_changed(self):
        """当内置着色器改变时，清空节点组选择"""
        if self.builtin_shader != 'NONE':
            self.shader_nodegroup = None

    def _on_shader_nodegroup_changed(self):
        """当节点组改变时，清空内置着色器选择"""
        if self.shader_nodegroup is not None:
            self.builtin_shader = 'NONE'

    def _on_specific_builtin_shader_changed(self):
        """当特定内置着色器改变时，清空特定节点组选择"""
        if self.specific_builtin_shader != 'NONE':
            self.specific_nodegroup = None

    def _on_specific_nodegroup_changed(self):
        """当特定节点组改变时，清空特定内置着色器选择"""
        if self.specific_nodegroup is not None:
            self.specific_builtin_shader = 'NONE'

    def _on_material_specific_builtin_shader_changed(self):
        """当材质模式下的特定内置着色器改变时，清空材质模式下的特定节点组选择"""
        if self.material_specific_builtin_shader != 'NONE':
            self.material_specific_nodegroup = None

    def _on_material_specific_nodegroup_changed(self):
        """当材质模式下的特定节点组改变时，清空材质模式下的特定内置着色器选择"""
        if self.material_specific_nodegroup is not None:
            self.material_specific_builtin_shader = 'NONE'

    # 连接快照集合 - 用于记录断开前的连接关系
    connection_snapshot: CollectionProperty(
        type=ConnectionSnapshotItem
    )

    # 当前连接快照的材质名称（用于分组显示）
    snapshot_material_name: StringProperty(
        name="快照材质名称",
        description="记录当前快照所属的材质名称",
        default=""
    )

    # 连接关系记录功能启用状态
    enable_connection_recording: BoolProperty(
        name="启用连接关系记录",
        description="启用或禁用连接关系记录功能",
        default=True
    )


def register():
    bpy.utils.register_class(ConnectionRuleItem)
    bpy.utils.register_class(ConnectionSnapshotItem)
    bpy.utils.register_class(ShaderReplacerProperties)


def unregister():
    bpy.utils.unregister_class(ShaderReplacerProperties)
    bpy.utils.unregister_class(ConnectionSnapshotItem)
    bpy.utils.unregister_class(ConnectionRuleItem)
