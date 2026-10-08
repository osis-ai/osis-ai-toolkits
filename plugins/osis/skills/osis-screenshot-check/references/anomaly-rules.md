# OSIS 视觉异常映射规则

`schema_version: 1.0`

只在直接视觉判断为 `incorrect` 后读取与问题最相关的最多两节规则。将字段作为当前项目代码的定位提示，不得直接指定代码行、对象编号或修改值。`auto_fix_allowed = gated` 表示仅在 `repair-policy.md` 的项目状态、唯一性、备份和一次修复门禁全部通过时，才自动应用白名单修复。

## `section_transition_step`

- `anomaly_type`: section_transition_step
- `engineering_fault`: 设计要求连续时，相邻截面可见几何不连续
- `visual_signals`: 非设计位置出现竖向台阶；内部截面轮廓在共享节点跳变
- `candidate_causes`: 相邻单元 `sec1/sec2` 不连续；渐变段被写成等截面；截面或偏移定义不一致
- `candidate_targets`: 单元截面端指派 `sec1/sec2`；截面与偏移定义 `geometry/SectionOffset`
- `required_facts`: 异常共享节点；左右相邻单元；可见截面签名；`transition_presence`；`transition_behavior`；`implementation_fault`
- `required_reference`: 当前项目画像中的允许突变位置和预期分区；含糊时按需读取一个相关标准案例
- `reject_conditions`: 设计明确允许同类型突变；截面几何等价；渲染伪影未排除
- `required_verification`: 先分别确认过渡是否存在、应有行为和实现故障；可见台阶只能证明过渡行为异常，不能证明过渡不应存在；设计确认存在时保留端部加厚和连续过渡，不得直接统一为标准截面；再比较当前 J 端与下一单元 I 端，并排除节点高程和 `SectionOffset`
- `auto_fix_allowed`: `gated`

## `section_assignment_outlier`

- `anomaly_type`: section_assignment_outlier
- `engineering_fault`: 均匀区单单元截面指派离群
- `visual_signals`: 局部矩形凹阶或凸阶；短平台被左右节点竖线界定
- `candidate_causes`: 单元 `sec1/sec2` 误指派；分段索引错一位；局部截面替换错误
- `candidate_targets`: 单元截面端指派 `sec1/sec2`；单元生成范围 `element_range/section_index`
- `required_facts`: 左邻—当前—右邻三单元；共享节点；可见截面签名
- `required_reference`: `expected_section_zones`；`allowed_discontinuity_positions`
- `reject_conditions`: 区段非均匀；合法局部构造；渲染伪影未排除
- `required_verification`: 证明当前单元是唯一离群；排除截面几何偏移和节点高程
- `auto_fix_allowed`: `gated`

## `member_axis_kink`

- `anomaly_type`: member_axis_kink
- `engineering_fault`: 非设计构件轴线折线或错位
- `visual_signals`: 构件轴线在节点处折断；上下轮廓整体错位
- `candidate_causes`: 节点坐标错误；单元 I/J 节点连接错误；局部坐标或截面偏移错误
- `candidate_targets`: 节点生成 `x/y/z`；单元连接 `i_node/j_node`；局部坐标与偏移 `local_axis/SectionOffset`
- `required_facts`: 折点节点；相邻单元连接；节点坐标
- `required_reference`: 允许设计折点；设计轴线
- `reject_conditions`: 设计明确允许折点；截面偏移可完整解释
- `required_verification`: 比较节点坐标与连接顺序；排除局部坐标和偏移
- `auto_fix_allowed`: `gated`

## `section_geometry_anomaly`

- `anomaly_type`: section_geometry_anomaly
- `engineering_fault`: 截面轮廓或梁高定义异常
- `visual_signals`: 局部梁高异常；腹板或翼缘轮廓异常
- `candidate_causes`: 截面尺寸参数错误；截面类型或轮廓错误；偏移或节点标高错误
- `candidate_targets`: 截面定义 `section_type/height/width/web/flange/chamfer`；截面偏移与节点 `SectionOffset/z`
- `required_facts`: 异常截面号；可见几何签名；使用该截面的单元
- `required_reference`: `expected_section_zones`；模板截面结构语义
- `reject_conditions`: 单元截面指派更能解释；设计明确允许该截面变化
- `required_verification`: 比较截面几何与指派；排除偏移和节点高程
- `auto_fix_allowed`: `gated`

## `reversed_section_transition`

