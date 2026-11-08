# 必要示例契约

本文件定向完善 V0.8 交接契约，不代表已有应用、CLI 或 API。JSON Schema 采用 Draft 2020-12；协议名 0.8-reviewed-example 表示文档示例。ID、名称及哈希均为虚构样例，64 位示例哈希语法有效但不代表真实文件或真实审批。

## 通用约定与权限

接口使用稳定 ID、带时区时间、受管理相对路径。Core 持久保存操作 ID 与请求摘要：同 ID 同请求返回既有结果，同 ID 不同内容报冲突。提案正文不可在批准后静默更改；摘要覆盖操作、目标 ID、目标修订、文件哈希、来源、正文、正式概念 ID、候选依赖及提案修订，排除摘要本身。规范化方法可参考 RFC 8785，实际方案待选型；不以 JSON 字符串随意散列代替固定规则。

本地 CLI 优先，MCP 后置。Agent 只能读取、检索、暂存、分析、起草和请求审核；approval.record 与 commit.execute 仅受信组件内部调用。Schema 合法、摘要相符或 Agent 自填 approved=true 均不构成可信批准。

| 操作 | 职责 | 边界 |
| --- | --- | --- |
| import.stage | 复制并校验原图，记录批次和基础信息 | 不正式分类 |
| proposal.create / revise / get | 资产/概念提案起草、修订、详情 | 不批准、不直接提交 |
| concept.propose / candidate.get | 新概念提案、去重候选及状态/正式 ID 映射 | 不写正式词典 |
| review.open / status | 打开 Reviewer、查询审核进度 | Agent 无批准参数 |
| asset.get / asset.preview | 正式详情、受控预览或原图只读引用 | 不包含未审核草案 |
| queue.get / queue.preview | 暂存/稍后详情、受控预览或原图只读引用 | 不转为正式事实 |
| search.assets / concepts / pending / related | 正式、术语、待审、明确关系查询 | 状态和权限隔离 |
| search.explain / suggest | 按需解释、查询条件建议 | 不自动解释、不新增概念 |

## 暂存与只读素材接口

