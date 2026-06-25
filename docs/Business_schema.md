# 采购入库流程设计（改进版）

## 1. 业务对象

| 业务对象 | 说明 | 核心属性 |
|---------|------|----------|
| **采购清单** | 需求方创建，包含采购单头与采购单行 | 单号、需求部门、创建时间、状态（草稿/已发布/部分收货/已完成/已关闭） |
| **采购清单行** | 明细物料及数量 | 行号、物料编码、计划数量、已收货数量、单价、期望到货日期 |
| **供应商** | 提供物料的主体 | 供应商编码、名称、联系方式 |
| **物料** | 采购的货物基本信息 | 物料编码、名称、规格、单位、是否启用批次管理、是否启用二维码管理 |
| **发货通知单** | 供应商响应采购清单后创建，表示准备发货 | 通知单号、关联采购单号、供应商、预计发货时间、状态（新建/已发货/部分发货/完成） |
| **发货通知单行** | 对应采购单行，可拆分数量 | 行号、采购单行号、物料编码、通知数量、已发货数量 |
| **货运单** | 实际发出货物时创建，包含物流信息 | 货运单号、关联发货通知单号、承运商、运单号、发货时间、状态（在途/部分到货/已到货/已拒收） |
| **收货记录** | 仓库实际核对实物后创建，触发质检 | 收货单号、关联货运单号、收货人、收货时间、实收数量、外包装状态（合格/异常） |
| **收货记录行** | 按物料/批次明细收货 | 行号、物料编码、实收数量、批次号、二维码（如有）、是否启用质检 |
| **质检单** | 质检部门根据收货记录创建，记录检验结果 | 质检单号、关联收货单号、质检员、质检时间、整体结果（合格/不合格/部分合格） |
| **质检明细** | 按物料/批次逐项检验 | 明细号、物料编码、批次号、二维码、检验项目、标准值、实测值、单项结果、最终判定（合格/不合格/让步接收/拒收） |
| **退货单** | 质检不合格或到货异常时生成，退回供应商 | 退货单号、关联收货单号/质检单号、退货原因、退货数量、状态（待退/已退/已关闭） |
| **入库单** | 质检合格后正式入库，确定库位 | 入库单号、关联质检单号/收货单号、入库时间、库位编码、仓库位ID、操作人、状态（暂存/已上架） |
| **入库单行** | 按物料/批次/二维码入库 | 行号、物料编码、批次号、二维码、入库数量、库位编码、仓库位 |
| **库位** | 仓库存储位置 | 库位编码、仓库ID、库区类型（暂存区/合格区/不合格区）、容量、是否占用 |
| **二维码记录** | 统一管理货物二维码（可预生成或到货生成） | 二维码ID、物料编码、批次号、生成方（供应商/仓库）、生成时间、关联单据号 |

## 2. 业务活动及业务流程

### 2.1 角色及职责
- **需求方**：创建采购清单
- **供应商**：响应采购清单，创建发货通知单；实际发货时创建货运单
- **仓库收货员**：到货验收，创建收货记录，触发质检
- **质检员**：创建质检单，执行检验，判定结果
- **仓库管理员**：根据质检结果安排入库或退货，分配库位

### 2.2 正常流程（全部合格）

1. **需求方创建采购清单**（单头+单行）  
   - 状态：已发布

2. **供应商响应** → 创建**发货通知单**（可部分响应）  
   - 状态：新建

3. **供应商实际发货** → 创建**货运单**，关联发货通知单  
   - 状态：在途

4. **货物到达仓库** → 仓库收货员核对实物（数量、外包装），与货运单比对  
   - 若一致，创建**收货记录**，状态“已收货”；若不一致，可部分收货或拒收（走异常分支）  
   - 收货记录创建后，自动触发**质检单**创建（系统生成或人工创建）

5. **质检员执行质检**  
   - 扫描物料批次/二维码，填写检验结果  
   - 若全部合格 → 质检单整体结果“合格”

6. **仓库管理员分配库位**  
   - 系统推荐或人工选择正式库位

7. **创建入库单**  
   - 关联质检单，填写入库数量、库位信息  
   - 执行上架，入库单状态“已上架”

8. **流程完成**，更新采购清单行的已收货数量，若全部收完则采购清单状态“已完成”

### 2.3 异常流程示例（质检不合格）

- 步骤5中，质检判定部分/全部不合格 → 质检单结果“不合格”或“部分合格”  
- **分支A**：可让步接收 → 质检明细标记“让步接收”，质检员注明原因，仍走正常入库，但需额外审批  
- **分支B**：拒收 → 创建**退货单**，记录退货数量和原因；仓库将货物移至不合格区；通知供应商；货运单状态部分置为“已拒收”；采购清单行扣减可收货数量  
- **分支C**：部分合格 → 对合格部分创建入库单，不合格部分生成退货单

## 3. 业务对象相关表实体分解

### 3.1 采购模块

**表名：`purchase_order`**（采购单头）

| 字段 | 类型 | 说明 |
|------|------|------|
| po_id | bigint PK | 采购单号 |
| dept | varchar | 需求部门 |
| create_time | datetime | 创建时间 |
| status | varchar | 草稿/已发布/部分收货/已完成/已关闭 |

**表名：`purchase_order_line`**（采购单行）

| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | bigint PK | 行号 |
| po_id | bigint FK | 关联采购单头 |
| material_code | varchar | 物料编码 |
| planned_qty | decimal | 计划数量 |
| received_qty | decimal | 已收货数量 |
| unit_price | decimal | 单价 |
| expected_date | date | 期望到货日期 |

### 3.2 供应商响应与发货

