---
name: liblibai-mcp-server
description: 当用户希望通过 LiblibAI MCP 服务端生成图片或视频时使用此技能。它用于指导模型选择正确的 LiblibAI 工具、理解每个工具的用途、组织输入参数、处理本地文件上传、查询任务状态，并同时保留线上地址和本地结果路径。
---

# LiblibAI MCP 使用指南

当用户希望通过 LiblibAI MCP 服务端生成图片或视频时，使用此技能。

这个技能的目标不是指导部署服务端，而是指导如何使用已经可用的 LiblibAI MCP 工具。

## 适用场景

适用于以下任务：

- 文生图
- 图生图
- 指令编辑
- 局部重绘
- 文生视频
- 图生视频
- 多图参考视频生成
- 多模态视频生成
- 上传本地图片或视频并生成可用的线上地址
- 查询生成任务状态
- 下载生成结果，同时保留线上 URL

## 使用原则

1. 优先使用语义最明确的专用工具，不要一上来就用通用工具。
2. 只有当专用工具缺少某些高级参数时，才使用 `submit_generation`。
3. 如果输入是本地文件路径，直接传路径；服务端会自动上传并替换成 Liblib 可访问的 URL。
4. 查询结果时要同时保留：
   - 远程地址
   - 本地下载路径
5. 图片和视频生成通常是异步任务：
   - 先提交任务
   - 再查状态
   - 或直接轮询直到完成

## 推荐调用顺序

大多数任务按这个顺序处理：

1. 选择合适的生成工具并提交任务
2. 记录返回的 `generate_uuid`
3. 使用 `poll_generation` 等待完成
4. 或使用 `get_generation_status` 做一次性查询
5. 读取结果中的：
   - 图片 `remote_url` / `local_path`
   - 视频 `remote_url` / `local_path`
   - 封面 `cover_url` / `cover_local_path`

## 工具总览

### 1. `server_info`

用途：

- 查看当前 MCP 服务的基础信息

适合场景：

- 想确认输出目录、MCP 路径、默认下载策略

---

### 2. `upload_file`

用途：

- 将本地图片或视频上传到 Liblib
- 返回可公网访问的在线地址

适合场景：

- 用户明确只想先拿到线上地址
- 需要把本地文件先上传，再手动用于其他请求
- 需要确认上传是否成功

输入说明：

- `local_path`：本地文件路径
- `copy_to_output`：是否额外复制到输出目录

输出重点：

- `online_url`
- `postUrl`
- `key`

---

### 3. `submit_generation`

用途：

- 通用提交工具
- 适用于任意 Liblib 接口
- 可直接传原始 `endpoint`、`template_uuid` 和 `generate_params`

适合场景：

- 专用工具不支持你想传的高级参数
- 需要调用新增接口
- 需要完全按官方文档拼原始参数

使用建议：

- 优先先用专用工具
- 只有专用工具不够时再回退到这个工具

---

## 图像工具

### 4. `star3_text_to_image`

用途：

- 星流 Star-3 Alpha 文生图

适合场景：

- 需要快速生成高质量图片
- 不想手动配置大量专业参数
- 常见人物、插画、视觉图生成

常用输入：

- `prompt`
- `aspect_ratio`
- `image_size`
- `img_count`
- `steps`
- `controlnet`

默认思路：

- 普通场景直接传 `prompt`
- 人像优先用 `portrait`
- 通用图可用 `square`

---

### 5. `star3_image_to_image`

用途：

- 星流 Star-3 Alpha 图生图

适合场景：

- 有参考图，想在原图基础上改造
- 想用构图控制或风格参考

常用输入：

- `prompt`
- `source_image`
- `img_count`
- `controlnet`

说明：

- `source_image` 可以是本地路径，也可以是在线 URL
- 本地路径会自动上传

---

### 6. `qwen_text_to_image`

用途：

- Qwen Image 文生图

适合场景：

- 需要更细的常规图像生成参数
- 想显式控制 `width`、`height`、`steps`、`cfgScale`、`seed`

常用输入：

- `prompt`
- `negative_prompt`
- `width`
- `height`
- `img_count`
- `steps`
- `cfg_scale`
- `seed`

适用建议：

- 需要更细尺寸控制时优先考虑这个工具

---

### 7. `kontext_text_to_image`

用途：

- F.1 Kontext 文生图

适合场景：

- 需要 Kontext 模型能力
- 想在 `pro` 和 `max` 间切换

常用输入：

- `prompt`
- `model`
- `aspect_ratio`
- `img_count`
- `guidance_scale`

---

### 8. `kontext_image_to_image`

用途：

- F.1 Kontext 图生图 / 多图参考

适合场景：

- 指令编辑
- 多张图片联合参考
- 强调参考图之间关系

常用输入：

- `prompt`
- `input_images`
- `model`
- `guidance_scale`

说明：

- `input_images` 可传本地路径列表或在线 URL 列表

---

### 9. `img1_generate`

用途：

- 智能算法 IMG1 生图

适合场景：

- 需要参考图列表
- 希望使用 IMG1 相关能力

常用输入：

- `prompt`
- `image_list`
- `style`
- `aspect_ratio`

---

### 10. `img1_inpaint`

用途：

- 智能算法 IMG1 局部重绘

适合场景：

- 已有原图和蒙版图
- 只想改局部区域

常用输入：

- `prompt`
- `source_image`
- `mask_image`

说明：

- `source_image` 和 `mask_image` 都可以直接传本地文件路径

---

### 11. `libdream_text_to_image`

用途：

- LibDream 文生图

适合场景：

- 偏中文理解、海报风格、创意图生成

常用输入：

