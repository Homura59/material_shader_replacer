"""
节点类型配置模块 - Blender 4.3 版本
将所有节点类型定义集中在此处，方便后续修改
"""

import bpy
import re
from .cache import NodeGroupCache


class SocketSemantics:
    """接口语义识别 - 识别接口的实际用途"""

    COLOR_KEYWORDS = ['color', 'base color',
                      'diffuse', 'albedo', '颜色', '基础色', '漫反射', '反照率']
    NORMAL_KEYWORDS = ['normal', 'bump', '法线', '凹凸']
    ROUGHNESS_KEYWORDS = ['roughness', 'rough', 'glossy', 'gloss', '粗糙', '光泽']
    METALLIC_KEYWORDS = ['metallic', 'metal', '金属']
    ALPHA_KEYWORDS = ['alpha', 'opacity', 'transparency', '透明', '不透明', 'fac']
    EMISSION_KEYWORDS = ['emission', 'emissive', 'glow', '自发光', '发光']
    SPECULAR_KEYWORDS = ['specular', 'spec', 'reflection', '高光', '反射']
    SUBSURFACE_KEYWORDS = ['subsurface', 'sss', '次表面']
    AO_KEYWORDS = ['ao', 'ambient occlusion', 'occlusion', '环境光遮蔽', '遮蔽']
    DISPLACEMENT_KEYWORDS = ['displacement', 'height', 'disp', '置换', '高度']

    @classmethod
    def get_socket_semantic(cls, socket_name):
        name_lower = socket_name.lower()

        # 优先匹配更具体的关键词
        if 'base color' in name_lower or 'basecolor' in name_lower:
            return 'COLOR'
        if any(kw in name_lower for kw in cls.NORMAL_KEYWORDS):
            return 'NORMAL'
        if any(kw in name_lower for kw in cls.ROUGHNESS_KEYWORDS):
            return 'ROUGHNESS'
        if any(kw in name_lower for kw in cls.METALLIC_KEYWORDS):
            return 'METALLIC'
        if any(kw in name_lower for kw in cls.ALPHA_KEYWORDS):
            return 'ALPHA'
        if any(kw in name_lower for kw in cls.EMISSION_KEYWORDS):
            return 'EMISSION'
        if any(kw in name_lower for kw in cls.SPECULAR_KEYWORDS):
            return 'SPECULAR'
        if any(kw in name_lower for kw in cls.SUBSURFACE_KEYWORDS):
            return 'SUBSURFACE'
        if any(kw in name_lower for kw in cls.AO_KEYWORDS):
            return 'AO'
        if any(kw in name_lower for kw in cls.DISPLACEMENT_KEYWORDS):
            return 'DISPLACEMENT'
        # 最后检查通用 'color'（避免被 'base color' 误匹配）
        if 'color' in name_lower or '颜色' in name_lower:
            return 'COLOR'

        return 'UNKNOWN'

    @classmethod
    def are_semantically_compatible(cls, output_semantic, input_semantic):
        if output_semantic == input_semantic:
            return 100

        compatibility = {
            ('COLOR', 'COLOR'): 100,
            ('COLOR', 'EMISSION'): 80,
            ('NORMAL', 'NORMAL'): 100,
            ('ROUGHNESS', 'ROUGHNESS'): 100,
            ('ROUGHNESS', 'SPECULAR'): 60,
            ('METALLIC', 'METALLIC'): 100,
            ('ALPHA', 'ALPHA'): 100,
            ('AO', 'ROUGHNESS'): 40,
            ('AO', 'SPECULAR'): 40,
        }

        return compatibility.get((output_semantic, input_semantic), 0)


