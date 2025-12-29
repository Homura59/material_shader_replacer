"""
操作符模块
定义插件的所有操作符
"""

import bpy
from bpy.types import Operator
from .node_config import (
    NodeTypeConfig,
    SocketSemantics,
    AutoConnectionRules,
    get_node_label_or_name,
    match_node_by_label_or_name,
    match_node_by_type,
    _get_sorted_shader_node_groups
)
from .cache import MaterialCache
from .error_handler import safe_link, safe_remove_node


class MATERIAL_OT_add_connection_rule(Operator):
    """添加连接规则"""

    bl_idname = "material.add_connection_rule"
    bl_label = "添加连接规则"
    bl_description = "添加一个新的连接规则"

    def execute(self, context):
        scene = context.scene
        props = scene.shader_replacer_props
        props.connection_rules.add()
        props.active_rule_index = len(props.connection_rules) - 1
        return {'FINISHED'}


class MATERIAL_OT_remove_connection_rule(Operator):
    """移除连接规则"""

    bl_idname = "material.remove_connection_rule"
    bl_label = "移除连接规则"
    bl_description = "移除选中的连接规则"

    def execute(self, context):
        scene = context.scene
        props = scene.shader_replacer_props
        index = props.active_rule_index
        if 0 <= index < len(props.connection_rules):
            props.connection_rules.remove(index)
            if props.active_rule_index >= len(props.connection_rules):
                props.active_rule_index = len(props.connection_rules) - 1
        return {'FINISHED'}


class MATERIAL_OT_clear_connection_snapshot(Operator):
    """清空连接快照"""

    bl_idname = "material.clear_connection_snapshot"
    bl_label = "清空连接快照"
    bl_description = "清空已记录的连接关系快照"

    def execute(self, context):
        scene = context.scene
        props = scene.shader_replacer_props

        while len(props.connection_snapshot) > 0:
            props.connection_snapshot.remove(0)

        self.report({'INFO'}, "已清空连接快照")
        return {'FINISHED'}