<!-- contract:stage -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-import-demo",
  "batch_id": "batch-demo-01",
  "source_handle": "selected-file-demo-01",
  "source": {
    "original_name": "雨夜参考.png",
    "origin": "用户选择的本地文件",
    "user_note": "以后再分类"
  },
  "analysis_requested": false
}
```

source_handle 是已校验的文件选择/导入句柄，不是任意目标路径。Core 必须复制到受管理持久存储，返回 queue_item_id、file_hash、batch_id 与基础元数据。staging/deferred 不是缓存。

| 只读接口 | 必填输入 | 输出与状态 |
| --- | --- | --- |
| asset.get | asset_id | 稳定 ID、active/archived、正式 revision、file_hash、已批准元数据/概念、来源、可用性；不返回新草案 |
| asset.preview | asset_id、variant=preview/original | 经过校验的只读内容句柄、真实 MIME、尺寸、哈希和有效期；archived 可通过已知 ID 读取，但不进入默认搜索 |
| queue.get | queue_item_id | 稳定 ID、batch_id、队列状态、基础来源/备注、file_hash、格式/尺寸与草案引用；需要草案详情时明确标记 unreviewed=true |
| queue.preview | queue_item_id、variant=preview/original | 当前持久原图/受控预览的只读内容句柄；无需历史会话或旧令牌 |

以上接口绑定当前用户获准的 Vault，Core 以稳定 ID 查内部相对路径，不接受任意原图路径、输出路径或写入模式。读取前校验根目录范围、路径穿越/符号链接逃逸、文件存在性、类型和资源限制；原图引用还要校验与登记指纹一致。派生缩略图有自己的哈希，不能冒充原图哈希。

内容句柄可由受控工具直接读取，或由 Core 生成只读导出副本供模型读取；不授予 Agent 正式库写权限，不暴露批准凭据，也不能将任意文件访问授权封装在句柄内。只读副本可清理，持久原图不可清理。短期句柄可过期，Vault+asset_id/queue_item_id 才是可持久定位方式；重启后重新请求接口生成新句柄，不保存旧临时路径作为唯一引用。具体句柄交付机制必须在 Phase 0 验证。

<!-- contract:queue-preview-request -->
```json
{
  "queue_item_id": "queue-demo-01",
  "variant": "original"
}
```

<!-- contract:queue-preview-response -->
```json
{
  "queue_item_id": "queue-demo-01",
  "batch_id": "batch-demo-01",
  "queue_state": "deferred",
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "variant": "original",
  "content_handle": "readonly-demo-content",
  "access": "read-only",
  "mime_type": "image/png",
  "unreviewed": true,
  "expires_at": "2026-11-07T16:00:00+08:00"
}
```

仅示例时间；真实返回须使用当前有效期限。Core 记录持久 ID，句柄不是跨会话保证。返回详情不代表视觉解码已成功；不支持格式返回 UNSUPPORTED_FORMAT，缺失记录返回 NOT_FOUND，文件缺失返回 FILE_MISSING，指纹变化返回 HASH_MISMATCH，越权返回 ACCESS_DENIED，旧句柄返回 HANDLE_EXPIRED。保留基础信息和原图，不假装成功预览或分析。

跨会话恢复流程：批量 import.stage → Reviewer 对当前批次未处理集合执行“后续全部稍后” → 持久保存批次/队列/原图并正常退出 → 若干天后 Agent 以 search.pending 查批次 → queue.get 取状态和必要草案 → queue.preview 重新获取图片 → 重新分析或修订草案 → 独立 Reviewer 批准后提交。整个流程不依赖旧聊天记录、缓存句柄或重新上传原图，也不要求人工整理目录。

## 按操作区分的资产提案

asset.create 只用 queue_item_id，target_revision=0；asset.update/asset.archive 只用正式 asset_id，target_revision≥1。两类目标字段互斥，source 仅记提案来源，不再重复充当目标 ID。正式资产更新不必出现在待审导入队列，可通过 proposal_id 请求审核。

create 的 changes.title 必填；update 的 changes 是标题、描述和设计价值的补丁，concept_ids 是本次希望保留的完整正式概念集合（空数组可清空关联），candidate_concept_refs 是尚未落实的候选依赖。未提供的文本字段不改；Core 比较前后状态拒绝无变化请求。这里的概念集合是多标签、多用途关联，不要求全部分面填写。图片内容不可被 update 替换；更改图像须新建衍生资产。

archive 的 changes 只含 state=archived 和 reason；提交后保留原图、来源、审核记录与关联，增加正式修订号，退出默认 active 检索，可按 ID 读取。V1 不提供 asset.delete、物理删除或反归档接口；未来如确需删除，需另行定义对象引用、恢复记录保护、权限和额外用户确认，不能复用 archive 或 reject 擦除原图。

### 资产提案 Schema

Schema 校验 Core 登记后的规范提案。首次 proposal.create/concept.propose 可由 Core 接收目标与正文后分配提案/候选 ID；登记完成后补齐下列字段再进入审核。Agent 不能指定未分配 ID 冒用其他提案。修订沿用 proposal.revise，Core 原子检查 revision 是上一版加一，重新生成摘要；新版本不继承旧批准。

<!-- contract:asset-schema -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "V0.8 asset proposal example",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "contract_version",
    "operation_id",
    "proposal_id",
    "revision",
    "operation",
    "source",
    "file_hash",
    "target_revision",
    "uncertainties",
    "changes"
  ],
  "properties": {
    "contract_version": {
      "const": "0.8-reviewed-example"
    },
    "operation_id": {
      "type": "string",
      "minLength": 1
    },
    "proposal_id": {
      "type": "string",
      "minLength": 1
    },
    "revision": {
      "type": "integer",
      "minimum": 1
    },
    "operation": {
      "enum": [
        "asset.create",
        "asset.update",
        "asset.archive"
      ]
    },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "origin"
      ],
      "properties": {
        "origin": {
          "enum": [
            "user-request",
            "agent-analysis"
          ]
        },
        "note": {
          "type": "string"
        }
      }
    },
    "file_hash": {
      "type": "string",
      "pattern": "^sha256:[a-f0-9]{64}$"
    },
    "target_revision": {
      "type": "integer",
      "minimum": 0
    },
    "queue_item_id": {
      "type": "string",
      "minLength": 1
    },
    "asset_id": {
      "type": "string",
      "minLength": 1
    },
    "analysis_run_id": {
      "type": "string",
      "minLength": 1
    },
    "concept_ids": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "candidate_concept_refs": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "candidate_id",
          "proposal_id",
          "revision",
          "proposal_hash"
        ],
        "properties": {
          "candidate_id": {
            "type": "string",
            "minLength": 1
          },
          "proposal_id": {
            "type": "string",
            "minLength": 1
          },
          "revision": {
            "type": "integer",
            "minimum": 1
          },
          "proposal_hash": {
            "type": "string",
            "pattern": "^sha256:[a-f0-9]{64}$"
          }
        }
      }
    },
    "uncertainties": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "changes": {
      "type": "object"
    }
  },
  "oneOf": [
    {
      "properties": {
        "operation": {
          "const": "asset.create"
        },
        "target_revision": {
          "const": 0
        },
        "changes": {
          "allOf": [
            {
              "type": "object",
              "additionalProperties": false,
              "properties": {
                "title": {
                  "type": "string",
                  "minLength": 1
                },
                "description": {
                  "type": "string"
                },
                "design_value": {
                  "type": "string"
                }
              }
            },
            {
              "required": [
                "title"
              ]
            }
          ]
        }
      },
      "required": [
        "queue_item_id",
        "concept_ids",
        "candidate_concept_refs"
      ],
      "not": {
        "required": [
          "asset_id"
        ]
      }
    },
    {
      "properties": {
        "operation": {
          "const": "asset.update"
        },
        "target_revision": {
          "type": "integer",
          "minimum": 1
        },
        "changes": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "title": {
              "type": "string",
              "minLength": 1
            },
            "description": {
              "type": "string"
            },
            "design_value": {
              "type": "string"
            }
          }
        }
      },
      "required": [
        "asset_id",
        "concept_ids",
        "candidate_concept_refs"
      ],
      "not": {
        "required": [
          "queue_item_id"
        ]
      }
    },
    {
      "properties": {
        "operation": {
          "const": "asset.archive"
        },
        "target_revision": {
          "type": "integer",
          "minimum": 1
        },
        "changes": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "state",
            "reason"
          ],
          "properties": {
            "state": {
              "const": "archived"
            },
            "reason": {
              "type": "string",
              "minLength": 1
            }
          }
        }
      },
      "required": [
        "asset_id"
      ],
      "not": {
        "anyOf": [
          {
            "required": [
              "queue_item_id"
            ]
          },
          {
            "required": [
              "concept_ids"
            ]
          },
          {
            "required": [
              "candidate_concept_refs"
            ]
          }
        ]
      }
    }
  ]
}
```

