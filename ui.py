"""
UI模块
定义插件的所有用户界面元素
"""

import bpy
from bpy.types import Panel, UIList
from .node_config import NODE_TYPE_NAMES, NodeTypeConfig


def get_disconnect_button_label(replace_mode):
    """根据替换模式获取断开连接按钮的显示文本"""
    button_labels = {
        'ALL': "断开所有连接",
        'SPECIFIC': "断开特定连接",
        'MATERIAL': "断开特定材质连接",
        'MATERIAL_SPECIFIC': "断开特定材质中的特定连接"
    }
    return button_labels.get(replace_mode, "断开所有连接")


def draw_shader_selector(layout, props, nodegroup_prop, builtin_prop, label_text):
    """
    统一的着色器选择器UI组件

    参数:
        layout: UI布局对象
        props: 属性集合对象
        nodegroup_prop: 节点组PointerProperty属性名
        builtin_prop: 内置着色器EnumProperty属性名
        label_text: 标签文字
    """
    box = layout.box()
    box.label(text=label_text, icon='NODE_MATERIAL')

    # 第一行: 内置着色器下拉框
    row = box.row(align=True)
    row.label(text="内置:")
    row.prop(props, builtin_prop, text="")

    # 第二行: 节点组 prop_search 搜索框 - 完美支持中文
    row = box.row(align=True)
    row.label(text="节点组:")
    row.prop_search(props, nodegroup_prop, bpy.data,
                    "node_groups", text="", icon='NODETREE')

    # 显示当前选中的信息
    builtin_value = getattr(props, builtin_prop)
    nodegroup_value = getattr(props, nodegroup_prop)

    if nodegroup_value:
        box.label(text=f"✓ 已选择节点组: {nodegroup_value.name}", icon='CHECKMARK')
    elif builtin_value and builtin_value != 'NONE':
        # 显示内置着色器的中文名称
        builtin_name = NodeTypeConfig.BUILTIN_SHADERS_FOR_MENU
        for item in builtin_name:
            if item[0] == builtin_value:
                box.label(text=f"✓ 已选择内置: {item[1]}", icon='CHECKMARK')
                break

    return box