class MATERIAL_OT_disconnect_all_connections(Operator):
    """断开连接（根据替换模式动态确定范围，同时记录连接关系用于后续恢复）"""

    bl_idname = "material.disconnect_all_connections"
    bl_label = "断开所有连接"
    bl_description = "断开选中物体全部材质全部节点之间的连接"

    def get_disconnect_button_label(self, replace_mode):
        """根据替换模式获取按钮显示文本"""
        button_labels = {
            'ALL': "断开所有连接",
            'SPECIFIC': "断开特定连接",
            'MATERIAL': "断开特定材质连接",
            'MATERIAL_SPECIFIC': "断开特定材质中的特定连接"
        }
        return button_labels.get(replace_mode, "断开所有连接")

    def get_shader_types_to_disconnect(self, props):
        """根据替换模式获取需要断开连接的着色器类型列表"""
        shader_types = []

        if props.replace_mode == 'SPECIFIC':
            if props.specific_builtin_shader and props.specific_builtin_shader != 'NONE':
                shader_types.append(props.specific_builtin_shader)
            if props.specific_nodegroup and props.specific_nodegroup.name:
                shader_types.append(f"GROUP:{props.specific_nodegroup.name}")
        elif props.replace_mode == 'MATERIAL_SPECIFIC':
            if props.material_specific_builtin_shader and props.material_specific_builtin_shader != 'NONE':
                shader_types.append(props.material_specific_builtin_shader)
            if props.material_specific_nodegroup and props.material_specific_nodegroup.name:
                shader_types.append(f"GROUP:{props.material_specific_nodegroup.name}")
        elif props.replace_mode == 'MATERIAL':
            if props.target_material:
                shader_types = ['ALL']
            else:
                shader_types = []
        else:
            shader_types = ['ALL']

        return shader_types

    def _record_connection(self, snapshot_collection, link, material_name, replace_mode, shader_type):
        """将单个连接记录到快照集合中"""
        from_node = link.from_node
        to_node = link.to_node
        from_socket = link.from_socket
        to_socket = link.to_socket

        from_socket_index = 0
        if from_node and from_socket:
            for i, output in enumerate(from_node.outputs):
                if output == from_socket or output.name == from_socket.name:
                    from_socket_index = i
                    break

        to_socket_index = 0
        if to_node and to_socket:
            for i, input_socket in enumerate(to_node.inputs):
                if input_socket == to_socket or input_socket.name == to_socket.name:
                    to_socket_index = i
                    break

        item = snapshot_collection.add()
        item.material_name = material_name
        item.from_node_name = from_node.name if from_node else ""
        item.from_node_type = from_node.type if from_node else ""
        item.from_socket_name = from_socket.name if from_socket else ""
        item.from_socket_index = from_socket_index
        item.from_socket_type = from_socket.bl_idname if from_socket else ""
        item.to_node_name = to_node.name if to_node else ""
        item.to_node_type = to_node.type if to_node else ""
        item.to_socket_name = to_socket.name if to_socket else ""
        item.to_socket_index = to_socket_index
        item.to_socket_type = to_socket.bl_idname if to_socket else ""
        item.replace_mode = replace_mode
        item.shader_type = shader_type

    def _clear_snapshot(self, props):
        """清空连接快照"""
        while len(props.connection_snapshot) > 0:
            props.connection_snapshot.remove(0)

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "没有选中任何对象")
            return {'CANCELLED'}

        scene = context.scene
        props = scene.shader_replacer_props

        shader_types = self.get_shader_types_to_disconnect(props)

        if props.replace_mode == 'MATERIAL' and not props.target_material:
            self.report({'WARNING'}, "请先选择目标材质")
            return {'CANCELLED'}

        disconnected_count = 0

        self._clear_snapshot(props)

        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material.use_nodes:
                        mat = slot.material
                        node_tree = mat.node_tree
                        links = node_tree.links
                        nodes = node_tree.nodes

                        should_process = True

                        if props.replace_mode in ('MATERIAL', 'MATERIAL_SPECIFIC'):
                            if props.target_material:
                                should_process = (mat.name == props.target_material.name)

                        if not should_process:
                            continue

                        links_to_remove = []
                        links_to_record = []

                        if 'ALL' in shader_types:
                            links_to_remove = list(links)
                            links_to_record = list(links)
                        else:
                            for link in links:
                                from_node = link.from_node
                                to_node = link.to_node

                                should_remove = False

                                for shader_type in shader_types:
                                    if shader_type.startswith('GROUP:'):
                                        group_name = shader_type[6:]
                                        if from_node and from_node.type == 'GROUP':
                                            if from_node.node_tree and from_node.node_tree.name == group_name:
                                                should_remove = True
                                        if to_node and to_node.type == 'GROUP':
                                            if to_node.node_tree and to_node.node_tree.name == group_name:
                                                should_remove = True
                                    else:
                                        if from_node and from_node.type == shader_type:
                                            should_remove = True
                                        if to_node and to_node.type == shader_type:
                                            should_remove = True

                                if should_remove:
                                    links_to_remove.append(link)
                                    links_to_record.append(link)

                        shader_type_str = ','.join(shader_types) if shader_types else 'ALL'

                        for link in links_to_record:
                            self._record_connection(
                                props.connection_snapshot,
                                link,
                                mat.name,
                                props.replace_mode,
                                shader_type_str
                            )

                        for link in links_to_remove:
                            links.remove(link)
                            disconnected_count += 1

        if props.replace_mode == 'ALL':
            report_msg = f"已断开 {disconnected_count} 个连接（已记录连接关系）"
        elif props.replace_mode == 'SPECIFIC':
            report_msg = f"已断开特定着色器的 {disconnected_count} 个连接（已记录连接关系）"
        elif props.replace_mode == 'MATERIAL':
            report_msg = f"已断开目标材质的 {disconnected_count} 个连接（已记录连接关系）"
        else:
            report_msg = f"已断开特定材质中特定着色器的 {disconnected_count} 个连接（已记录连接关系）"

        self.report({'INFO'}, report_msg)
        return {'FINISHED'}