Core 额外检查：目标属于当前 Vault；create 的队列尚未正式提交且文件匹配；update/archive 的正式资产存在且为 active、修订号匹配；引用与分析记录有效；正式概念均已批准；候选依赖未消解时只能保存 draft，禁止批准或提交。Schema 不替代这些运行时检查。

### 新增、更新、归档示例

<!-- contract:asset-create -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-create-demo",
  "proposal_id": "proposal-create-demo",
  "revision": 1,
  "operation": "asset.create",
  "source": {
    "origin": "agent-analysis"
  },
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "target_revision": 0,
  "queue_item_id": "queue-demo-01",
  "analysis_run_id": "analysis-demo-01",
  "concept_ids": [
    "concept-demo-city"
  ],
  "candidate_concept_refs": [],
  "uncertainties": [],
  "changes": {
    "title": "城市雨夜光影参考",
    "description": "已供用户审核的描述"
  }
}
```

<!-- contract:asset-update -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-update-demo",
  "proposal_id": "proposal-update-demo",
  "revision": 1,
  "operation": "asset.update",
  "source": {
    "origin": "agent-analysis"
  },
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "target_revision": 3,
  "analysis_run_id": "analysis-demo-01",
  "concept_ids": [
    "concept-demo-city"
  ],
  "candidate_concept_refs": [],
  "uncertainties": [],
  "changes": {
    "title": "修订后的雨夜参考标题"
  },
  "asset_id": "asset-demo-01"
}
```