class NodeTypeConfig:
    """Blender 4.3 节点类型配置

    所有节点类型的定义都集中在这个类中，包括：
    - 着色器节点类型（用于识别哪些节点是着色器）
    - 纹理节点类型
    - 节点类型到 Python 类名的映射（用于创建新节点）
    - 节点类型的显示名称（中英文）

    如需适配新版本 Blender，只需修改此类中的定义即可。
    """

    # ----------------------------------------------------------
    # 1. 着色器节点类型集合
    # 用于判断一个节点是否是着色器节点
    # node.type 的值会是这些字符串之一
    # ----------------------------------------------------------
    SHADER_NODE_TYPES = {
        # 表面着色器
        'BSDF_PRINCIPLED',      # 原理化BSDF - 最常用的PBR着色器
        'BSDF_DIFFUSE',         # 漫射BSDF
        'BSDF_GLOSSY',          # 光泽BSDF
        'BSDF_TRANSPARENT',     # 透明BSDF
        'BSDF_GLASS',           # 玻璃BSDF
        'BSDF_TRANSLUCENT',     # 半透明BSDF
        'BSDF_ANISOTROPIC',     # 各向异性BSDF
        'BSDF_VELVET',          # 天绒布BSDF（旧版本，保留兼容）
        'BSDF_REFRACTION',      # 折射BSDF
        'BSDF_TOON',            # 卡通BSDF
        'BSDF_SHEEN',           # 光泽BSDF（Blender 4.0 新增）

        # 毛发着色器
        'BSDF_HAIR',            # 毛发BSDF
        'BSDF_HAIR_PRINCIPLED',  # 原理化毛发BSDF

        # 次表面散射
        'SUBSURFACE_SCATTERING',  # 次表面散射

        # 自发光
        'EMISSION',             # 自发光

        # 体积着色器
        'VOLUME_ABSORPTION',    # 体积吸收
        'VOLUME_SCATTER',       # 体积散射
        'VOLUME_PRINCIPLED',    # 原理化体积

        # 混合着色器
        'MIX_SHADER',           # 混合着色器
        'ADD_SHADER',           # 相加着色器

        # 其他
        'HOLDOUT',              # 阻隔
        'BACKGROUND',           # 背景（用于世界环境）
        'EEVEE_SPECULAR',       # EEVEE高光（仅EEVEE）
    }

    # ----------------------------------------------------------
    # 2. 纹理节点类型集合
    # ----------------------------------------------------------
    TEXTURE_NODE_TYPES = {
        'TEX_IMAGE',            # 图像纹理
        'TEX_ENVIRONMENT',      # 环境纹理
        'TEX_SKY',              # 天空纹理
        'TEX_NOISE',            # 噪波纹理
        'TEX_VORONOI',          # 沃罗诺伊纹理
        'TEX_WAVE',             # 波浪纹理
        'TEX_MAGIC',            # 魔法纹理
        'TEX_CHECKER',          # 棋盘格纹理
        'TEX_BRICK',            # 砖块纹理
        'TEX_GRADIENT',         # 渐变纹理
        'TEX_WHITE_NOISE',      # 白噪波纹理
        'TEX_GABOR',            # Gabor纹理（Blender 4.1 新增）
        'TEX_MUSGRAVE',         # Musgrave纹理（旧版本）
    }
    # ----------------------------------------------------------
    # 3. 节点类型 -> Python类名 映射
    # 用于 nodes.new(type=xxx) 创建新节点
    # 格式: 'NODE_TYPE': 'ShaderNodeXxx'
    # ----------------------------------------------------------
    SHADER_TYPE_TO_CLASS = {
        # 表面着色器
        'BSDF_PRINCIPLED': 'ShaderNodeBsdfPrincipled',
        'BSDF_DIFFUSE': 'ShaderNodeBsdfDiffuse',
        'BSDF_GLOSSY': 'ShaderNodeBsdfGlossy',
        'BSDF_TRANSPARENT': 'ShaderNodeBsdfTransparent',
        'BSDF_GLASS': 'ShaderNodeBsdfGlass',
        'BSDF_TRANSLUCENT': 'ShaderNodeBsdfTranslucent',
        'BSDF_ANISOTROPIC': 'ShaderNodeBsdfAnisotropic',
        'BSDF_REFRACTION': 'ShaderNodeBsdfRefraction',
        'BSDF_TOON': 'ShaderNodeBsdfToon',
        'BSDF_SHEEN': 'ShaderNodeBsdfSheen',

        # 毛发
        'BSDF_HAIR': 'ShaderNodeBsdfHair',
        'BSDF_HAIR_PRINCIPLED': 'ShaderNodeBsdfHairPrincipled',

        # 其他着色器
        'SUBSURFACE_SCATTERING': 'ShaderNodeSubsurfaceScattering',
        'EMISSION': 'ShaderNodeEmission',
        'HOLDOUT': 'ShaderNodeHoldout',
        'BACKGROUND': 'ShaderNodeBackground',
        # 体积
        'VOLUME_ABSORPTION': 'ShaderNodeVolumeAbsorption',
        'VOLUME_SCATTER': 'ShaderNodeVolumeScatter',
        'VOLUME_PRINCIPLED': 'ShaderNodeVolumePrincipled',

        # 混合
        'MIX_SHADER': 'ShaderNodeMixShader',
        'ADD_SHADER': 'ShaderNodeAddShader',
    }

    # ----------------------------------------------------------
    # 4. 内置着色器列表（用于下拉菜单）
    # 格式: (标识符, 显示名称, 描述)
    # ----------------------------------------------------------
    BUILTIN_SHADERS_FOR_MENU = [
        ('BSDF_PRINCIPLED', '原理化BSDF (Principled BSDF)', '基础PBR着色器'),
        ('BSDF_DIFFUSE', '漫射BSDF (Diffuse BSDF)', '漫反射着色器'),
        ('BSDF_GLOSSY', '光泽BSDF (Glossy BSDF)', '光泽着色器'),
        ('BSDF_TRANSPARENT', '透明BSDF (Transparent BSDF)', '透明着色器'),
        ('BSDF_GLASS', '玻璃BSDF (Glass BSDF)', '玻璃着色器'),
        ('BSDF_TRANSLUCENT', '半透明BSDF (Translucent BSDF)', '半透明着色器'),
        ('BSDF_REFRACTION', '折射BSDF (Refraction BSDF)', '折射着色器'),
        ('BSDF_TOON', '卡通BSDF (Toon BSDF)', '卡通着色器'),
        ('BSDF_SHEEN', '光泽BSDF (Sheen BSDF)', '光泽着色器'),
        ('EMISSION', '自发光 (Emission)', '自发光着色器'),
        ('SUBSURFACE_SCATTERING', '次表面散射 (Subsurface Scattering)', '次表面散射'),
        ('VOLUME_ABSORPTION', '体积吸收 (Volume Absorption)', '体积吸收'),
        ('VOLUME_SCATTER', '体积散射 (Volume Scatter)', '体积散射'),
        ('VOLUME_PRINCIPLED', '原理化体积 (Principled Volume)', '原理化体积着色器'),
        ('MIX_SHADER', '混合着色器 (Mix Shader)', '混合两个着色器'),
        ('ADD_SHADER', '相加着色器 (Add Shader)', '相加两个着色器'),
    ]

    # ----------------------------------------------------------
    # 5. 用于验证的内置着色器类型列表
    # ----------------------------------------------------------
    BUILTIN_SHADER_TYPES = [
        'BSDF_PRINCIPLED', 'BSDF_DIFFUSE', 'BSDF_GLOSSY', 'BSDF_TRANSPARENT',
        'BSDF_GLASS', 'EMISSION', 'BSDF_ANISOTROPIC', 'BSDF_HAIR',
        'SUBSURFACE_SCATTERING', 'VOLUME_ABSORPTION', 'VOLUME_SCATTER',
        'VOLUME_PRINCIPLED', 'MIX_SHADER', 'ADD_SHADER', 'BSDF_SHEEN',
        'BSDF_TRANSLUCENT', 'BSDF_REFRACTION', 'BSDF_TOON', 'HOLDOUT',
        'BSDF_HAIR_PRINCIPLED', 'BACKGROUND',
    ]

    # ----------------------------------------------------------
    # 6. 着色器关键词（用于识别自定义节点组是否是着色器）
    # ----------------------------------------------------------
    SHADER_KEYWORDS = ['shader', 'bsdf', 'material', '着色', '材质', 'surface']

    @classmethod
    def identify_custom_shader_role(cls, node):
        """识别自定义节点组的角色"""
        if node.type != 'GROUP' or not node.node_tree:
            return None

        name = (node.label if node.label else node.node_tree.name).lower()

        # 识别常见的第三方着色器类型
        if any(kw in name for kw in ['pbr', 'principled', '原理', '标准']):
            return 'PBR_SHADER'
        if any(kw in name for kw in ['glass', 'transparent', '玻璃', '透明']):
            return 'GLASS_SHADER'
        if any(kw in name for kw in ['toon', 'cartoon', 'cel', '卡通']):
            return 'TOON_SHADER'
        if any(kw in name for kw in ['hair', 'fur', '毛发', '毛皮']):
            return 'HAIR_SHADER'
        if any(kw in name for kw in ['skin', 'sss', '皮肤', '次表面']):
            return 'SKIN_SHADER'

        return 'CUSTOM_SHADER'
    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    @classmethod
    def is_shader_node(cls, node):
        """
        判断节点是否是着色器节点

        参数:
            node: bpy.types.Node 对象
        返回:
            bool: 是否是着色器节点
        """
        # 检查内置着色器类型
        if node.type in cls.SHADER_NODE_TYPES:
            return True

        # 检查节点组
        if node.type == 'GROUP' and node.node_tree:
            # 检查是否有 SHADER 类型输出
            if any(out.type == 'SHADER' for out in node.outputs):
                return True

            # 检查名称是否包含着色器关键词
            ng_name_lower = node.node_tree.name.lower()
            if any(kw in ng_name_lower for kw in cls.SHADER_KEYWORDS):
                return True

        return False

    @classmethod
    def is_texture_node(cls, node):
        """判断节点是否是纹理节点"""
        return node.type in cls.TEXTURE_NODE_TYPES

    @classmethod
    def get_shader_class_name(cls, shader_type):
        """
        获取着色器类型对应的 Python 类名

        参数:
            shader_type: 着色器类型字符串，如 'BSDF_PRINCIPLED'
        返回:
            str: Python 类名，如 'ShaderNodeBsdfPrincipled'
        """
        return cls.SHADER_TYPE_TO_CLASS.get(shader_type, 'ShaderNodeBsdfPrincipled')

    @classmethod
    def is_valid_builtin_shader(cls, shader_type):
        """检查是否是有效的内置着色器类型"""
        return shader_type in cls.BUILTIN_SHADER_TYPES