class MATERIAL_OT_reconnect_with_rules(Operator):
    """使用规则重新连接（根据替换模式动态确定范围，同时应用保存的连接快照）"""
    bl_idname = "material.reconnect_with_rules"
    bl_label = "使用规则重新连接"
    bl_description = "根据自动连接开关状态决定连接方式：开启时先自动连接再应用自定义规则，关闭时只应用自定义规则"

    def get_shader_types_to_reconnect(self, props):
        """根据替换模式获取需要重连的着色器类型列表"""
        shader_types = []

        if props.replace_mode == 'SPECIFIC':
            if props.specific_builtin_shader and props.specific_builtin_shader != 'NONE':
                shader_types.append(props.specific_builtin_shader)
            if props.specific_nodegroup and props.specific_nodegroup.name:
                shader_types.append(f"GROUP:{props.specific_nodegroup.name}")
        elif props.replace_mode == 'MATERIAL_SPECIFIC':
            if props.material_specific_builtin_shader and props.material_specific_builtin_shader != 'NONE':
                shader_types.append(props.material_specific_builtin_shader)
            if props.material_specific_nodegroup and props.material_specific_nodegroup.name:
                shader_types.append(f"GROUP:{props.material_specific_nodegroup.name}")
        elif props.replace_mode == 'MATERIAL':
            if props.target_material:
                shader_types = ['ALL']
            else:
                shader_types = []
        else:
            shader_types = ['ALL']

        return shader_types

    def _restore_connections_from_snapshot(self, props, node_tree, material_name):
        """从快照中恢复指定材质的连接关系"""
        restored_count = 0

        for snapshot_item in props.connection_snapshot:
            if snapshot_item.material_name != material_name:
                continue

            from_node_name = snapshot_item.from_node_name
            to_node_name = snapshot_item.to_node_name
            from_socket_index = snapshot_item.from_socket_index
            to_socket_index = snapshot_item.to_socket_index

            if not from_node_name or not to_node_name:
                continue

            from_node = node_tree.nodes.get(from_node_name)
            to_node = node_tree.nodes.get(to_node_name)

            if not from_node or not to_node:
                continue

            if from_socket_index < len(from_node.outputs) and to_socket_index < len(to_node.inputs):
                source_socket = from_node.outputs[from_socket_index]
                target_socket = to_node.inputs[to_socket_index]

                if safe_link(node_tree.links, source_socket, target_socket):
                    restored_count += 1

        return restored_count

    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "没有选中任何对象")
            return {'CANCELLED'}

        scene = context.scene
        props = scene.shader_replacer_props

        shader_types = self.get_shader_types_to_reconnect(props)

        auto_connect_count = 0
        custom_rule_count = 0
        restored_count = 0
        processed_materials = set()

        has_snapshot = len(props.connection_snapshot) > 0

        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material.use_nodes:
                        mat = slot.material

                        if mat.name in processed_materials:
                            continue

                        should_process = True
                        if props.replace_mode in ('MATERIAL', 'MATERIAL_SPECIFIC'):
                            if props.target_material:
                                should_process = (mat.name == props.target_material.name)

                        if not should_process:
                            continue

                        processed_materials.add(mat.name)
                        node_tree = mat.node_tree
                        nodes = node_tree.nodes
                        links = node_tree.links

                        if props.auto_connect:
                            auto_connect_count += AutoConnectionRules.apply_auto_connections(
                                nodes, links, props)

                        for rule in props.connection_rules:
                            source_nodes = []
                            if rule.source_match_mode == 'LABEL':
                                if rule.source_node_label:
                                    source_nodes = [n for n in nodes if match_node_by_label_or_name(
                                        n, rule.source_node_label)]
                            else:
                                if rule.source_node_type and not rule.source_node_type.startswith('__'):
                                    source_nodes = [n for n in nodes if match_node_by_type(
                                        n, rule.source_node_type)]

                            target_nodes = []
                            if rule.target_match_mode == 'LABEL':
                                if rule.target_node_label:
                                    target_nodes = [n for n in nodes if match_node_by_label_or_name(
                                        n, rule.target_node_label)]
                            else:
                                if rule.target_node_type and not rule.target_node_type.startswith('__'):
                                    target_nodes = [n for n in nodes if match_node_by_type(
                                        n, rule.target_node_type)]

                            for source_node in source_nodes:
                                for target_node in target_nodes:
                                    if source_node == target_node:
                                        continue

                                    if (rule.source_socket_index < len(source_node.outputs) and
                                            rule.target_socket_index < len(target_node.inputs)):

                                        source_socket = source_node.outputs[rule.source_socket_index]
                                        target_socket = target_node.inputs[rule.target_socket_index]

                                        if not safe_link(links, source_socket, target_socket):
                                            print(
                                                f"连接失败: {source_node.name}[{rule.source_socket_index}] -> {target_node.name}[{rule.target_socket_index}]")
                                        else:
                                            custom_rule_count += 1

                        if has_snapshot:
                            restored_count += self._restore_connections_from_snapshot(
                                props, node_tree, mat.name)

        if has_snapshot:
            if props.auto_connect:
                self.report(
                    {'INFO'}, f"自动连接: {auto_connect_count}, 自定义规则: {custom_rule_count}, 恢复连接: {restored_count}")
            else:
                self.report(
                    {'INFO'}, f"自定义规则: {custom_rule_count}, 恢复连接: {restored_count} (自动连接已关闭)")
        else:
            if props.auto_connect:
                self.report(
                    {'INFO'}, f"自动连接: {auto_connect_count} 个, 自定义规则连接: {custom_rule_count} 个")
            else:
                self.report({'INFO'}, f"自定义规则连接: {custom_rule_count} 个 (自动连接已关闭)")

        return {'FINISHED'}


