from __future__ import annotations


LOCAL_COMMAND_DESCRIPTIONS = {
    "init": "创建配置文件和空 Vault，不覆盖已有配置。",
    "doctor": "检查 Python、SQLite、FTS5、图像格式和视觉能力。",
    "serve": "启动同时承载 API 与 WebUI 的唯一长期本机服务。",
    "open": "在浏览器中打开当前服务的本机会话。",
    "stop": "请求当前服务完成手头请求后正常关闭。",
    "commands": "从运行中的服务读取公开业务命令列表。",
}


REMOTE_COMMAND_DESCRIPTIONS = {
    "status": "查询当前服务、Vault、数据库和视觉能力状态。",
    "import.stage": "按原图哈希将本机图片导入持久待审队列。",
    "queue.get": "读取一个待审队列项目的完整信息。",
    "queue.preview": "读取一个待审项目的安全预览信息。",
    "search.pending": "检索尚未进入正式资料库的待审项目。",
    "analysis.record": "保存 Agent 对待审素材的分析草稿和来源信息。",
    "proposal.create": "为资产、概念、知识或 Prompt 创建新提案。",
    "proposal.revise": "基于已有提案创建必须重新审核的新修订。",
    "proposal.get": "按提案 ID 和修订号读取最终提案内容。",
    "candidate.get": "读取尚未正式建立的概念候选项。",
    "asset.get": "按稳定资产 ID 读取正式资产记录。",
    "asset.preview": "读取正式资产的安全预览信息。",
    "search.concepts": "检索已批准的概念、别名和明确关系。",
    "search.assets": "检索只包含已审核事实的正式资产。",
    "search.explain": "解释正式资产为什么匹配当前搜索。",
    "search.related": "查找与指定正式资产相关的素材。",
    "knowledge.get": "读取指定的已批准知识条目。",
    "knowledge.search": "检索已批准的版本化知识内容。",
    "prompt.get": "读取指定的已批准 Prompt。",
    "prompt.list": "列出已批准的版本化 Prompt。",
    "prompt.render": "用声明变量确定性渲染已批准 Prompt。",
    "visual.index": "为正式资产建立可重建的本机视觉特征。",
    "visual.search": "使用本机视觉特征查找相似正式资产。",
    "search.rebuild": "从已批准事实重新构建正式搜索索引。",
    "operations.recover": "恢复可安全继续或收尾的中断操作。",
    "review.list": "列出当前等待用户处理的提案。",
    "review.get": "读取审核前必须展示的完整提案版本。",
    "review.action": "绑定提案版本和哈希执行批准、退回、拒绝或稍后。",
}


COMMAND_DESCRIPTIONS = {
    **LOCAL_COMMAND_DESCRIPTIONS,
    **REMOTE_COMMAND_DESCRIPTIONS,
}