- `anomaly_type`: reversed_section_transition
- `engineering_fault`: 变截面可见截面签名的趋势或分区方向与设计相反
- `visual_signals`: 端—跨中—端截面签名趋势与设计相反；腹板—下翼缘交界线或下翼缘厚度反转、回摆或突然复位；总梁高恒定但内部轮廓趋势错误；设计要求镜像而两侧趋势不对应
- `candidate_causes`: 起终截面顺序颠倒；单元拓扑顺序反向；插值比例定义错误；分区边界映射错误；当前 OSIS 载入状态与项目源文件不是同一版本
- `candidate_targets`: 单元截面端指派 `sec1/sec2/element_order`；单元生成分区 `element_range/zone_boundary/interpolation_ratio`；截面签名参数：下翼缘厚度 `bottom_flange_thickness`、腹板—下翼缘交界线 `web_bottom_flange_junction`、内部轮廓 `internal_contour`
- `required_facts`: 有来源的预期设计/项目源/实时模型截面序列；端—跨中—端可见轮廓趋势；腹板—下翼缘交界线和下翼缘厚度趋势；过渡区节点坐标；`source_state_consistency`
- `required_reference`: 设计截面分区及其签名趋势；`expected_section_zones`；左右对称或明确非对称要求
- `reject_conditions`: 设计截面分区或签名趋势未确认；设计本身明确允许该非单调趋势；必需局部图不能覆盖完整趋势
- `required_verification`: 确认设计截面分区及起终截面；从四张本轮图片识别反转、回摆或突然复位；按拓扑排列全部 I/J 端截面签名，标明项目源/实时模型来源并与设计序列逐项比较；检查单元 I→J 趋势、J→下一 I 连续性、插值比例和分区边界；若项目源正确而实时模型或视觉观察冲突，不得修改项目源或重建实时模型，设置 `repair_status = unsafe_to_apply` 并停止自动修复
- `auto_fix_allowed`: `gated`

## `member_missing`

- `anomaly_type`: member_missing
- `engineering_fault`: 设计范围内构件或单元缺失
- `visual_signals`: 应连续的构件区间出现空白；构件在非设计位置提前终止
- `candidate_causes`: 循环边界错误；构件筛选条件错误；单元创建范围遗漏；分组过滤错误
- `candidate_targets`: 单元生成范围 `loop_boundary/element_range`；构件筛选 `filter_condition/member_group`
- `required_facts`: 缺失区坐标范围；邻接节点；已创建单元序列
- `required_reference`: 构件拓扑；设计构件范围
- `reject_conditions`: 设计开口或预留孔；视图遮挡或未刷新
- `required_verification`: 比较设计范围与已创建单元；检查循环边界和筛选条件
- `auto_fix_allowed`: `gated`

## `member_global_offset`

- `anomaly_type`: member_global_offset
- `engineering_fault`: 构件整体相对设计基准偏移
- `visual_signals`: 整段构件平行偏移；多个相邻单元以相同方向错位
- `candidate_causes`: 坐标基准错误；坐标系转换错误；统一偏移重复施加
- `candidate_targets`: 节点生成 `x/y/z/datum`；坐标转换 `local_to_global/transform`；截面偏移 `SectionOffset`
- `required_facts`: 多个节点坐标；基准构件位置；偏移方向与量级
- `required_reference`: 设计坐标基准；构件布置要求
- `reject_conditions`: 相机投影或裁剪误差；合法偏心设计
- `required_verification`: 比较多个节点与设计基准；排除全局视图和截面偏移
- `auto_fix_allowed`: `gated`

## `symmetry_mapping_mismatch`

- `anomaly_type`: symmetry_mapping_mismatch
- `engineering_fault`: 对称构件的镜像或编号映射错误
- `visual_signals`: 应对称区域的轮廓或构件数量不对称；镜像过渡区短竖向单元边界数量或相对间距不一致；左右同类构件参数趋势不对应
- `candidate_causes`: 镜像复制错误；编号映射错误；左右分区索引不一致；单元生成 `loop_boundary` 错误
- `candidate_targets`: 对称复制 `mirror_axis/source_member`；编号映射 `id_map/section_index`；左右分区生成 `zone_boundary/loop_boundary`
- `required_facts`: 对称轴；左右对象映射；左右截面或节点序列；镜像过渡区短竖向单元边界数量和相对间距
- `required_reference`: 左右对称要求；明确非对称设计例外
- `reject_conditions`: 用户或模板明确允许非对称；对称轴未确认
- `required_verification`: 确认对称要求；构造镜像过渡区边界序列；比较短竖向单元边界数量和相对间距；构造左右对象映射；比较编号和参数序列
- `auto_fix_allowed`: `gated`