# ============================================================
# 节点类型映射表（英文类型 -> 中文显示名称）
# 用于UI显示
# ============================================================
NODE_TYPE_NAMES = {
    # 着色器节点
    'BSDF_PRINCIPLED': '原理化BSDF',
    'BSDF_DIFFUSE': '漫射BSDF',
    'BSDF_GLOSSY': '光泽BSDF',
    'BSDF_TRANSPARENT': '透明BSDF',
    'BSDF_GLASS': '玻璃BSDF',
    'BSDF_TRANSLUCENT': '半透明BSDF',
    'BSDF_ANISOTROPIC': '各向异性BSDF',
    'BSDF_VELVET': '天鹅绒BSDF',
    'BSDF_REFRACTION': '折射BSDF',
    'BSDF_TOON': '卡通BSDF',
    'BSDF_SHEEN': '光泽BSDF',
    'BSDF_HAIR': '毛发BSDF',
    'BSDF_HAIR_PRINCIPLED': '原理化毛发BSDF',
    'SUBSURFACE_SCATTERING': '次表面散射',
    'EMISSION': '自发光',
    'VOLUME_ABSORPTION': '体积吸收',
    'VOLUME_SCATTER': '体积散射',
    'VOLUME_PRINCIPLED': '原理化体积',
    'EEVEE_SPECULAR': 'Eevee高光',
    'ADD_SHADER': '混合着色器(相加)',
    'MIX_SHADER': '混合着色器',
    'HOLDOUT': '阻隔',
    'BACKGROUND': '背景',
    # 纹理节点
    'TEX_IMAGE': '图像纹理',
    'TEX_ENVIRONMENT': '环境纹理',
    'TEX_SKY': '天空纹理',
    'TEX_NOISE': '噪波纹理',
    'TEX_VORONOI': '沃罗诺伊纹理',
    'TEX_MUSGRAVE': 'Musgrave纹理',
    'TEX_WAVE': '波浪纹理',
    'TEX_MAGIC': '魔法纹理',
    'TEX_CHECKER': '棋盘格纹理',
    'TEX_BRICK': '砖块纹理',
    'TEX_GRADIENT': '渐变纹理',
    'TEX_POINTDENSITY': '点密度',
    'TEX_IES': 'IES纹理',
    'TEX_WHITE_NOISE': '白噪波纹理',
    'TEX_GABOR': 'Gabor纹理',

    # 颜色节点
    'MIX': '混合',
    'MIX_RGB': '混合RGB',
    'CURVE_RGB': 'RGB曲线',
    'CURVE_VEC': '矢量曲线',
    'INVERT': '反转',
    'HUE_SAT': '色相/饱和度',
    'GAMMA': '伽马',
    'BRIGHTCONTRAST': '亮度/对比度',
    'LIGHT_FALLOFF': '灯光衰减',

    # 矢量节点
    'BUMP': '凹凸',
    'NORMAL': '法向',
    'NORMAL_MAP': '法向贴图',
    'DISPLACEMENT': '置换',
    'VECTOR_DISPLACEMENT': '矢量置换',
    'MAPPING': '映射',
    'VECT_TRANSFORM': '矢量变换',
    'VECTOR_ROTATE': '矢量旋转',
    'VECTOR_MATH': '矢量运算',

    # 转换节点
    'VALTORGB': '颜色渐变',
    'RGBTOBW': 'RGB转BW',
    'SEPARATE_COLOR': '分离颜色',
    'COMBINE_COLOR': '合并颜色',
    'SEPRGB': '分离RGB',
    'COMBRGB': '合并RGB',
    'SEPXYZ': '分离XYZ',
    'COMBXYZ': '合并XYZ',
    'SEPHSV': '分离HSV',
    'COMBHSV': '合并HSV',
    'WAVELENGTH': '波长',
    'BLACKBODY': '黑体',
    # 输入节点
    'TEX_COORD': '纹理坐标',
    'UVMAP': 'UV贴图',
    'GEOMETRY': '几何数据',
    'OBJECT_INFO': '物体信息',
    'PARTICLE_INFO': '粒子信息',
    'HAIR_INFO': '毛发信息',
    'POINT_INFO': '点信息',
    'VOLUME_INFO': '体积信息',
    'ATTRIBUTE': '属性',
    'TANGENT': '切向',
    'LAYER_WEIGHT': '层权重',
    'FRESNEL': '菲涅尔',
    'AMBIENT_OCCLUSION': '环境光遮蔽',
    'BEVEL': '倒角',
    'WIREFRAME': '线框',
    'VALUE': '数值',
    'RGB': 'RGB',
    'VERTEX_COLOR': '顶点颜色',
    'CAMERA': '相机数据',
    'LIGHT_PATH': '光程',

    # 输出节点
    'OUTPUT_MATERIAL': '材质输出',
    'OUTPUT_WORLD': '世界输出',
    'OUTPUT_LIGHT': '灯光输出',
    'OUTPUT_AOV': 'AOV输出',

    # 数学节点
    'MATH': '数学运算',
    'CLAMP': '钳制',
    'MAP_RANGE': '映射范围',

    # 其他节点
    'GROUP': '节点组',
    'GROUP_INPUT': '组输入',
    'GROUP_OUTPUT': '组输出',
    'FRAME': '框架',
    'REROUTE': '重定向',
    'SCRIPT': 'OSL脚本',
}