<!-- contract:asset-archive -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-archive-demo",
  "proposal_id": "proposal-archive-demo",
  "revision": 1,
  "operation": "asset.archive",
  "source": {
    "origin": "agent-analysis"
  },
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "target_revision": 4,
  "uncertainties": [],
  "changes": {
    "state": "archived",
    "reason": "不再作为日常参考"
  },
  "asset_id": "asset-demo-01"
}
```

## 新标准概念的最小闭环

V1 实现 concept.create；候选概念与正式 concept_id 分开，不自动扩大为词典治理系统。概念修订/合并、批量迁移和复杂关系治理只保留边界，本版不暴露 concept.update/concept.merge 可调用正式接口，收到请求返回 OPERATION_NOT_SUPPORTED。

1. Agent 先调用 search.concepts，对中英文首选名称和严格别名做规范化匹配并看定义、分面及关系；精确命中优先复用，近似命中列为人工候选，不能把 related 当同义。Core 在提案登记和提交时各复查一次，防止并发重复。
2. 未找到可复用概念时，通过 concept.propose 提交 concept.create 草案。Core 分配稳定 candidate_id、proposal_id、revision，生成 proposal_hash；candidate_id 仅是待审引用，绝不能装成正式 concept_id。
3. Reviewer 展示重复候选、首选名称/中英文术语、定义、十二分面之一、严格别名、broader/narrower/related 关系与不确定性。V1 关系仅引用现有正式概念，支持少量显式关系与必要循环/冲突检查，不做高级推理。候选间关系需先后批准，不建立复杂依赖图。修改产生新提案修订和摘要。
4. 用户通过受信组件批准最终概念正文。Core 复验去重、字段、关系和批准，SQLite 单事务分配新的正式 concept_id 并写词条、关系、初始概念修订、审核与操作结果。正式 ID 由 Core 生成，不由 Agent 指定；幂等重试返回相同 ID，不重复建词。若名称/严格别名与正式概念冲突，返回 CONCEPT_DUPLICATE；不自动合并。受控词典查询可返回已批准词条，但没有未经批准的资产关联。
5. candidate.get 返回状态及提交成功的 resolved_concept_id。资产草案可以用 candidate_concept_refs 绑定候选 ID、提案及修订/摘要，但它们只存草案，不能进正式词典、asset_concepts 或正式资产索引。旧 suggested_new_concepts 的想法需先转为候选提案，再写候选引用，不再在资产 changes 内夹带隐式建词。
6. 概念提交成功后，Agent 将候选引用替换为正式 concept_id，并生成资产的新提案修订/摘要；Reviewer 再审核该最终资产版本。不得自动重写已经批准的资产提案。新概念被拒绝、被新版本取代或创建失败时，资产草案保持待处理，原图不变；Agent 按用户要求改用既有概念、修订/重试候选，或移除该候选后重新审核资产。不能静默跳过依赖或把未批准名称当标签。

V1 不支持“一次批准动作同时创建概念和资产”。允许同一 Reviewer 会话先审概念，概念事务提交成功后刷新资产提案，再单独批准资产。这样无跨对象组合审批或分布式事务：概念创建失败，资产不能提交；概念已成功但资产失败，概念仍为合法可复用词条，资产保留待审并按操作日志重试，不回滚已批准概念，也不发布半成品资产。复合原子审批后置。

### 新概念提案 Schema 与示例

<!-- contract:concept-schema -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "V0.8 concept.create example",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "contract_version",
    "operation_id",
    "proposal_id",
    "revision",
    "operation",
    "candidate_id",
    "target_revision",
    "source",
    "uncertainties",
    "changes"
  ],
  "properties": {
    "contract_version": {
      "const": "0.8-reviewed-example"
    },
    "operation_id": {
      "type": "string",
      "minLength": 1
    },
    "proposal_id": {
      "type": "string",
      "minLength": 1
    },
    "revision": {
      "type": "integer",
      "minimum": 1
    },
    "operation": {
      "const": "concept.create"
    },
    "candidate_id": {
      "type": "string",
      "minLength": 1
    },
    "target_revision": {
      "const": 0
    },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "note"
      ],
      "properties": {
        "note": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "uncertainties": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "changes": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "preferred_name",
        "terms",
        "definition",
        "facet",
        "aliases",
        "relations"
      ],
      "properties": {
        "preferred_name": {
          "type": "string",
          "minLength": 1
        },
        "terms": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "zh",
            "en"
          ],
          "properties": {
            "zh": {
              "type": "string",
              "minLength": 1
            },
            "en": {
              "type": [
                "string",
                "null"
              ]
            }
          }
        },
        "definition": {
          "type": "string",
          "minLength": 1
        },
        "facet": {
          "enum": [
            "work_type",
            "subject",
            "scene",
            "style",
            "technique",
            "composition",
            "lighting",
            "color",
            "material",
            "pose_action",
            "mood",
            "usage"
          ]
        },
        "aliases": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        },
        "relations": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "kind",
              "concept_id"
            ],
            "properties": {
              "kind": {
                "enum": [
                  "broader",
                  "narrower",
                  "related"
                ]
              },
              "concept_id": {
                "type": "string",
                "minLength": 1
              }
            }
          }
        }
      }
    }
  }
}
```