**表名：`delivery_notice`**（发货通知单头）

| 字段 | 类型 | 说明 |
|------|------|------|
| notice_id | bigint PK | 通知单号 |
| po_id | bigint FK | 关联采购单 |
| supplier_code | varchar | 供应商编码 |
| expect_ship_time | datetime | 预计发货时间 |
| status | varchar | 新建/已发货/部分发货/完成 |

**表名：`delivery_notice_line`**（发货通知单行）

| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | bigint PK | |
| notice_id | bigint FK | |
| po_line_id | bigint FK | 采购单行号 |
| material_code | varchar | |
| notice_qty | decimal | 通知数量 |
| shipped_qty | decimal | 已发货数量 |

**表名：`freight_order`**（货运单）

| 字段 | 类型 | 说明 |
|------|------|------|
| freight_id | bigint PK | 货运单号 |
| notice_id | bigint FK | 关联发货通知单 |
| carrier | varchar | 承运商 |
| tracking_no | varchar | 运单号 |
| ship_time | datetime | 发货时间 |
| status | varchar | 在途/部分到货/已到货/已拒收 |

### 3.3 收货与质检

**表名：`receipt_record`**（收货记录头）

| 字段 | 类型 | 说明 |
|------|------|------|
| receipt_id | bigint PK | 收货单号 |
| freight_id | bigint FK | 关联货运单 |
| receiver | varchar | 收货人 |
| receipt_time | datetime | 收货时间 |
| package_status | varchar | 合格/异常 |

**表名：`receipt_record_line`**（收货记录行）

| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | bigint PK | |
| receipt_id | bigint FK | |
| material_code | varchar | |
| actual_qty | decimal | 实收数量 |
| batch_no | varchar | 批次号 |
| qr_code | varchar | 二维码（可为空） |
| need_qc | boolean | 是否需质检（默认true） |

**表名：`qc_order`**（质检单头）

| 字段 | 类型 | 说明 |
|------|------|------|
| qc_id | bigint PK | 质检单号 |
| receipt_id | bigint FK | 关联收货单 |
| qc_user | varchar | 质检员 |
| qc_time | datetime | 质检时间 |
| overall_result | varchar | 合格/不合格/部分合格 |

**表名：`qc_detail`**（质检明细）

| 字段 | 类型 | 说明 |
|------|------|------|
| detail_id | bigint PK | |
| qc_id | bigint FK | |
| material_code | varchar | |
| batch_no | varchar | |
| qr_code | varchar | |
| check_item | varchar | 检验项目（如外观、尺寸） |
| standard_value | varchar | 标准值 |
| measured_value | varchar | 实测值 |
| item_result | varchar | 单项结果（合格/不合格） |
| final_judgment | varchar | 合格/不合格/让步接收/拒收 |

### 3.4 退货处理

**表名：`return_order`**（退货单头）

| 字段 | 类型 | 说明 |
|------|------|------|
| return_id | bigint PK | 退货单号 |
| source_type | varchar | 来源类型：收货单/质检单 |
| source_id | bigint | 关联来源单据ID |
| reason | text | 退货原因 |
| total_qty | decimal | 退货数量 |
| status | varchar | 待退/已退/已关闭 |

**表名：`return_order_line`**（退货单行）

| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | bigint PK | |
| return_id | bigint FK | |
| material_code | varchar | |
| batch_no | varchar | |
| qr_code | varchar | |
| return_qty | decimal | 退货数量 |

### 3.5 入库与库位

**表名：`inbound_order`**（入库单头）

| 字段 | 类型 | 说明 |
|------|------|------|
| inbound_id | bigint PK | 入库单号 |
| qc_id | bigint FK | 关联质检单（合格部分） |
| source_receipt_id | bigint FK | 也可直接关联收货单（备选） |
| inbound_time | datetime | 入库时间 |
| operator | varchar | 操作人 |
| status | varchar | 暂存/已上架 |

**表名：`inbound_order_line`**（入库单行）

| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | bigint PK | |
| inbound_id | bigint FK | |
| material_code | varchar | |
| batch_no | varchar | |
| qr_code | varchar | |
| inbound_qty | decimal | 入库数量 |
| location_code | varchar | 库位编码（外键） |

**表名：`location`**（库位主数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| location_code | varchar PK | 库位编码 |
| warehouse_id | varchar | 仓库ID |
| zone_type | varchar | 暂存区/合格区/不合格区 |
| capacity | decimal | 最大容量 |
| is_occupied | boolean | 是否占用 |

### 3.6 二维码辅助管理

**表名：`qr_code_master`**（二维码记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| qr_id | bigint PK | |
| qr_code | varchar unique | 二维码值 |
| material_code | varchar | |
| batch_no | varchar | |
| generated_by | varchar | 供应商/仓库 |
| generate_time | datetime | |
| source_doc_no | varchar | 生成时的关联单号（如发货通知单号） |

## 4. 表关系简要说明

- `purchase_order` 1:N `purchase_order_line`
- `purchase_order` 1:N `delivery_notice`
- `delivery_notice` 1:N `delivery_notice_line`
- `delivery_notice` 1:N `freight_order`
- `freight_order` 1:N `receipt_record`
- `receipt_record` 1:N `receipt_record_line`
- `receipt_record` 1:1 `qc_order`（通过 `receipt_id` 触发）
- `qc_order` 1:N `qc_detail`
- `qc_order` 1:1 或 1:N `inbound_order`（若分批入库可能多张）
- `inbound_order` 1:N `inbound_order_line`
- `inbound_order_line` N:1 `location`
- `qc_order` 或 `receipt_record` 1:N `return_order`（当不合格时）