# 反向映射（中文名称 -> 英文类型）
NODE_TYPE_NAMES_REVERSE = {v: k for k, v in NODE_TYPE_NAMES.items()}


def get_node_type_items(self, context):
    """获取节点类型列表用于下拉菜单"""
    items = [('', '-- Select Node Type --', '')]

    # 按类别分组
    categories = {
        'Shader': ['BSDF_PRINCIPLED', 'BSDF_DIFFUSE', 'BSDF_GLOSSY', 'BSDF_TRANSPARENT',
                   'BSDF_GLASS', 'EMISSION', 'SUBSURFACE_SCATTERING', 'MIX_SHADER', 'ADD_SHADER'],
        'Texture': ['TEX_IMAGE', 'TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE',
                    'TEX_CHECKER', 'TEX_GRADIENT', 'TEX_BRICK', 'TEX_MAGIC'],
        'Color': ['MIX', 'MIX_RGB', 'CURVE_RGB', 'INVERT', 'HUE_SAT', 'GAMMA', 'BRIGHTCONTRAST'],
        'Vector': ['BUMP', 'NORMAL', 'NORMAL_MAP', 'MAPPING', 'DISPLACEMENT', 'VECTOR_MATH'],
        'Converter': ['VALTORGB', 'RGBTOBW', 'SEPARATE_COLOR', 'COMBINE_COLOR', 'SEPXYZ', 'COMBXYZ'],
        'Input': ['TEX_COORD', 'UVMAP', 'GEOMETRY', 'OBJECT_INFO', 'ATTRIBUTE', 'FRESNEL',
                  'LAYER_WEIGHT', 'VALUE', 'RGB', 'VERTEX_COLOR'],
        'Output': ['OUTPUT_MATERIAL'],
        'Math': ['MATH', 'CLAMP', 'MAP_RANGE'],
        'Other': ['GROUP', 'REROUTE', 'FRAME'],
    }

    # 节点类型英文显示名称
    node_display_names = {
        'BSDF_PRINCIPLED': 'Principled BSDF',
        'BSDF_DIFFUSE': 'Diffuse BSDF',
        'BSDF_GLOSSY': 'Glossy BSDF',
        'BSDF_TRANSPARENT': 'Transparent BSDF',
        'BSDF_GLASS': 'Glass BSDF',
        'EMISSION': 'Emission',
        'SUBSURFACE_SCATTERING': 'Subsurface Scattering',
        'MIX_SHADER': 'Mix Shader',
        'ADD_SHADER': 'Add Shader',
        'TEX_IMAGE': 'Image Texture',
        'TEX_NOISE': 'Noise Texture',
        'TEX_VORONOI': 'Voronoi Texture',
        'TEX_WAVE': 'Wave Texture',
        'TEX_CHECKER': 'Checker Texture',
        'TEX_GRADIENT': 'Gradient Texture',
        'TEX_BRICK': 'Brick Texture',
        'TEX_MAGIC': 'Magic Texture',
        'MIX': 'Mix',
        'MIX_RGB': 'Mix RGB',
        'CURVE_RGB': 'RGB Curves',
        'INVERT': 'Invert',
        'HUE_SAT': 'Hue/Saturation',
        'GAMMA': 'Gamma',
        'BRIGHTCONTRAST': 'Bright/Contrast',
        'BUMP': 'Bump',
        'NORMAL': 'Normal',
        'NORMAL_MAP': 'Normal Map',
        'MAPPING': 'Mapping',
        'DISPLACEMENT': 'Displacement',
        'VECTOR_MATH': 'Vector Math',
        'VALTORGB': 'Color Ramp',
        'RGBTOBW': 'RGB to BW',
        'SEPARATE_COLOR': 'Separate Color',
        'COMBINE_COLOR': 'Combine Color',
        'SEPXYZ': 'Separate XYZ',
        'COMBXYZ': 'Combine XYZ',
        'TEX_COORD': 'Texture Coordinate',
        'UVMAP': 'UV Map',
        'GEOMETRY': 'Geometry',
        'OBJECT_INFO': 'Object Info',
        'ATTRIBUTE': 'Attribute',
        'FRESNEL': 'Fresnel',
        'LAYER_WEIGHT': 'Layer Weight',
        'VALUE': 'Value',
        'RGB': 'RGB',
        'VERTEX_COLOR': 'Vertex Color',
        'OUTPUT_MATERIAL': 'Material Output',
        'MATH': 'Math',
        'CLAMP': 'Clamp',
        'MAP_RANGE': 'Map Range',
        'GROUP': 'Node Group',
        'REROUTE': 'Reroute',
        'FRAME': 'Frame',
    }

    for category, types in categories.items():
        # 添加分隔符
        items.append((f'__{category}__', f'-- {category} --', ''))
        for node_type in types:
            display_name = node_display_names.get(node_type, node_type)
            items.append((node_type, display_name, f'Node type: {node_type}'))

    return items


