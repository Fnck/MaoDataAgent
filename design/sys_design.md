## 表结构设计

### 1. 业务活动表 (`business_activity`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| activity_id | int PK | 活动唯一标识 |
| name | varchar(100) | 活动名称 |
| description | text | 活动详细描述 |
| pre_activities | text | 前序活动ID列表（逗号分隔） |
| post_activities | text | 后序活动ID列表（逗号分隔） |
| operated_object_ids | text | 操作的主要业务对象ID列表 |
| input_entities | text | 输入实体（表名列表） |
| output_entities | text | 输出实体（表名列表） |
| node_metrics | text | 活动节点相关指标 |
| created_by | varchar(50) | 创建人 |
| created_time | datetime | 创建时间 |
| updated_by | varchar(50) | 更新人 |
| updated_time | datetime | 更新时间 |

### 2. 业务对象表 (`business_object`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| object_id | int PK | 业务对象唯一标识 |
| name | varchar(100) | 业务对象名称 |
| description | text | 业务对象描述 |
| related_entities | text | 相关实体（表名列表） |
| entity_relationships | text | 实体关联关系描述 |
| maintainer | varchar(50) | 维护人 |
| department | varchar(50) | 所属部门 |
| permissions | text | 权限相关字段 |
| created_by | varchar(50) | 创建人 |
| created_time | datetime | 创建时间 |
| updated_by | varchar(50) | 更新人 |
| updated_time | datetime | 更新时间 |

### 3. 业务规则表 (`business_rule`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| rule_id | int PK | 规则唯一标识 |
| name | varchar(100) | 规则名称 |
| description | text | 规则描述 |
| category | varchar(50) | 规则类别 |
| condition_expression | text | 条件表达式 |
| associated_activity_id | int | 关联的业务活动ID |
| associated_object_id | int | 关联的业务对象ID |
| priority | int | 优先级 |
| status | varchar(20) | 状态（启用/禁用） |
| created_by | varchar(50) | 创建人 |
| created_time | datetime | 创建时间 |
| updated_by | varchar(50) | 更新人 |
| updated_time | datetime | 更新时间 |

### 4. 指标表 (`metric`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| metric_id | int PK | 指标唯一标识 |
| name | varchar(100) | 指标名称 |
| business_meaning | text | 指标业务含义 |
| calculation_formula | text | 计算公式 |
| query_logic | text | 查询逻辑（SQL） |
| unit | varchar(20) | 指标单位 |
| data_source | varchar(100) | 数据来源 |
| refresh_cycle | varchar(20) | 刷新周期 |
| created_by | varchar(50) | 创建人 |
| created_time | datetime | 创建时间 |
| updated_by | varchar(50) | 更新人 |
| updated_time | datetime | 更新时间 |

### 5. 业务对象关系表 (`business_object_relationship`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| relationship_id | int PK | 关系唯一标识 |
| object_id_1 | int | 业务对象1 ID |
| object_id_2 | int | 业务对象2 ID |
| relationship_type | varchar(20) | 关系类型 |
| join_logic | text | JOIN 逻辑描述 |
| constraint_logic | text | 约束逻辑描述 |
| join_direction | varchar(10) | JOIN 方向 |
| union_logic | text | UNION 逻辑（可选） |
| created_by | varchar(50) | 创建人 |
| created_time | datetime | 创建时间 |
| updated_by | varchar(50) | 更新人 |
| updated_time | datetime | 更新时间 |

### 6. 业务活动与指标关联表 (`activity_metric_rel`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| id | int PK | 关联唯一标识 |
| activity_id | int | 业务活动ID |
| metric_id | int | 指标ID |
| usage_stage | varchar(50) | 指标使用阶段 |
| created_time | datetime | 创建时间 |

### 7. 业务活动与实体关联表 (`activity_entity_rel`)

| 字段名 | 数据类型 | 说明 |
|--------|----------|------|
| id | int PK | 关联唯一标识 |
| activity_id | int | 业务活动ID |
| entity_name | varchar(100) | 表名或实体名称 |
| entity_type | varchar(10) | 类型（INPUT/OUTPUT） |
| order_index | int | 顺序 |
| created_time | datetime | 创建时间 |
