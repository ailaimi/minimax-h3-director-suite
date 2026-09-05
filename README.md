# MiniMax H3 Director Suite

面向 Codex + ComfyUI 的 MiniMax H3 短剧导演与本地执行工具包。它负责把剧本整理成可执行的 Beat、镜头、素材与 H3 提示词，再通过已经验证过的 ComfyUI 工作流逐 Beat 测试、抽帧质检、续跑和下载。

仓库包含两个可独立安装的 Codex Skills：

- `oh-my-minimaxh3-director`：剧本分析、人物与空间关系、Beat/镜头拆分、素材冲突检查、提示词和工作流编排。
- `comfyui-h3-local-runner`：已有导演工程的本地预检、低分辨率测试、任务监控、下载、抽帧质检和选择性重试。

## 一、使用前需要准备什么

### 1. Codex

将两个 Skill 安装到 `%USERPROFILE%\.codex\skills\`，然后重启 Codex。

```powershell
git clone https://github.com/ailaimi/minimax-h3-director-suite.git
Set-Location .\minimax-h3-director-suite
Copy-Item -Recurse -Force .\skills\oh-my-minimaxh3-director "$env:USERPROFILE\.codex\skills\"
Copy-Item -Recurse -Force .\skills\comfyui-h3-local-runner "$env:USERPROFILE\.codex\skills\"
```

### 2. ComfyUI

可以使用本地 ComfyUI、AutoDL 或其他可访问的 ComfyUI 实例。默认本地地址为 `http://127.0.0.1:8188`。打开 `http://127.0.0.1:8188/system_stats`，能返回 JSON 即说明 API 可访问。

远程 ComfyUI 需要提供完整的 HTTPS 地址；若使用临时隧道，地址变化后必须重新探测。

### 3. MiniMax H3 模型

不同工作流需要的主模型不同。模型文件名必须与工作流 JSON 中配置的文件名一致。

| ComfyUI 目录 | 文件 | 用途 |
|---|---|---|
| `models/diffusion_models/` | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | Ref2VA 多参考图生成 |
| `models/diffusion_models/` | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | T2V/首帧/首尾帧生成 |
| `models/text_encoders/` | `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | H3 文本编码器 |
| `models/vae/` | `minimax_h3_video_vae_fp16.safetensors` | 视频 VAE |
| `models/vae/` | `minimax_h3_audio_vae_fp32.safetensors` | 音频 VAE |
| `models/loras/` | `minimax_h3_turbo_4step_ema_ckpt500.safetensors` | 内置 T2V 模板的 4 步 Turbo LoRA |
| 工作流指定目录 | `minimax_h3_turbo_v4_step600_ema.safetensors` | 内置 Ref2VA 模板引用的 Turbo 权重；按实际节点配置放置 |

模型来源可参考 [Comfy-Org/minimax-H3](https://www.modelscope.cn/models/Comfy-Org/minimax-H3)。量化模型也可以使用，但需要同步修改工作流中的模型文件名。

### 4. ComfyUI 节点

发行包内置模板会使用 H3 节点及若干常用辅助节点，例如：

- `MiniMaxH3ReferenceToVideo`
- `MiniMaxH3ImageToVideo`
- `MiniMaxH3TurboLoRA`、`MiniMaxH3TurboSampler`
- `ResolutionSelector`
- `SaveVideo`、`CreateVideo`
- `PathchSageAttentionKJ`
- `TESpeedMiniMaxH3`
- `LayerUtility: ImageScaleByAspectRatio V2`

不同 ComfyUI/H3 节点包版本的节点名称可能变化。最可靠的检查方式是：在 ComfyUI 中加载对应模板，查看红色缺失节点；通过 ComfyUI Manager 安装缺失节点包，重启 ComfyUI，再确认工作流能独立成功运行一次。不要在节点缺失时直接批量提交。

## 二、ComfyUI 具体要准备哪些工作流

建议准备下面三类工作流。至少要先让计划使用的类型在 ComfyUI 中成功运行一次。

| 项目模式 | 工作流文件 | 必要输入 | 适用场景 |
|---|---|---|---|
| Ref2VA | `ref2va.json` | 提示词 + 人物/场景/道具参考图 | 人物身份、服装或场景一致性优先的镜头 |
| T2V/T2VA | `t2v.json` | 提示词 | 不需要固定人物或关键物件的建立镜头、气氛镜头 |
| FL2VA/I2V | `i2v.json` | 提示词 + 首帧，可按工作流扩展末帧 | 精确控制开场构图；同一道具存在相反状态时优先用于首尾帧控制 |

内置模板位于：

```text
skills/oh-my-minimaxh3-director/assets/templates/
  ref2va.json
  t2v.json
  i2v.json
