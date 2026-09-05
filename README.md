# MiniMax H3 Director Suite

面向 Codex + ComfyUI 的 MiniMax H3 短剧导演与本地执行工具包。

本仓库将两个可独立安装的 Codex Skills 组织在一起：

- `oh-my-minimaxh3-director`：剧本分析、Beat 与镜头设计、素材规划、H3 工作流编排。
- `comfyui-h3-local-runner`：已建立项目的本地测试、续跑、下载、抽帧质检与选择性重试。

## 安装

克隆仓库：

```powershell
git clone https://github.com/ailaimi/minimax-h3-director-suite.git
```

把所需 Skill 目录复制到 Codex Skills 目录：

```powershell
Copy-Item -Recurse -Force .\minimax-h3-director-suite\skills\oh-my-minimaxh3-director "$env:USERPROFILE\.codex\skills\"
Copy-Item -Recurse -Force .\minimax-h3-director-suite\skills\comfyui-h3-local-runner "$env:USERPROFILE\.codex\skills\"
```

重新启动 Codex 后，可用自然语言或 `$oh-my-minimaxh3-director` 开始制作；已有导演工程可使用 `$comfyui-h3-local-runner` 继续执行。

## 推荐工作流

1. 分析剧情状态、信息切点、人物关系与连续空间。
2. 按真实导演节奏拆分 Beat 和镜头。
3. 检查人物、场景、服装、道具和身体状态冲突。
4. 先生成 storyboard、prompts、refs 与 director 数据。
5. 以低分辨率测试代表性 Beat，抽帧检查后再逐 Beat 推进。

## 目录

```text
skills/
  oh-my-minimaxh3-director/
  comfyui-h3-local-runner/
```

## 来源与许可证

`oh-my-minimaxh3-director` 来源于 TFboy1 的同名 MIT 项目，本仓库不是该上游仓库，也不代表其作者。原始版权和许可证完整保留在对应 Skill 目录中。

本仓库新增的整合文档与 `comfyui-h3-local-runner` 以 MIT 许可证发布。第三方组件及模型仍遵循各自许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 安全提示

提交前请检查工作流、日志和项目文件，避免把 API Key、访问令牌、本机账号路径或私人素材发布到公开仓库。