- `prompt`
- `aspect_ratio`
- `img_count`
- `guidance_scale`
- `seed`

---

### 12. `libedit_image_edit`

用途：

- LibEdit 指令编辑

适合场景：

- 已有图片，想通过自然语言修改
- 可带额外参考图辅助编辑

常用输入：

- `prompt`
- `source_image`
- `reference_images`

说明：

- `source_image` 可为本地路径
- `reference_images` 可传多张本地图片

---

## 视频工具

### 13. `kling_text_to_video`

用途：

- Kling 文生视频

适合场景：

- 纯文本生成视频
- 不依赖首帧或参考图

常用输入：

- `prompt`
- `model`
- `aspect_ratio`
- `duration`
- `mode`
- `prompt_magic`
- `sound`

使用建议：

- 一般先从默认参数开始
- 如果用户明确追求质量，再考虑 `mode="pro"`

---

### 14. `kling_image_to_video`

用途：

- Kling 图生视频

适合场景：

- 以一张图或首尾帧生成视频

常见输入模式：

1. `image`
   - 适合部分新模型
2. `start_frame`
   - 首帧生成
3. `start_frame + end_frame`
   - 首尾帧生成

常用输入：

- `prompt`
- `image`
- `start_frame`
- `end_frame`
- `model`
- `duration`
- `mode`
- `sound`

注意事项：

- 含尾帧时，通常需要 `mode="pro"`
- 本地图片路径可直接传入

---

### 15. `kling_multi_image_to_video`

用途：

- Kling 多图参考视频生成

适合场景：

- 多张参考图共同决定场景、人物、风格

常用输入：

- `prompt`
- `reference_images`
- `model`
- `aspect_ratio`
- `duration`
- `mode`

说明：

- `reference_images` 支持本地路径列表

---

### 16. `kling_omni_video`

用途：

- Kling Omni-Video V1 多模态视频生成/编辑

适合场景：

- 混合使用图片、视频、文字
- 视频编辑
- 多模态参考生成

常用输入：

- `prompt`
- `images`
- `videos`
- `model`
- `aspect_ratio`
- `duration`
- `mode`

说明：

- `images` 里通常是对象数组，如：
  - `image_url`
  - `type`
- `videos` 里通常是对象数组，如：
  - `video_url`
  - `refer_type`
  - `keep_original_sound`

这是视频能力里最灵活的工具之一。

---

## 任务状态与结果工具

### 17. `get_generation_status`

用途：

- 查询一次任务当前状态

适合场景：

- 用户只想看当前进度
- 你想手动控制轮询
- 不希望当前请求长时间阻塞

常用输入：

- `generate_uuid`
- `status_endpoint`
- `download_results`

什么时候用：

- 已有任务 ID，只想看当前状态
- 前端或调用方自己负责后续轮询

---

### 18. `poll_generation`

用途：

- 持续轮询直到任务结束
- 可在完成后自动下载结果

适合场景：

- 用户希望“一次拿到最终结果”
- 希望结果文件直接落到本地目录
- 想同时保留远程地址和本地路径

常用输入：

- `generate_uuid`
- `status_endpoint`
- `poll_interval_seconds`
- `timeout_seconds`
- `download_results`

推荐：

- 一般优先用这个工具拿最终结果

---

## 状态接口怎么选

不同接口对应不同状态查询地址，不要混用。

- Star-3 ultra：
  - `/api/generate/webui/status`
- Qwen / Kontext / IMG1 / LibDream / LibEdit / Kling：
  - `/api/generate/status`
- ComfyUI：
  - `/api/generate/comfy/status`

如果使用的是专用工具，通常直接沿用工具默认值即可。
如果使用 `submit_generation`，要自己传对 `status_endpoint`。

## 本地文件使用规则

以下字段可以直接传本地文件路径，服务端会自动上传：

- `sourceImage`
- `controlImage`
- `maskImage`
- `image`
- `imageUrl`
- `startFrame`
- `endFrame`
- `image_url`
- `video_url`
- `referenceImages`
- `image_list`
- `input_images`

如果已经有可公网访问的 URL，直接传 URL 即可，不需要重复上传。

## 结果读取规则

图片结果重点看：

- `images[].remote_url`
- `images[].local_path`

视频结果重点看：

- `videos[].remote_url`
- `videos[].local_path`
- `videos[].cover_url`
- `videos[].cover_local_path`

要求：

- 即使已经下载到本地，也必须保留线上 URL
- 不要只返回本地路径而丢失远程地址

## 典型选择建议

### 用户说“帮我生成一张图片”

优先考虑：

- `star3_text_to_image`
- `qwen_text_to_image`
- `libdream_text_to_image`

### 用户说“拿这张图改一下”

优先考虑：

- `star3_image_to_image`
- `libedit_image_edit`
- `kontext_image_to_image`

### 用户说“局部改这张图”

优先考虑：

- `img1_inpaint`

### 用户说“生成一个视频”

优先考虑：

- `kling_text_to_video`

### 用户说“根据这张图生成视频”

优先考虑：

- `kling_image_to_video`

### 用户说“多张图综合参考做视频”

优先考虑：

- `kling_multi_image_to_video`
- `kling_omni_video`

### 用户说“我要传很复杂的官方参数”

优先考虑：

- `submit_generation`

## 工作方式要求

- 优先使用最贴近用户意图的专用工具
- 除非必要，不要把简单任务复杂化
- 高级参数默认保持可选
- 本地输入自动上传时，要清楚告知最终会保留线上地址
- 返回结果时，不要遗漏 `generate_uuid`
- 如果任务是异步的，不要把“提交任务”和“最终结果”混为一谈