class MATERIAL_UL_connection_rule_list(UIList):
    """连接规则列表UI"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # 源节点显示
            if item.source_match_mode == 'LABEL':
                source_text = item.source_node_label if item.source_node_label else "未设置"
            else:
                if item.source_node_type and item.source_node_type in NODE_TYPE_NAMES:
                    source_text = NODE_TYPE_NAMES[item.source_node_type]
                else:
                    source_text = item.source_node_type if item.source_node_type else "未设置"

            # 目标节点显示
            if item.target_match_mode == 'LABEL':
                target_text = item.target_node_label if item.target_node_label else "未设置"
            else:
                if item.target_node_type and item.target_node_type in NODE_TYPE_NAMES:
                    target_text = NODE_TYPE_NAMES[item.target_node_type]
                else:
                    target_text = item.target_node_type if item.target_node_type else "未设置"

            row.label(text=f"{source_text}[{item.source_socket_index}]")
            row.label(text="→", icon='FORWARD')
            row.label(text=f"{target_text}[{item.target_socket_index}]")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='LINKED')


class MATERIAL_PT_shader_replacer_panel(Panel):
    """材质着色器替换面板 - 放在3D视图侧边栏"""

    bl_label = "材质替换工具"
    bl_idname = "MATERIAL_PT_shader_replacer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '材质工具'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.shader_replacer_props

        # 使用统一的着色器选择器
        draw_shader_selector(
            layout, props,
            nodegroup_prop="shader_nodegroup",
            builtin_prop="builtin_shader",
            label_text="目标着色器:"
        )

        # 目标选择
        box = layout.box()
        box.label(text="目标选择:", icon='OBJECT_DATA')
        row = box.row()
        row.prop(props, "target_type", expand=True)

        # 替换设置
        box = layout.box()
        box.label(text="替换设置:", icon='TOOL_SETTINGS')
        box.prop(props, "replace_mode", text="")

        # 当选择"替换特定着色器"模式时,显示特定着色器选择（在替换设置和自动连接之间）
        if props.replace_mode == 'SPECIFIC':
            # 使用统一的着色器选择器
            draw_shader_selector(
                layout, props,
                nodegroup_prop="specific_nodegroup",
                builtin_prop="specific_builtin_shader",
                label_text="要替换的着色器:"
            )

        # 当选择"替换特定材质"模式时,显示材质选择器（在替换设置和自动连接之间）
        elif props.replace_mode == 'MATERIAL':
            material_box = layout.box()
            material_box.label(text="目标材质:", icon='MATERIAL')

            # prop_search 材质搜索框 - 完美支持中文
            row = material_box.row(align=True)
            row.prop_search(props, "target_material", bpy.data, "materials",
                            text="", icon='MATERIAL_DATA')

            # 显示当前选中的材质信息
            if props.target_material:
                material_box.label(
                    text=f"✓ 已选择: {props.target_material.name}", icon='CHECKMARK')
            else:
                material_box.label(text="⚠ 请选择要替换的材质", icon='INFO')

        # 当选择"替换特定材质中的特定着色器"模式时
        elif props.replace_mode == 'MATERIAL_SPECIFIC':
            # 材质选择器
            material_box = layout.box()
            material_box.label(text="目标材质:", icon='MATERIAL')

            row = material_box.row(align=True)
            row.prop_search(props, "target_material", bpy.data, "materials",
                            text="", icon='MATERIAL_DATA')

            if props.target_material:
                material_box.label(
                    text=f"✓ 已选择: {props.target_material.name}", icon='CHECKMARK')
            else:
                material_box.label(text="⚠ 请选择要替换的材质", icon='INFO')

            # 特定着色器选择器（在材质选择和自动连接之间）
            draw_shader_selector(
                layout, props,
                nodegroup_prop="material_specific_nodegroup",
                builtin_prop="material_specific_builtin_shader",
                label_text="要替换的着色器:"
            )

        # 当选择"替换特定材质中的特定着色器"模式时
        elif props.replace_mode == 'MATERIAL_SPECIFIC':
            # 材质选择器
            material_box = layout.box()
            material_box.label(text="目标材质:", icon='MATERIAL')

            row = material_box.row(align=True)
            row.prop_search(props, "target_material", bpy.data, "materials",
                            text="", icon='MATERIAL_DATA')

            if props.target_material:
                material_box.label(
                    text=f"✓ 已选择: {props.target_material.name}", icon='CHECKMARK')
            else:
                material_box.label(text="⚠ 请选择要替换的材质", icon='INFO')

            # 特定着色器选择器（在材质选择和自动连接之间）
            draw_shader_selector(
                layout, props,
                nodegroup_prop="material_specific_nodegroup",
                builtin_prop="material_specific_builtin_shader",
                label_text="要替换的着色器:"
            )

        # 连接选项
        box = layout.box()
        box.prop(props, "auto_connect")

        # 高级选项
        box = layout.box()
        box.prop(props, "advanced_options", icon='PREFERENCES')
        if props.advanced_options:
            self.draw_advanced_options(context, box, props)

        # 执行按钮
        col = layout.column()
        col.scale_y = 1.5
        col.operator("material.batch_replace_shader",
                     text="批量替换着色器", icon='MATERIAL')

    def draw_advanced_options(self, context, parent_box, props):
        """绘制高级选项"""
        advanced_box = parent_box.box()
        advanced_box.label(text="高级连接设置:", icon='LINKED')

        # 断开和重新连接按钮
        row = advanced_box.row(align=True)
        disconnect_label = get_disconnect_button_label(props.replace_mode)
        row.operator("material.disconnect_all_connections",
                     text=disconnect_label, icon='X')
        row.operator("material.reconnect_with_rules",
                     text="使用规则重新连接", icon='LINKED')

        # 连接快照状态显示
        if props.connection_snapshot:
            snapshot_count = len(props.connection_snapshot)
            snapshot_box = advanced_box.box()
            row = snapshot_box.row(align=True)
            row.label(text=f"已记录 {snapshot_count} 个连接关系", icon='INFO')
            row.operator("material.clear_connection_snapshot", text="清空快照", icon='TRASH')
        else:
            row = advanced_box.row(align=True)
            row.label(text="暂无连接关系记录", icon='INFO')
        
        # 连接关系记录启用/禁用开关（动态文本）
        row = advanced_box.row(align=True)
        record_text = "禁用连接关系记录" if props.enable_connection_recording else "启用连接关系记录"
        row.prop(props, "enable_connection_recording", text=record_text)

        # 连接规则说明
        advanced_box.label(text="自定义连接规则:")

        # 连接规则列表
        row = advanced_box.row()
        row.template_list(
            "MATERIAL_UL_connection_rule_list", "",
            props, "connection_rules",
            props, "active_rule_index",
            rows=3
        )

        # 添加/删除规则按钮
        col = row.column(align=True)
        col.operator("material.add_connection_rule", icon='ADD', text="")
        col.operator("material.remove_connection_rule", icon='REMOVE', text="")

        # 显示当前选中规则的详细设置
        if props.connection_rules and 0 <= props.active_rule_index < len(props.connection_rules):
            rule = props.connection_rules[props.active_rule_index]

            rule_box = advanced_box.box()
            rule_box.label(
                text=f"规则 {props.active_rule_index + 1} 详细设置:", icon='SETTINGS')

            # 源节点设置
            source_box = rule_box.box()
            source_box.label(text="源节点 (输出端):", icon='EXPORT')
            source_box.prop(rule, "source_match_mode", text="匹配方式")

            if rule.source_match_mode == 'LABEL':
                source_box.prop(rule, "source_node_label", text="标签/名称")
            else:
                source_box.prop(rule, "source_node_type", text="节点类型")

            source_box.prop(rule, "source_socket_index", text="输出接口索引")

            # 目标节点设置
            target_box = rule_box.box()
            target_box.label(text="目标节点 (输入端):", icon='IMPORT')
            target_box.prop(rule, "target_match_mode", text="匹配方式")

            if rule.target_match_mode == 'LABEL':
                target_box.prop(rule, "target_node_label", text="标签/名称")
            else:
                target_box.prop(rule, "target_node_type", text="节点类型")

            target_box.prop(rule, "target_socket_index", text="输入接口索引")


class MATERIAL_PT_shader_replacer_material(Panel):
    """材质属性面板中的替换工具"""

    bl_label = "材质替换工具"
    bl_idname = "MATERIAL_PT_shader_replacer_material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.shader_replacer_props

        # 使用统一的着色器选择器
        draw_shader_selector(
            layout, props,
            nodegroup_prop="shader_nodegroup",
            builtin_prop="builtin_shader",
            label_text="目标着色器:"
        )

        # 目标选择
        box = layout.box()
        box.label(text="目标选择:", icon='OBJECT_DATA')
        row = box.row()
        row.prop(props, "target_type", expand=True)

        # 替换模式
        box = layout.box()
        box.label(text="替换设置:", icon='TOOL_SETTINGS')
        box.prop(props, "replace_mode", text="")

        # 当选择"替换特定着色器"模式时（在替换设置和自动连接之间）
        if props.replace_mode == 'SPECIFIC':
            # 使用统一的着色器选择器
            draw_shader_selector(
                layout, props,
                nodegroup_prop="specific_nodegroup",
                builtin_prop="specific_builtin_shader",
                label_text="要替换的着色器:"
            )

        # 当选择"替换特定材质"模式时,显示材质选择器（在替换设置和自动连接之间）
        elif props.replace_mode == 'MATERIAL':
            material_box = layout.box()
            material_box.label(text="目标材质:", icon='MATERIAL')

            # prop_search 材质搜索框 - 完美支持中文
            row = material_box.row(align=True)
            row.prop_search(props, "target_material", bpy.data, "materials",
                            text="", icon='MATERIAL_DATA')

            # 显示当前选中的材质信息
            if props.target_material:
                material_box.label(
                    text=f"✓ 已选择: {props.target_material.name}", icon='CHECKMARK')
            else:
                material_box.label(text="⚠ 请选择要替换的材质", icon='INFO')

        # 连接选项
        box = layout.box()
        box.prop(props, "auto_connect")

        # 高级选项
        box = layout.box()
        box.prop(props, "advanced_options", icon='PREFERENCES')
        if props.advanced_options:
            self.draw_advanced_options(context, box, props)

        # 执行按钮
        col = layout.column()
        col.scale_y = 1.5
        col.operator(
            "material.batch_replace_shader",
            text="批量替换着色器",
            icon='MATERIAL'
        )

    def draw_advanced_options(self, context, parent_box, props):
        """绘制高级选项"""
        advanced_box = parent_box.box()
        advanced_box.label(text="高级连接设置:", icon='LINKED')

        # 断开和重新连接按钮
        row = advanced_box.row(align=True)
        disconnect_label = get_disconnect_button_label(props.replace_mode)
        row.operator("material.disconnect_all_connections",
                     text=disconnect_label, icon='X')
        row.operator("material.reconnect_with_rules",
                     text="使用规则重新连接", icon='LINKED')

        # 连接快照状态显示
        if props.connection_snapshot:
            snapshot_count = len(props.connection_snapshot)
            snapshot_box = advanced_box.box()
            row = snapshot_box.row(align=True)
            row.label(text=f"已记录 {snapshot_count} 个连接关系", icon='INFO')
            row.operator("material.clear_connection_snapshot", text="清空快照", icon='TRASH')
        else:
            row = advanced_box.row(align=True)
            row.label(text="暂无连接关系记录", icon='INFO')
        
        # 连接关系记录启用/禁用开关（动态文本）
        row = advanced_box.row(align=True)
        record_text = "禁用连接关系记录" if props.enable_connection_recording else "启用连接关系记录"
        row.prop(props, "enable_connection_recording", text=record_text)

        # 连接规则说明
        advanced_box.label(text="自定义连接规则:")

        # 连接规则列表
        row = advanced_box.row()
        row.template_list(
            "MATERIAL_UL_connection_rule_list", "",
            props, "connection_rules",
            props, "active_rule_index",
            rows=3
        )

        # 添加/删除规则按钮
        col = row.column(align=True)
        col.operator("material.add_connection_rule", icon='ADD', text="")
        col.operator("material.remove_connection_rule", icon='REMOVE', text="")

        # 显示当前选中规则的详细设置
        if props.connection_rules and 0 <= props.active_rule_index < len(props.connection_rules):
            rule = props.connection_rules[props.active_rule_index]

            rule_box = advanced_box.box()
            rule_box.label(
                text=f"规则 {props.active_rule_index + 1} 详细设置:", icon='SETTINGS')

            # 源节点设置
            source_box = rule_box.box()
            source_box.label(text="源节点 (输出端):", icon='EXPORT')
            source_box.prop(rule, "source_match_mode", text="匹配方式")

            if rule.source_match_mode == 'LABEL':
                source_box.prop(rule, "source_node_label", text="标签/名称")
            else:
                source_box.prop(rule, "source_node_type", text="节点类型")

            source_box.prop(rule, "source_socket_index", text="输出接口索引")

            # 目标节点设置
            target_box = rule_box.box()
            target_box.label(text="目标节点 (输入端):", icon='IMPORT')
            target_box.prop(rule, "target_match_mode", text="匹配方式")

            if rule.target_match_mode == 'LABEL':
                target_box.prop(rule, "target_node_label", text="标签/名称")
            else:
                target_box.prop(rule, "target_node_type", text="节点类型")

            target_box.prop(rule, "target_socket_index", text="输入接口索引")