def _get_sorted_shader_node_groups():
    """获取排序后的着色器节点组列表（带缓存）"""
    return NodeGroupCache.get_sorted_shader_node_groups()


def get_available_shaders(self, context):
    """获取可用的着色器列表"""

    def has_chinese(text):
        """检测字符串是否包含中文或其他非 ASCII 字符"""
        try:
            text.encode('ascii')
            return False
        except UnicodeEncodeError:
            return True

    shaders = []

    # 添加节点组着色器(排序以确保顺序一致)
    shader_node_groups = _get_sorted_shader_node_groups()

    for i, ng in enumerate(shader_node_groups):
        identifier = f"NODEGROUP_{i}"
        # Blender EnumProperty 的中文显示存在兼容性问题
        # 如枟包含非 ASCII 字符,在 name 中使用简化标识符
        # UI 层会额外显示完整的中文名称
        if has_chinese(ng.name):
            display_name = f"NodeGroup_{i}"
            description = "Custom shader node group"
        else:
            display_name = ng.name
            description = ng.name

        shaders.append((identifier, display_name, description))

    # 添加内置着色器
    shaders.extend(NodeTypeConfig.BUILTIN_SHADERS_FOR_MENU)

    if not shaders:
        shaders.append(('NONE', '-- No Shaders Available --', ''))

    return shaders