```

### 推荐：使用你已经跑通的工作流

内置模板只是兼容起点。若你已经在 ComfyUI 中跑通自己的 H3 工作流，应优先使用它，因为模型名称、自定义节点版本、显存优化和采样参数都已与你的环境匹配。

工作流必须导出为 **API Format JSON**，而不是只保存普通 UI 工作流。普通 UI JSON 通常包含顶层 `nodes` 和 `links`；API JSON 则以节点 ID 为键，每个节点包含 `class_type` 和 `inputs`。

导出步骤：

1. 在 ComfyUI 中打开并成功运行工作流。
2. 确认生成的视频和音频均正常。
3. 在 ComfyUI 菜单中选择 `Save (API Format)`；若没有该选项，在设置中开启开发者模式/API 保存功能。
4. 把导出的 JSON 放入项目的 `workflows/` 目录。
5. 为文件使用容易识别的名称，例如 `h3_ref2va_api.json`、`h3_t2v_api.json`、`h3_fl2va_api.json`。

若手上只有 UI 格式 JSON，可转换为 API 格式：

```powershell
python .\skills\oh-my-minimaxh3-director\scripts\convert_ui_workflow.py `
  <UI工作流.json> `
  --output <API工作流.json> `
  --object-info-url http://127.0.0.1:8188
```

转换后仍须在 ComfyUI 中验证一次。自定义节点版本不同会导致字段映射发生变化，转换成功不等于一定能够生成。

### 工作流放置位置

扫描器会检查以下位置：

```text
<项目目录>/workflows/
<项目目录>/templates/
<工作区根>/workflows/
<工作区根>/pv1min_workflows/
```

也可以在 `pipeline-config.json` 中使用 `templates_dir` 指定自己的工作流目录。

扫描命令：

```powershell
python .\skills\oh-my-minimaxh3-director\scripts\scan_workflows.py `
  --project <项目目录> `
  --workspace <工作区根>
```

扫描结果会标注工作流格式、推断模式、参考图槽位、Turbo 标记、模型文件和输出前缀。选择结果会写入 `storyboard.json` 的 `meta.workflow_map`，可以按模式统一指定，也可以按 Beat/段号单独指定。

```json
{
  "meta": {
    "workflow_map": {
      "ref2va": "workflows/h3_ref2va_api.json",
      "t2v": "workflows/h3_t2v_api.json",
      "3": "workflows/h3_fl2va_api.json"
    }
  }
}
```

优先级为：段内 `template` > 段号映射 > 模式映射 > 内置模板推断。

## 三、推荐项目目录

```text
我的短剧项目/
  source/
    剧本.md
  workflows/
    h3_ref2va_api.json
    h3_t2v_api.json
    h3_fl2va_api.json
  refs/
    characters/
    locations/
    props/
    beat-specific/
  storyboard.json
  prompts/
  director/
  jobs/
  outputs/
  qc/
```

关键要求：一张场景参考图只表达一个连续空间；关键道具或身体状态使用 Beat 专用完整构图；人物、背景人物和需要运动的物体在首尾帧中都要存在合理动作差异。

## 四、从剧本开始制作

在 Codex 中可以直接说：

```text
使用 $oh-my-minimaxh3-director，把 <剧本路径> 建立成完整短剧工程。
先分析剧情状态、信息切点、人物关系和空间关系；按真实导演节奏拆分 Beat 和镜头；
先生成 storyboard、prompts、refs 和 director 数据，不要立即批量生成视频。
```

导演阶段应依次完成：

1. 读取剧本，列出人物关系、说话对象、场景连接、道具和身体状态。
2. 按信息变化和表演动作拆 Beat，不使用固定 10 秒切段。
3. 建立镜头轴线、人物屏幕方向、视线、站位和空间地标。
4. 检查人物、场景、服装、道具、伤势和姿态是否互相冲突。
5. 生成角色、场景、道具及 Beat 专用参考图计划。
6. 保持对白原文、顺序和说话对象，写入 H3 提示词。
7. 为每个 Beat 选择 Ref2VA、T2V 或 FL2VA/I2V 工作流。
8. 输出 storyboard、prompts、refs 和 director 数据，等待执行确认。

## 五、第一次连接和验证 ComfyUI

在导演 Skill 目录中运行：

```powershell
python .\scripts\probe_comfy.py --workspace <工作区根> --write
python .\scripts\check_hardware.py
```

远程 ComfyUI：

```powershell
python .\scripts\probe_comfy.py --workspace <工作区根> --url https://<远程地址> --write
python .\scripts\check_hardware.py --remote-url https://<远程地址>
```

探测结果会写入工作区的 `.config/pipeline-config.json`。提交前要确认 `/system_stats` 与 `/object_info` 均可访问。

## 六、代表性 Beat 的低分辨率测试

不要首次就批量生成整集。先选择一个同时包含主要人物、典型空间、对白/表演和关键道具的代表性 Beat。