class MATERIAL_OT_batch_replace_shader(Operator):
    """批量替换材质着色器操作符"""

    bl_idname = "material.batch_replace_shader"
    bl_label = "批量替换材质着色器"
    bl_description = "在选定对象或集合上批量替换材质中的着色器"
    bl_options = {'REGISTER', 'UNDO'}

    def _get_type_compatibility_score(self, output_type, input_type):
        """计算类型兼容性分数（0-100）"""
        # 完全匹配
        if output_type == input_type:
            return 100

        # 兼容性矩阵
        compatibility = {
            ('RGBA', 'RGBA'): 100,
            ('RGBA', 'VECTOR'): 80,
            ('RGBA', 'VALUE'): 60,
            ('VECTOR', 'VECTOR'): 100,
            ('VECTOR', 'RGBA'): 80,
            ('VALUE', 'VALUE'): 100,
            ('VALUE', 'RGBA'): 60,
            ('SHADER', 'SHADER'): 100,
        }

        return compatibility.get((output_type, input_type), 0)

    def get_socket_index(self, socket_collection, target_socket):
        """
        安全地获取 socket 在集合中的索引

        参数:
            socket_collection: inputs 或 outputs 集合
            target_socket: 要查找的 socket
        返回:
            索引值，如果未找到返回 -1
        """
        try:
            for i, socket in enumerate(socket_collection):
                if socket == target_socket:
                    return i
        except ReferenceError:
            pass
        return -1

    def _find_alpha_input(self, shader_node):
        """
        查找着色器节点的 Alpha 输入接口

        参数:
            shader_node: 着色器节点
        返回:
            Alpha 输入接口，或 None
        """
        # 常见的 Alpha 输入名称
        alpha_names = ['alpha', 'Alpha', 'Opacity',
                       'opacity', '透明度', '不透明度', 'Fac']

        for inp in shader_node.inputs:
            if inp.name in alpha_names:
                return inp

        return None

    def _find_best_input_for_image_texture(self, shader_node, socket_type, connected_inputs, is_alpha=False):
        """
        为图像纹理查找最佳输入接口

        参数:
            shader_node: 着色器节点
            socket_type: 接口类型 ('RGBA' 或 'VALUE')
            connected_inputs: 已连接的输入集合
            is_alpha: 是否是 Alpha 输出
        返回:
            最佳匹配的输入接口，或 None
        """
        if is_alpha:
            # Alpha 输出：只连接明确的 alpha 相关接口
            alpha_keywords = ['alpha', 'opacity', 'transparency', '透明']
            matching_inputs = []

            for idx, inp in enumerate(shader_node.inputs):
                if inp in connected_inputs:
                    continue
                inp_name_lower = inp.name.lower()
                if any(kw in inp_name_lower for kw in alpha_keywords):
                    matching_inputs.append((idx, inp))

            # 返回序号最小的匹配接口
            if matching_inputs:
                matching_inputs.sort(key=lambda x: x[0])
                return matching_inputs[0][1]

            # 没有匹配则不连接
            return None

        else:
            # Color 输出：按优先级查找颜色相关接口
            color_keywords = [
                'base color', 'basecolor',  # 最高优先级
                'color', '颜色',             # 第二优先级（包含"颜色"的都在这里）
                'diffuse', '漫反射',         # 第三优先级
                'albedo', '反照率', '基础色',  # 第四优先级
            ]

            # 按关键词优先级查找
            for keyword in color_keywords:
                matching_inputs = []
                for idx, inp in enumerate(shader_node.inputs):
                    if inp in connected_inputs:
                        continue
                    inp_name_lower = inp.name.lower()

                    # 检查是否包含关键词
                    if keyword in inp_name_lower:
                        matching_inputs.append((idx, inp))

                # 找到匹配的关键词，返回序号最小的
                if matching_inputs:
                    matching_inputs.sort(key=lambda x: x[0])
                    return matching_inputs[0][1]

            # 没有匹配颜色关键词，使用原有规则（语义匹配）
            return None

    def _find_best_input_socket(self, shader_node, original_name, original_type, connected_inputs):
        """
        智能查找最佳匹配的输入接口

        评分系统：
        - 名称完全匹配: +100
        - 名称部分匹配: +50
        - 语义匹配: +0~100
        - 类型兼容: +0~100
        - 接口位置: 越靠前越优先 +10~1
        """

        original_semantic = SocketSemantics.get_socket_semantic(original_name)
        candidates = []

        for idx, inp in enumerate(shader_node.inputs):
            if inp in connected_inputs:
                continue

            score = 0

            # 1. 名称匹配（最高优先级）
            if inp.name == original_name:
                score += 100
            elif inp.name.lower() == original_name.lower():
                score += 90
            elif original_name.lower() in inp.name.lower() or inp.name.lower() in original_name.lower():
                score += 50

            # 2. 语义匹配
            input_semantic = SocketSemantics.get_socket_semantic(inp.name)
            semantic_score = SocketSemantics.are_semantically_compatible(
                original_semantic, input_semantic)
            score += semantic_score * 0.8  # 权重0.8

            # 3. 类型兼容性
            type_score = self._get_type_compatibility_score(
                original_type, inp.type)
            score += type_score * 0.6  # 权重0.6

            # 4. 位置优先级（前面的接口优先）
            position_score = max(0, 10 - idx)
            score += position_score

            candidates.append((inp, score))

        # 按分数排序，返回最高分
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_socket, best_score = candidates[0]

            # 只有分数足够高才连接（避免错误连接）
            if best_score >= 30:
                return best_socket

        return None

    def _find_best_output_socket(self, shader_node, original_name, original_type, connected_outputs):
        """
        智能查找最佳匹配的输出接口

        优先级：
        1. 相同名称的接口
        2. 第一个相同类型的接口

        参数:
            shader_node: 新着色器节点
            original_name: 原始接口名称
            original_type: 原始接口类型
            connected_outputs: 已使用的输出接口集合
        返回:
            最佳匹配的输出接口，或 None
        """
        # 规则1：优先匹配相同名称的接口
        if original_name in shader_node.outputs:
            return shader_node.outputs[original_name]

        # 尝试不区分大小写匹配
        original_name_lower = original_name.lower()
        for out in shader_node.outputs:
            if out.name.lower() == original_name_lower:
                return out

        # 规则2：查找第一个相同类型的接口
        for out in shader_node.outputs:
            if out.type == original_type:
                return out

        # 如果没有匹配，返回第一个输出
        if len(shader_node.outputs) > 0:
            return shader_node.outputs[0]

        return None

    def _find_shader_output(self, shader_node):
        """
        查找着色器节点的 SHADER 类型输出接口
        优先返回第一个 SHADER 类型输出

        参数:
            shader_node: 着色器节点
        返回:
            SHADER 类型输出接口，或第一个输出，或 None
        """
        for out in shader_node.outputs:
            if out.type == 'SHADER':
                return out

        # 如果没有 SHADER 类型，返回第一个输出
        if len(shader_node.outputs) > 0:
            return shader_node.outputs[0]

        return None

    def execute(self, context):
        """执行替换操作"""
        scene = context.scene
        props = scene.shader_replacer_props

        # 获取目标着色器名称 - 优先级: builtin_shader > nodegroup
        target_shader_name = ""

        # 优先检查内置着色器
        if props.builtin_shader and props.builtin_shader != 'NONE':
            target_shader_name = props.builtin_shader
        # 其次检查 prop_search 选择的节点组(完美支持中文)
        elif props.shader_nodegroup:
            target_shader_name = props.shader_nodegroup.name

        # 验证目标着色器
        if not target_shader_name:
            self.report({'ERROR'}, "请选择目标着色器（内置或节点组）")
            return {'CANCELLED'}

        # 验证着色器是否存在
        node_group_exists = any(
            ng.name == target_shader_name
            for ng in bpy.data.node_groups
            if ng.type == 'SHADER'
        )

        if not node_group_exists and not NodeTypeConfig.is_valid_builtin_shader(target_shader_name):
            self.report({'ERROR'}, f"未找到着色器: '{target_shader_name}',请检查名称是否正确")
            return {'CANCELLED'}

        # 获取要替换的特定着色器名称
        specific_shader_name = ""
        if props.replace_mode == 'SPECIFIC':
            # 优先检查内置着色器
            if props.specific_builtin_shader and props.specific_builtin_shader != 'NONE':
                specific_shader_name = props.specific_builtin_shader
            # 其次检查 prop_search 选择的节点组
            elif props.specific_nodegroup:
                specific_shader_name = props.specific_nodegroup.name

            if not specific_shader_name:
                self.report({'ERROR'}, "请选择要替换的特定着色器（内置或节点组）")
                return {'CANCELLED'}

        # 处理替换特定材质模式
        if props.replace_mode == 'MATERIAL':
            if not props.target_material:
                self.report({'ERROR'}, "请选择要替换的目标材质")
                return {'CANCELLED'}

            # 直接处理特定材质
            mat = props.target_material
            if not mat.use_nodes:
                self.report({'WARNING'}, f"材质 '{mat.name}' 未启用节点")
                return {'CANCELLED'}

            # 清空材质缓存
            MaterialCache.clear()

            # 材质模式下默认替换所有着色器
            specific_shader_name = ""
            result = self.replace_material_shaders(
                mat, props, target_shader_name, specific_shader_name)

            if result > 0:
                self.report(
                    {'INFO'},
                    f"替换完成！在材质 '{mat.name}' 中成功替换 {result} 个着色器节点"
                )
            else:
                self.report(
                    {'WARNING'},
                    f"在材质 '{mat.name}' 中没有找到需要替换的着色器"
                )

            return {'FINISHED'}

        # 处理替换特定材质中的特定着色器模式
        if props.replace_mode == 'MATERIAL_SPECIFIC':
            if not props.target_material:
                self.report({'ERROR'}, "请选择要替换的目标材质")
                return {'CANCELLED'}

            mat = props.target_material
            if not mat.use_nodes:
                self.report({'WARNING'}, f"材质 '{mat.name}' 未启用节点")
                return {'CANCELLED'}

            # 获取材质模式下的特定着色器名称
            material_specific_shader_name = ""
            if props.material_specific_builtin_shader and props.material_specific_builtin_shader != 'NONE':
                material_specific_shader_name = props.material_specific_builtin_shader
            elif props.material_specific_nodegroup:
                material_specific_shader_name = props.material_specific_nodegroup.name

            # 清空材质缓存
            MaterialCache.clear()

            result = self.replace_material_shaders(
                mat, props, target_shader_name, material_specific_shader_name)

            if result > 0:
                if material_specific_shader_name:
                    self.report(
                        {'INFO'},
                        f"在材质 '{mat.name}' 中成功替换 {result} 个 '{material_specific_shader_name}' 着色器节点"
                    )
                else:
                    self.report(
                        {'INFO'},
                        f"在材质 '{mat.name}' 中成功替换 {result} 个着色器节点"
                    )
            else:
                if material_specific_shader_name:
                    self.report(
                        {'WARNING'},
                        f"在材质 '{mat.name}' 中没有找到需要替换的 '{material_specific_shader_name}' 着色器"
                    )
                else:
                    self.report(
                        {'WARNING'},
                        f"在材质 '{mat.name}' 中没有找到需要替换的着色器"
                    )

            return {'FINISHED'}

        # 获取目标对象列表
        target_objects = self.get_target_objects(context, props.target_type)

        if not target_objects:
            self.report({'WARNING'}, "没有找到目标对象，请先选择对象或确认集合中有对象")
            return {'CANCELLED'}

        # 清空材质缓存
        MaterialCache.clear()

        # 统计信息
        total_materials = 0
        replaced_materials = 0
        replaced_shaders = 0

        # 遍历所有目标对象
        for obj in target_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material.use_nodes:
                        mat = slot.material
                        total_materials += 1

                        # 检查缓存
                        if MaterialCache.is_processed(mat):
                            result = MaterialCache.get_result(mat)
                        else:
                            result = self.replace_material_shaders(
                                mat, props, target_shader_name, specific_shader_name)
                            MaterialCache.mark_processed(mat, result)

                        if result > 0:
                            replaced_materials += 1
                            replaced_shaders += result

        # 显示结果
        if replaced_shaders == 0:
            self.report(
                {'WARNING'}, f"处理了 {total_materials} 个材质，但没有找到需要替换的着色器")
        else:
            self.report(
                {'INFO'},
                f"替换完成！共处理 {replaced_materials}/{total_materials} 个材质，"
                f"成功替换 {replaced_shaders} 个着色器节点"
            )

        return {'FINISHED'}

    def get_shader_name_from_enum(self, enum_value):
        """从枚举值获取实际的着色器名称"""
        if not enum_value or enum_value == 'NONE':
            return ""

        if enum_value.startswith("NODEGROUP_"):
            try:
                index = int(enum_value.split("_")[1])
                # 使用辅助函数
                node_groups_list = _get_sorted_shader_node_groups()
                if 0 <= index < len(node_groups_list):
                    return node_groups_list[index].name
            except (ValueError, IndexError):
                pass
            return ""
        else:
            if NodeTypeConfig.is_valid_builtin_shader(enum_value):
                return enum_value

        return ""

    def get_target_objects(self, context, target_type):
        """获取目标对象列表"""

        if target_type == 'OBJECTS':
            return context.selected_objects
        elif target_type == 'COLLECTION':
            if context.collection:
                return context.collection.all_objects
            else:
                return []
        return []

    def replace_material_shaders(self, material, props, target_shader_name, specific_shader_name):
        """
        替换材质中的着色器节点，返回替换的节点数量

        智能连接规则：
        1. 优先匹配相同名称的接口
        2. 其次匹配第一个相同类型的接口
        3. 图像纹理特殊处理：优先连接颜色，有Alpha输入时才连接Alpha
        4. 着色器输出优先连接到材质输出的Surface接口
        """

        node_tree = material.node_tree
        nodes = node_tree.nodes
        links = node_tree.links

        # 查找要替换的着色器节点
        shaders_to_replace = []

        # 查找连接到材质输出的节点
        nodes_connected_to_output = set()
        for link in links:
            if link.to_node.type == 'OUTPUT_MATERIAL':
                nodes_connected_to_output.add(link.from_node.name)

        if props.replace_mode == 'ALL' or props.replace_mode == 'MATERIAL':
            # 'ALL' 模式：替换所有着色器
            # 'MATERIAL' 模式：在特定材质中替换所有着色器
            for node in nodes:
                if node.type in NodeTypeConfig.SHADER_NODE_TYPES:
                    shaders_to_replace.append(node.name)

                elif node.type == 'GROUP' and node.node_tree:
                    should_replace = False

                    has_shader_output = any(
                        out.type == 'SHADER' for out in node.outputs)
                    if has_shader_output:
                        should_replace = True

                    if node.name in nodes_connected_to_output:
                        should_replace = True

                    ng_name_lower = node.node_tree.name.lower()
                    if any(kw in ng_name_lower for kw in NodeTypeConfig.SHADER_KEYWORDS):
                        should_replace = True

                    if should_replace:
                        if node.node_tree.name != target_shader_name:
                            shaders_to_replace.append(node.name)
        elif props.replace_mode == 'SPECIFIC' or props.replace_mode == 'MATERIAL_SPECIFIC':
            # 'SPECIFIC' 模式：替换特定着色器
            # 'MATERIAL_SPECIFIC' 模式：在特定材质中替换特定着色器
            for node in nodes:
                if node.type == 'GROUP' and node.node_tree:
                    if node.node_tree.name == specific_shader_name:
                        shaders_to_replace.append(node.name)
                elif node.type == specific_shader_name:
                    shaders_to_replace.append(node.name)

        if not shaders_to_replace:
            return 0

        replaced_count = 0

        # 替换每个着色器节点
        for old_shader_name in shaders_to_replace:
            old_shader = nodes.get(old_shader_name)
            if old_shader is None:
                continue

            # 保存旧节点的连接信息（增强版）
            input_links = {}
            output_links = {}
            old_location = old_shader.location.copy()

            # 收集输入连接（记录更多信息用于智能匹配）
            links_snapshot = list(links)
            for link in links_snapshot:
                try:
                    if link.to_node == old_shader:
                        socket_name = link.to_socket.name
                        socket_index = self.get_socket_index(
                            old_shader.inputs, link.to_socket)
                        socket_type = link.to_socket.type
                        if socket_name not in input_links:
                            input_links[socket_name] = []
                        input_links[socket_name].append({
                            'from_node': link.from_node.name,
                            'from_node_type': link.from_node.type,
                            'from_socket': link.from_socket.name,
                            'from_socket_type': link.from_socket.type,
                            'from_socket_index': self.get_socket_index(link.from_node.outputs, link.from_socket),
                            'to_socket_index': socket_index,
                            'to_socket_type': socket_type
                        })
                except ReferenceError:
                    continue

            # 收集输出连接（增强版）
            for link in links_snapshot:
                try:
                    if link.from_node == old_shader:
                        socket_name = link.from_socket.name
                        socket_index = self.get_socket_index(
                            old_shader.outputs, link.from_socket)
                        socket_type = link.from_socket.type
                        if socket_name not in output_links:
                            output_links[socket_name] = []
                        output_links[socket_name].append({
                            'to_node': link.to_node.name,
                            'to_node_type': link.to_node.type,
                            'to_socket': link.to_socket.name,
                            'to_socket_type': link.to_socket.type,
                            'to_socket_index': self.get_socket_index(link.to_node.inputs, link.to_socket),
                            'from_socket_index': socket_index,
                            'from_socket_type': socket_type
                        })
                except ReferenceError:
                    continue

            # 删除旧节点
            if not safe_remove_node(nodes, old_shader):
                continue

            # 创建新着色器节点
            try:
                node_group = None
                for ng in bpy.data.node_groups:
                    if ng.type == 'SHADER' and ng.name == target_shader_name:
                        node_group = ng
                        break

                if node_group:
                    new_shader = nodes.new(type='ShaderNodeGroup')
                    new_shader.node_tree = node_group
                    new_shader.name = target_shader_name
                    new_shader.label = target_shader_name
                else:
                    node_type = NodeTypeConfig.get_shader_class_name(
                        target_shader_name)
                    new_shader = nodes.new(type=node_type)
                    new_shader.name = target_shader_name
                    new_shader.label = target_shader_name

                new_shader.location = old_location

                # ========== 智能连接输入 ==========
                if props.auto_connect:
                    # AutoConnectionRules.apply_auto_connections(nodes, links, props)
                    connected_inputs = set()

                    for socket_name, connections in input_links.items():
                        for conn in connections:
                            source_node = nodes.get(conn['from_node'])
                            if not source_node:
                                continue

                            # 获取源接口
                            source_socket = None
                            if 0 <= conn['from_socket_index'] < len(source_node.outputs):
                                source_socket = source_node.outputs[conn['from_socket_index']]

                            if not source_socket:
                                for out in source_node.outputs:
                                    if out.name == conn['from_socket']:
                                        source_socket = out
                                        break

                            if not source_socket:
                                continue

                            # 查找最佳匹配的输入接口
                            target_socket = self._find_best_input_socket(
                                new_shader, socket_name, conn['to_socket_type'], connected_inputs
                            )

                            if target_socket:
                                if safe_link(links, source_socket, target_socket):
                                    connected_inputs.add(target_socket)
                # ========== 智能连接输出 ==========
                if props.auto_connect:
                    connected_outputs = set()
                    output_connected_to_material = False  # 标记是否已连接到材质输出

                    # 首先处理已记录的输出连接
                    for socket_name, connections in output_links.items():
                        for conn in connections:
                            target_node = nodes.get(conn['to_node'])
                            if not target_node:
                                continue

                            # 规则4：着色器输出到材质输出节点的特殊处理
                            if target_node.type == 'OUTPUT_MATERIAL' and not output_connected_to_material:
                                # 优先使用第一个 SHADER 类型输出连接到 Surface
                                source_socket = self._find_shader_output(
                                    new_shader)
                                if source_socket:
                                    # 优先连接到 Surface 接口（第一个接口）
                                    surface_input = None
                                    if 'Surface' in target_node.inputs:
                                        surface_input = target_node.inputs['Surface']
                                    elif len(target_node.inputs) > 0:
                                        surface_input = target_node.inputs[0]

                                    if surface_input:
                                        if safe_link(links, source_socket, surface_input):
                                            connected_outputs.add(
                                                source_socket)
                                            output_connected_to_material = True
                                        continue

                            # 获取目标接口
                            target_socket = None
                            if 0 <= conn['to_socket_index'] < len(target_node.inputs):
                                target_socket = target_node.inputs[conn['to_socket_index']]

                            if not target_socket:
                                for inp in target_node.inputs:
                                    if inp.name == conn['to_socket']:
                                        target_socket = inp
                                        break

                            if not target_socket:
                                continue

                            # 标准输出连接逻辑
                            source_socket = self._find_best_output_socket(
                                new_shader, socket_name, conn['from_socket_type'], connected_outputs
                            )

                            if source_socket:
                                if safe_link(links, source_socket, target_socket):
                                    connected_outputs.add(source_socket)
                    # ========== 保底逻辑：确保连接到材质输出节点 ==========
                    # 如果还没有连接到材质输出节点，主动查找并连接
                    if not output_connected_to_material:
                        # 查找材质输出节点
                        output_node = None
                        for node in nodes:
                            if node.type == 'OUTPUT_MATERIAL':
                                output_node = node
                                break

                        if output_node:
                            # 获取新着色器的第一个输出（优先 SHADER 类型）
                            source_socket = self._find_shader_output(
                                new_shader)
                            if source_socket:
                                # 连接到 Surface 接口（第一个接口）
                                surface_input = None
                                if 'Surface' in output_node.inputs:
                                    surface_input = output_node.inputs['Surface']
                                elif len(output_node.inputs) > 0:
                                    surface_input = output_node.inputs[0]

                                if surface_input:
                                    if safe_link(links, source_socket, surface_input):
                                        output_connected_to_material = True
                replaced_count += 1
            except Exception as e:
                print(f"创建着色器节点时出错: {e}")
                import traceback
                traceback.print_exc()
                continue

        return replaced_count