def get_available_shaders_for_specific(self, context):
    """获取可用的着色器列表（用于替换特定着色器）"""
    return get_available_shaders(self, context)


def get_node_label_or_name(node):
    """获取节点的标签名称，如果没有标签则返回节点名称"""
    if node.label and node.label.strip():
        return node.label.strip()
    return node.name


def match_node_by_label_or_name(node, target_name):
    """通过标签或名称匹配节点"""
    if not target_name:
        return False
    target_name_lower = target_name.lower().strip()
    # 检查标签（精确匹配）
    if node.label and node.label.lower().strip() == target_name_lower:
        return True
    # 检查名称（精确匹配）
    if node.name.lower().strip() == target_name_lower:
        return True
    # 部分匹配（标签或名称包含目标字符串）
    if node.label and target_name_lower in node.label.lower():
        return True
    if target_name_lower in node.name.lower():
        return True
    return False


def match_node_by_type(node, target_type):
    """通过节点类型匹配节点"""
    if not target_type:
        return False
    # 直接比较节点类型
    if node.type == target_type:
        return True

    # 检查是否是节点组
    if target_type == 'GROUP' and node.type == 'GROUP':
        return True

    # 检查中文名称映射
    if target_type in NODE_TYPE_NAMES_REVERSE:
        english_type = NODE_TYPE_NAMES_REVERSE[target_type]
        if node.type == english_type:
            return True

    return False