已建立并跑通过执行图后，使用本地 Runner：

```powershell
Set-Location "$env:USERPROFILE\.codex\skills\comfyui-h3-local-runner"

python .\scripts\h3_runner.py inspect --project <项目目录>
python .\scripts\h3_runner.py capture --project <项目目录> --prompt-id <ComfyUI成功任务ID>
python .\scripts\director_compiler.py --project <项目目录>
python .\scripts\coverage_audit.py --project <项目目录> --script <原始剧本路径>
python .\scripts\asset_audit.py --director-spec <director数据路径> --report <检查报告路径>
python .\scripts\h3_runner.py submit --project <项目目录> --director-spec <director数据路径> --scale 0.4 --label beat-01-test
python .\scripts\h3_runner.py status --project <项目目录> --download
```

`capture` 会冻结一个已经成功的 ComfyUI API 图，后续重试尽量复用这张图，避免节点 ID、字段和模型配置漂移。提交前先运行 `status`，不要在任务仍处于 pending/running 时重复提交。

通过 0.4MP 测试后，可根据显存和质量需求提高到 0.7MP，再逐 Beat 继续。分辨率由工作流的宽高比和百万像素选择器共同决定，不等同于固定的“720P”。

## 七、每次生成后的质检

每个 Beat 下载后都要抽取开头、中间、结尾帧，并检查：

- 人物：身份、脸、年龄、发型、服装是否稳定。
- 空间：是否仍是同一连续空间，轴线、左右位置和视线是否正确。
- 道具：数量、位置、持握关系以及前后状态是否符合剧情。
- 身体状态：站立/蹲伏、伤势、赤脚/穿鞋、袖口等是否连续。
- 表演：动作是否推动信息，首尾动作是否存在合理差异。
- 台词：原文、说话顺序、说话人和对象是否正确，口型/声音是否可接受。
- 连续性：前一 Beat 的末状态能否自然接到下一 Beat 的首状态。
- 画面污染：是否出现字幕、水印、无关文字、额外人物或相似道具。

单项失败只重做对应 Beat。连续两次出现同一缺陷时，应改变镜头结构、参考图或工作流模式，而不是只换随机种子。

## 八、常见问题

### `/prompt` 返回 `node_errors`

先阅读响应中的 `class_type` 和错误消息。通常是缺失节点、模型文件名不匹配、UI 工作流未转 API 格式，或节点字段与当前版本不一致。

### 报错涉及 `UNETLoader` 或 `CLIPLoader`

工作流中保存的模型文件名与本机实际名称不同。检查 `models/diffusion_models/` 和 `models/text_encoders/`，或通过 `/object_info/UNETLoader` 查看当前可选值，再修改模板。

### 参考图上传失败

确认文件存在；远程 ComfyUI 的 `LoadImage.image` 必须是远程 `input/` 下的相对路径。本套脚本会通过 `/upload/image` 上传并改写路径，不要把本机绝对路径直接写进远程工作流。

### 同一道具的相反状态互相污染

例如空杯/满杯、开门/关门、完整/破碎。优先使用明确的首帧与末帧；若仍泄漏，拆成两个片段，在手部遮挡、前景擦过、撞击或眨眼等合理遮挡点剪接。

### 台词必须完全精确

H3 原生对白是生成式的，必须逐条试听。若逐字、节奏或音色必须精确，应使用已确认的录音/TTS，并在后期完成配音、口型或字幕。

### 显存不足

先缩短时长、降低 MP、使用量化模型或 Turbo；本地不足时改用 24GB 以上云 GPU。建议系统内存 32GB 以上，并预留约 40GB 模型空间及视频输出空间。

## 九、更多文档

- [首次安装与模型说明](skills/oh-my-minimaxh3-director/references/setup-guide.md)
- [工作流路由和字段映射](skills/oh-my-minimaxh3-director/references/workflow-routing.md)
- [ComfyUI API 与错误排查](skills/oh-my-minimaxh3-director/references/api-and-mcp.md)
- [导演执行与质检规则](skills/comfyui-h3-local-runner/references/director-playbook.md)
- [Director v2 数据结构](skills/comfyui-h3-local-runner/references/director-schema-v2.md)

## 十、来源与许可证

`oh-my-minimaxh3-director` 来源于 TFboy1 的同名 MIT 项目。本仓库不是该上游仓库，也不代表其作者；原始版权、许可证和贡献者说明完整保留在对应 Skill 目录中。

本仓库新增的整合文档与 `comfyui-h3-local-runner` 以 MIT 许可证发布。MiniMax H3、ComfyUI、自定义节点、模型与可选剪辑工具仍遵循各自许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

公开项目前请再次检查工作流、日志和项目文件，避免提交 API Key、访问令牌、本机账号路径或私人素材。