<!-- contract:concept-create -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-concept-demo",
  "proposal_id": "proposal-concept-demo",
  "revision": 1,
  "operation": "concept.create",
  "candidate_id": "candidate-demo-01",
  "target_revision": 0,
  "source": {
    "note": "素材分析中遇到的术语候选；名称和释义待核实"
  },
  "uncertainties": [
    "是否与已有术语重复需核实"
  ],
  "changes": {
    "preferred_name": "示例柔光技法",
    "terms": {
      "zh": "示例柔光技法",
      "en": null
    },
    "definition": "用于演示新概念审核的定义，不是生产词表内容。",
    "facet": "technique",
    "aliases": [],
    "relations": []
  }
}
```

### 含候选引用的资产草案（不可批准）

<!-- contract:asset-unresolved-candidate -->
```json
{
  "contract_version": "0.8-reviewed-example",
  "operation_id": "op-create-pending-concept",
  "proposal_id": "proposal-create-pending-concept",
  "revision": 1,
  "operation": "asset.create",
  "source": {
    "origin": "agent-analysis"
  },
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "target_revision": 0,
  "queue_item_id": "queue-demo-01",
  "analysis_run_id": "analysis-demo-01",
  "concept_ids": [
    "concept-demo-city"
  ],
  "candidate_concept_refs": [
    {
      "candidate_id": "candidate-demo-01",
      "proposal_id": "proposal-concept-demo",
      "revision": 1,
      "proposal_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
    }
  ],
  "uncertainties": [],
  "changes": {
    "title": "城市雨夜光影参考",
    "description": "已供用户审核的描述"
  }
}
```

该草案语法可成立，但审批/提交必须以 DEPENDENCY_UNRESOLVED 拒绝，直至生成候选全部落实为正式 concept_id 的新资产版本。

## Reviewer 专有动作与状态

approve、request_changes、reject、defer_current、defer_remaining_batch 仅受信 Reviewer 调用。Agent 可以请求打开提案，不能自行触发批准。资产批准保留 VARP 五项绑定 proposal_id + revision + proposal_hash + file_hash + target_revision，且包括操作与对应 queue_item_id 或 asset_id；该目标也包含在正文摘要中。

<!-- contract:asset-approval -->
```json
{
  "action": "approve",
  "operation": "asset.update",
  "asset_id": "asset-demo-01",
  "proposal_id": "proposal-update-demo",
  "revision": 1,
  "proposal_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
  "file_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "target_revision": 3,
  "operation_id": "op-review-update-demo"
}
```

这是针对上文 asset.update 的受信动作载荷示例；create 用 queue_item_id，archive 用 asset_id，必须与被批准提案完全一致。proposal_hash 为示意值，真实值由 Core 对固定规范化正文计算，不能接受示例字面值当真实审批。

独立 concept.create 没有原图目标，因此不伪造 file_hash：概念批准绑定 operation、candidate_id、proposal_id、revision、proposal_hash、target_revision=0。此为对象类型明确的审批契约扩展，不取代或减少资产的五项绑定。

<!-- contract:concept-approval -->
```json
{
  "action": "approve",
  "operation": "concept.create",
  "candidate_id": "candidate-demo-01",
  "proposal_id": "proposal-concept-demo",
  "revision": 1,
  "proposal_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
  "target_revision": 0,
  "operation_id": "op-review-concept-demo"
}
```

批准只改变 Proposal 为 approved；可信 commit.execute 成功才使资产 staged→active、active 更新 revision 或 active→archived。Operation 独立记录 pending/committing/committed/failed；Queue 独立记录 pending/in_review/deferred/resolved。概念批准也必须成功提交后才生成可复用正式 ID。哈希、版本、目标修订或候选依赖变化均使对应旧批准不可复用。

批量批准仍逐项绑定最终提案与对象，不能用泛化“整批同意”替代。稍后只需当前 queue_item_id，不要求已分析或已有提案；后续全部稍后绑定当前 batch_id 的尚未处理集合，返回逐项结果，不覆盖已批准/拒绝项、不影响未来批次。拒绝不删除原图。

## 正式搜索 Query

```json
{
  "contract_version": "0.8-reviewed-example",
  "scope": "active",
  "must": [{"concept_id": "concept-demo-person"}],
  "should": [
    {"concept_id": "concept-demo-soft-side-light"},
    {"text": "秋季穿搭"}
  ],
  "must_not": [],
  "filters": {"orientation": "landscape"},
  "expand_narrower": true,
  "expand_related": false,
  "limit": 10,
  "include_explanation": false
}
```

执行前将自然语言概念名解析为真实 concept_id。上例 ID 不是种子词典；十二个正式分面见 REQUIREMENTS.md R05。Core 校验条件集合、范围、数量、过滤项及文本长度，不接受原始 SQL/任意 MATCH 表达式。严格条件无法落实时返回未解析条件或能力限制，不偷偷忽略。

### 搜索结果示例

```json
{
  "scope": "active",
  "items": [
    {
      "asset_id": "asset-demo-01",
      "title": "已批准的素材标题",
      "thumbnail_handle": "preview-demo-01",
      "open_handle": "asset-demo-01"
    }
  ],
  "constraints_relaxed": false,
  "unresolved_conditions": [],
  "next_cursor": null
}
```

Agent 只展示真实返回项，默认不附命中理由。空结果返回 items=[]，不填充虚构资产。若用户同意放宽搜索，用新 Query 执行并明确哪些条件改变；不得把宽松结果当原始严格命中。

### 待审查询示例

```json
{
  "scope": "pending",
  "status": ["deferred"],
  "batch_id": "batch-demo-01",
  "imported_after": "2026-11-01T00:00:00+08:00",
  "text_in_basic_metadata": "雨夜参考",
  "limit": 30
}
```

只检索基础来源信息和用户备注；未审核 AI 草案在详情返回且明确 draft，不能作为正式命中事实。批次统计按需返回 total_pending、counts_by_batch、oldest_pending_at。

## 错误与重试语义建议

| 错误码 | 含义/处理 |
| --- | --- |
| OPERATION_NOT_SUPPORTED | V1 未实现操作（含物理删除/概念治理），不接受隐藏提交 |
| DEPENDENCY_UNRESOLVED | 候选概念尚未落实，资产保持草案 |
| CONCEPT_DUPLICATE | 名称/严格别名冲突，人工选择复用或修订，不自动合并 |
| NOT_FOUND / FILE_MISSING | 记录不存在或文件缺失；不伪造预览 |
| ACCESS_DENIED / HANDLE_EXPIRED | 越权或句柄过期；过期可凭稳定 ID 重新读取 |
| VALIDATION_FAILED | 不合法输入，修正请求；不能假装成功 |
| UNSUPPORTED_FORMAT / RESOURCE_LIMIT | 文件不支持或超限；保留可保留资料并提示 |
| UNAUTHORIZED_REVIEW | 调用者/用户动作不可信；禁止重试绕过 |
| STALE_PROPOSAL | 提案修订或摘要不符，重新显示最终版本审核 |
| TARGET_REVISION_CONFLICT | 正式资产已被修订；刷新目标和草案后重新审核 |
| HASH_MISMATCH | 文件变化，停止正式提交 |
| IDEMPOTENCY_CONFLICT | 同 operation_id 不同内容；不得覆盖旧操作 |
| UNKNOWN_CONCEPT / UNRESOLVED_CONDITION | 解析或查询约束不成立，不自行创正式标签 |
| STORAGE_FULL / STORAGE_UNAVAILABLE | 不发布半成品；保留已完整暂存资料 |
| DATABASE_BUSY | 有限重试，仍失败则报告；无无限循环 |
| RECOVERY_REQUIRED | 有未完成操作，受控恢复后继续 |
| ASSET_UNAVAILABLE | 原图缺失/异常，不返回虚假可用状态 |

统一错误返回建议包含 code、简短中文 message、operation_id、retryable 和必要状态。日志不包含秘密或整幅图片数据。

## 后续扩展契约（1.1）

`knowledge.create/update/archive` 与 `prompt.create/update/archive` 沿用 change_proposals、proposal_hash、target_revision、可信 Reviewer 和幂等 operation_id。它们没有原图目标，因此不伪造 file_hash；批准绑定 operation、target_id、proposal_id、revision、proposal_hash 与 target_revision。正式提交前草案不能进入知识 FTS 或 Prompt 列表。

```json
{
  "operation_id": "op-knowledge-demo",
  "operation": "knowledge.create",
  "target_revision": 0,
  "changes": {
    "title": "逆光观察",
    "summary": "逆光素材的观察要点",
    "content_markdown": "# 逆光\n观察轮廓、主体曝光与背景亮度。",
    "links": [{"target_kind": "concept", "target_id": "concept-demo-backlight"}]
  }
}
```

```json
{
  "operation_id": "op-prompt-demo",
  "operation": "prompt.create",
  "target_revision": 0,
  "changes": {
    "name": "构图分析",
    "description": "生成构图观察任务",
    "template": "分析 {{subject}} 的构图。",
    "variables": {"subject": {"type": "string", "required": true}},
    "knowledge_ids": [],
    "concept_ids": []
  }
}
```

`prompt.render` 只接受正式 prompt_id 和已声明变量，返回确定性文本及引用修订，不执行表达式。`visual.index` 只更新可重建派生特征；`visual.search` 必须且只能接受 asset_id 或 queue_item_id，返回按 Apple Vision distance 升序排列的 active 资产。相似结果不自动写标签、关系或知识。

WebUI 只代理 `status`、详情/预览、正式/待审/知识/Prompt/相似查询与 `prompt.render`；提案、审核、提交、索引重建等写操作不在 Web 白名单内。