class AutoConnectionRules:
    """自动连接规则封装类 - 统一管理自动连接逻辑"""

    @staticmethod
    def apply_auto_connections(nodes, links, props):
        """
        应用自动连接规则

        参数:
            nodes: 节点树的 nodes 集合
            links: 节点树的 links 集合
            props: ShaderReplacerProperties 实例
        返回:
            连接数量
        """
        if not props.auto_connect:
            return 0

        connect_count = 0

        # 查找材质输出节点
        output_node = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output_node = node
                break

        # 查找所有着色器节点
        shader_nodes = []
        for node in nodes:
            if node.type in NodeTypeConfig.SHADER_NODE_TYPES:
                shader_nodes.append(node)
            elif node.type == 'GROUP' and hasattr(node, 'node_tree') and node.node_tree:
                if NodeTypeConfig.is_shader_node(node):
                    shader_nodes.append(node)

        # 查找所有纹理节点
        texture_nodes = []
        for node in nodes:
            if NodeTypeConfig.is_texture_node(node):
                texture_nodes.append(node)

        # 着色器到材质输出的连接
        if output_node and shader_nodes:
            for shader_node in shader_nodes:
                shader_output = None
                for output in shader_node.outputs:
                    if output.type == 'SHADER':
                        shader_output = output
                        break
                if not shader_output and len(shader_node.outputs) > 0:
                    shader_output = shader_node.outputs[0]

                if shader_output:
                    surface_input = None
                    surface_names = ['Surface', 'surface', '表面', '曲面', '表（曲）面']
                    for name in surface_names:
                        if name in output_node.inputs:
                            surface_input = output_node.inputs[name]
                            break
                    if not surface_input and len(output_node.inputs) > 0:
                        surface_input = output_node.inputs[0]

                    if surface_input:
                        try:
                            links.new(shader_output, surface_input)
                            connect_count += 1
                        except:
                            pass
                    break

        # 纹理到着色器的连接
        if shader_nodes and texture_nodes:
            for shader_node in shader_nodes:
                connected_inputs = set()

                # 检查着色器是否有 Alpha 输入
                has_alpha_input = False
                for inp in shader_node.inputs:
                    if SocketSemantics.get_socket_semantic(inp.name) == 'ALPHA':
                        has_alpha_input = True
                        break

                for tex_node in texture_nodes:
                    if not tex_node.outputs:
                        continue

                    # 图像纹理特殊处理
                    if tex_node.type == 'TEX_IMAGE':
                        # 连接 Color 输出
                        if len(tex_node.outputs) > 0:
                            color_output = tex_node.outputs[0]

                            # 查找 Base Color 接口
                            target_input = None
                            color_keywords = [
                                'base color', 'basecolor', 'color', '颜色', 'diffuse', '漫反射', 'albedo', '反照率', '基础色']

                            for keyword in color_keywords:
                                matching_inputs = []
                                for idx, inp in enumerate(shader_node.inputs):
                                    if inp in connected_inputs:
                                        continue
                                    if keyword in inp.name.lower():
                                        matching_inputs.append((idx, inp))

                                if matching_inputs:
                                    matching_inputs.sort(key=lambda x: x[0])
                                    target_input = matching_inputs[0][1]
                                    break

                            if target_input:
                                try:
                                    links.new(color_output, target_input)
                                    connected_inputs.add(target_input)
                                    connect_count += 1
                                except:
                                    pass

                        # 连接 Alpha 输出（仅当着色器有 Alpha 输入时）
                        if has_alpha_input and len(tex_node.outputs) > 1:
                            alpha_output = tex_node.outputs[1]

                            # 查找 Alpha 接口
                            alpha_input = None
                            alpha_keywords = [
                                'alpha', 'opacity', 'transparency', '透明']

                            matching_inputs = []
                            for idx, inp in enumerate(shader_node.inputs):
                                if inp in connected_inputs:
                                    continue
                                inp_name_lower = inp.name.lower()
                                if any(kw in inp_name_lower for kw in alpha_keywords):
                                    matching_inputs.append((idx, inp))

                            if matching_inputs:
                                matching_inputs.sort(key=lambda x: x[0])
                                alpha_input = matching_inputs[0][1]

                            if alpha_input:
                                try:
                                    links.new(alpha_output, alpha_input)
                                    connected_inputs.add(alpha_input)
                                    connect_count += 1
                                except:
                                    pass

                    else:
                        # 其他纹理节点：使用语义匹配
                        tex_name = (
                            tex_node.label if tex_node.label else tex_node.name).lower()

                        # 纹理语义识别
                        tex_semantic = 'COLOR'
                        if any(kw in tex_name for kw in ['normal', 'norm', '法线']):
                            tex_semantic = 'NORMAL'
                        elif any(kw in tex_name for kw in ['rough', 'gloss', '粗糙', '光泽']):
                            tex_semantic = 'ROUGHNESS'
                        elif any(kw in tex_name for kw in ['metal', '金属']):
                            tex_semantic = 'METALLIC'
                        elif any(kw in tex_name for kw in ['ao', 'ambient', '遮蔽']):
                            tex_semantic = 'AO'
                        elif any(kw in tex_name for kw in ['emit', 'glow', '发光']):
                            tex_semantic = 'EMISSION'
                        elif any(kw in tex_name for kw in ['alpha', 'opacity', '透明']):
                            tex_semantic = 'ALPHA'

                        # 找到颜色输出（RGBA 或 VECTOR 类型，且名称包含 color）
                        color_output = None
                        for out in tex_node.outputs:
                            if out.type in ['RGBA', 'VECTOR'] and 'color' in out.name.lower():
                                color_output = out
                                break

                        # 如果没找到明确的颜色输出，使用第一个 RGBA 或 VECTOR 输出
                        if not color_output:
                            for out in tex_node.outputs:
                                if out.type in ['RGBA', 'VECTOR']:
                                    color_output = out
                                    break

                        if not color_output:
                            continue

                        # 找到最佳输入接口
                        best_input = None
                        best_score = 0

                        for inp in shader_node.inputs:
                            if inp in connected_inputs:
                                continue

                            input_semantic = SocketSemantics.get_socket_semantic(
                                inp.name)
                            score = SocketSemantics.are_semantically_compatible(
                                tex_semantic, input_semantic)

                            if score > best_score:
                                best_score = score
                                best_input = inp

                        # 连接颜色输出
                        if best_input and best_score >= 50:
                            try:
                                links.new(color_output, best_input)
                                connected_inputs.add(best_input)
                                connect_count += 1
                            except:
                                pass
        # return connect_count

        # ========== 其他类型节点到着色器的连接 ==========
        # 查找所有非纹理、非着色器的节点
        other_nodes = []
        for node in nodes:
            if (node.type not in NodeTypeConfig.TEXTURE_NODE_TYPES and
                node.type not in NodeTypeConfig.SHADER_NODE_TYPES and
                node.type != 'OUTPUT_MATERIAL' and
                    node.type != 'GROUP'):
                other_nodes.append(node)

        if shader_nodes and other_nodes:
            for shader_node in shader_nodes:
                connected_inputs = set()  # 新的 connected_inputs，不与纹理共享

                for other_node in other_nodes:
                    if not other_node.outputs:
                        continue

                    node_name = (
                        other_node.label if other_node.label else other_node.name).lower()

                    for out in other_node.outputs:
                        if out.type not in ['RGBA', 'VECTOR', 'VALUE']:
                            continue

                        output_semantic = SocketSemantics.get_socket_semantic(
                            out.name)
                        if output_semantic == 'UNKNOWN':
                            if any(kw in node_name for kw in ['normal', 'norm', '法线']):
                                output_semantic = 'NORMAL'
                            elif any(kw in node_name for kw in ['rough', '粗糙']):
                                output_semantic = 'ROUGHNESS'
                            elif any(kw in node_name for kw in ['metal', '金属']):
                                output_semantic = 'METALLIC'
                            elif any(kw in node_name for kw in ['ao', '遮蔽']):
                                output_semantic = 'AO'
                            elif any(kw in node_name for kw in ['bump', '凹凸']):
                                output_semantic = 'NORMAL'
                            elif any(kw in node_name for kw in ['alpha', '透明']):
                                output_semantic = 'ALPHA'
                            else:
                                output_semantic = 'COLOR'

                        best_input = None
                        best_score = 0

                        for inp in shader_node.inputs:
                            if inp in connected_inputs:
                                continue

                            input_semantic = SocketSemantics.get_socket_semantic(
                                inp.name)
                            score = SocketSemantics.are_semantically_compatible(
                                output_semantic, input_semantic)

                            if score > best_score:
                                best_score = score
                                best_input = inp

                        if best_input and best_score >= 40:
                            try:
                                links.new(out, best_input)
                                connected_inputs.add(best_input)
                                connect_count += 1
                                break
                            except:
                                pass
        return connect_count


def get_all_node_types(self, context):
    """获取所有节点类型用于下拉菜单"""
    items = [('', '-- Select Node Type --', '')]

    # 按类别分组
    categories = {
        'Shader': [
            'BSDF_PRINCIPLED', 'BSDF_DIFFUSE', 'BSDF_GLOSSY', 'BSDF_TRANSPARENT',
            'BSDF_GLASS', 'EMISSION', 'SUBSURFACE_SCATTERING', 'MIX_SHADER', 'ADD_SHADER',
            'BSDF_TRANSLUCENT', 'BSDF_REFRACTION', 'BSDF_TOON', 'BSDF_SHEEN', 'BSDF_ANISOTROPIC',
            'BSDF_HAIR', 'BSDF_HAIR_PRINCIPLED', 'VOLUME_ABSORPTION', 'VOLUME_SCATTER',
            'VOLUME_PRINCIPLED', 'HOLDOUT', 'BACKGROUND', 'EEVEE_SPECULAR'
        ],
        'Texture': [
            'TEX_IMAGE', 'TEX_ENVIRONMENT', 'TEX_SKY', 'TEX_NOISE', 'TEX_VORONOI',
            'TEX_WAVE', 'TEX_MAGIC', 'TEX_CHECKER', 'TEX_BRICK', 'TEX_GRADIENT',
            'TEX_WHITE_NOISE', 'TEX_GABOR', 'TEX_MUSGRAVE', 'TEX_POINTDENSITY', 'TEX_IES'
        ],
        'Color': [
            'MIX', 'MIX_RGB', 'CURVE_RGB', 'CURVE_VEC', 'INVERT', 'HUE_SAT',
            'GAMMA', 'BRIGHTCONTRAST', 'LIGHT_FALLOFF', 'VALTORGB', 'RGBTOBW'
        ],
        'Vector': [
            'BUMP', 'NORMAL', 'NORMAL_MAP', 'DISPLACEMENT', 'VECTOR_DISPLACEMENT',
            'MAPPING', 'VECT_TRANSFORM', 'VECTOR_ROTATE', 'VECTOR_MATH'
        ],
        'Converter': [
            'SEPARATE_COLOR', 'COMBINE_COLOR', 'SEPRGB', 'COMBRGB', 'SEPXYZ',
            'COMBXYZ', 'SEPHSV', 'COMBHSV', 'WAVELENGTH', 'BLACKBODY'
        ],
        'Input': [
            'TEX_COORD', 'UVMAP', 'GEOMETRY', 'OBJECT_INFO', 'PARTICLE_INFO',
            'HAIR_INFO', 'POINT_INFO', 'VOLUME_INFO', 'ATTRIBUTE', 'TANGENT',
            'LAYER_WEIGHT', 'FRESNEL', 'AMBIENT_OCCLUSION', 'BEVEL', 'WIREFRAME',
            'VALUE', 'RGB', 'VERTEX_COLOR', 'CAMERA', 'LIGHT_PATH'
        ],
        'Output': [
            'OUTPUT_MATERIAL', 'OUTPUT_WORLD', 'OUTPUT_LIGHT', 'OUTPUT_AOV'
        ],
        'Math': [
            'MATH', 'CLAMP', 'MAP_RANGE'
        ],
        'Layout': [
            'FRAME', 'REROUTE', 'GROUP', 'GROUP_INPUT', 'GROUP_OUTPUT'
        ],
        'Script': [
            'SCRIPT'
        ]
    }

    for category, types in categories.items():
        # 添加分隔符
        items.append((f'__{category}__', f'-- {category} --', ''))
        for node_type in types:
            display_name = NODE_TYPE_NAMES.get(node_type, node_type)
            items.append((node_type, display_name, f'Node type: {node_type}'))

    return items


def register():
    """注册节点配置模块"""
    pass


def unregister():
    """注销节点配置模块"""
    pass
