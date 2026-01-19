# 文本处理工具集

用于处理各种文本格式的 Python 工具集，支持 SRT 字幕、直播文稿的处理，包括格式转换、文本清洗、分段和摘要生成。

## 核心功能

- 🆕 **SRT 字幕处理** - 提取纯文本、保留时间范围、时间范围切片
- 🆕 **多格式支持** - SRT 字幕、时间戳格式、纯文本自动检测
- **文稿清洗** - 调用 LLM 去除口语化表达，规范文本
- **摘要生成** - 双阶段自动摘要，提取内容要点
- **智能分段** - 按空格数量自动分段，保留时间信息
- **断点续传** - 支持中断后继续处理

## 项目结构

```
Text-Processing/
├── src/                                          # 源代码目录
│   ├── preprocessor.py                           # 通用文本处理器（支持 SRT/时间戳/纯文本）
│   ├── transcript_processor.py                   # 文稿清洗处理器
│   ├── summary_processor.py                      # 摘要处理器
│   ├── progress_utils.py                         # 进度管理工具（断点续传）
│   ├── api_utils.py                              # API 调用工具
│   ├── config_utils.py                           # 配置加载工具
│   └── streaming_processor.py                    # 流式处理核心模块
├── config/                                       # 配置文件目录
│   ├── api_key.txt                              # DeepSeek API Key
│   ├── transcript_prompt.md                     # 文稿清洗提示词
│   ├── summary_prompt.md                        # 段落摘要提示词
│   └── merge_prompt.md                          # 摘要合并提示词
├── input/                                        # 输入文件目录（推荐手动创建）
├── output/                                       # 输出文件目录（推荐手动创建，首次运行会自动创建）
├── requirements.txt                              # Python 依赖
└── README.md                                     # 项目说明
```

## 功能特性

| 脚本 | 功能 | 输入格式支持 | API 调用 |
|------|------|-------------|---------|
| `preprocessor.py` | 通用文本处理器 | SRT/时间戳/纯文本 | 否 |
| `transcript_processor.py` | 文稿清洗处理器 | SRT/时间戳/纯文本 | 是 |
| `summary_processor.py` | 摘要处理器 | SRT/时间戳/纯文本 | 是 |

## 安装

### 1. 环境要求
- Python 3.x

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

**依赖列表：**
- `openai>=1.0.0` - DeepSeek API 调用
- `pysrt>=1.1.2` - SRT 字幕文件解析

### 3. 创建目录（推荐）

建议手动创建输入和输出目录，以便更好地组织文件：

```bash
# 创建输入目录（放置待处理的文件）
mkdir input

# 创建输出目录（存放处理结果）
mkdir output
```

**注意：** 首次运行需要 API 的脚本时，如果 `output/` 目录不存在，程序会自动创建。

### 4. 配置 API Key

如果需要使用 API 调用功能（如 `transcript_processor.py` 或 `summary_processor.py`），需要配置 DeepSeek API key。

#### 方式一：交互式初始化（推荐）

首次运行需要 API 的脚本时，程序会自动检测并提示你输入 API key，同时确保 output 文件夹存在：

```bash
python src/transcript_processor.py input/subtitles.srt
```

如果 `config/api_key.txt` 不存在，会显示首次运行初始化界面：

```
============================================================
[INIT] StreamScribe-AI 首次运行初始化
[INIT] First-time setup for StreamScribe-AI
============================================================

[SETUP] 首次使用需要设置 DeepSeek API Key
[SETUP] First time setup: DeepSeek API Key required
   获取地址 Get your key: https://api-docs.deepseek.com.zh-cn/

请输入你的 API Key / Enter your API Key: _
```

输入完成后，程序会自动：
1. 创建 `config/` 目录并保存 API key
2. 创建 `output/` 目录（如果不存在）
3. 显示初始化完成提示

#### 方式二：手动配置

直接在 `config/api_key.txt` 中填入你的 DeepSeek API key：

```
# DeepSeek API Key
# 获取地址: https://api-docs.deepseek.com.zh-cn/
sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

#### 获取 API Key

访问 [DeepSeek API 文档](https://api-docs.deepseek.com.zh-cn/) 注册并获取你的 API key。

## 使用方法

### 一、通用文本处理器（preprocessor.py）🆕

自动检测文件格式并处理，支持 SRT 字幕、时间戳格式和纯文本。

#### 支持的处理模式

| 模式 | 说明 | 适用格式 |
|------|------|---------|
| `plain` | 提取纯文本，去除所有时间戳 | 全部格式 |
| `with-time` | 保留时间范围分段 | 全部格式 |
| `slice` | 时间范围切片 | 仅 SRT 格式 |

#### 使用示例

```bash
# 显示帮助信息
python src/preprocessor.py --help

# === SRT 字幕处理 ===

# 提取纯文本
python src/preprocessor.py input/subtitles.srt --mode plain

# 保留时间范围分段（默认每段 50-60 个空格）
python src/preprocessor.py input/subtitles.srt --mode with-time

# 自定义分段参数
python src/preprocessor.py input/subtitles.srt --mode with-time --min 40 --max 50

# 时间范围切片（提取 2分钟到 5分钟的字幕）
python src/preprocessor.py input/subtitles.srt --mode slice --start 2m --end 5m

# === 时间戳格式文件处理 ===

python src/preprocessor.py input/transcript.txt --mode with-time

# === 纯文本文件处理 ===

python src/preprocessor.py input/plain.txt --mode with-time --min 40 --max 50
```

#### 支持的输入格式

**SRT 字幕格式：**
```
1
00:00:00,690 --> 00:00:04,130
字幕文本内容

2
00:00:04,810 --> 00:00:07,490
下一条字幕
```

**时间戳格式：**
```
[0.5s --> 2.3s] 文本内容
```

**纯文本格式：**
```
纯文本内容
```

#### 时间格式支持（用于 --start/--end 参数）

| 格式 | 说明 | 示例 |
|------|------|------|
| `SS` | 纯秒数 | `90` |
| `MM:SS` | 分:秒 | `2:30` |
| `HH:MM:SS,mmm` | SRT 格式 | `00:02:30,500` |
| `MMm` | 分钟 | `2m` |
| `SSs` | 秒 | `30s` |

#### 输出文件

| 模式 | 输出文件名 | 内容说明 |
|------|-----------|----------|
| `plain` | `{filename}_plain.txt` | 纯文本内容 |
| `with-time` | `{filename}_with_time.txt` | 带时间范围的分段 |
| `slice` | `{filename}_slice.txt` | 时间范围内字幕 |

#### 输出格式示例

**with-time 模式：**
```
============================================================
段落 1
============================================================
【0.7秒 - 1分16.3秒】
字幕文本内容...
```

**slice 模式：**
```
============================================================
字幕切片
============================================================
时间范围: 【2分0.0秒 - 5分0.0秒】
原始范围: 2m --> 5m

============================================================
内容
============================================================

【2分1.5秒 - 2分4.4秒】
字幕内容

【2分4.5秒 - 2分7.5秒】
字幕内容
...
```

---

### 二、文稿清洗处理器（transcript_processor.py）

自动检测格式，去除时间戳、分段后调用 DeepSeek API 进行文稿清洗。

#### 支持的输入格式

- SRT 字幕文件（`.srt`）
- 时间戳格式（`.txt`）
- 纯文本（`.txt`）

#### 运行命令

```bash
# 处理 SRT 字幕文件
python src/transcript_processor.py input/subtitles.srt

# 处理时间戳格式文件
python src/transcript_processor.py input/transcript.txt

# 处理纯文本文件
python src/transcript_processor.py input/plain.txt

# 自定义分段参数（默认每段 50-60 个空格）
python src/transcript_processor.py input/transcript.txt 40 50
```

#### 输出文件

- `output/{filename}_processed.md` - 清洗后的文稿

#### 特性

- ✅ 自动格式检测（支持 SRT）
- ✅ 流式写入，实时保存
- ✅ 显式进度标记，可靠的断点续传
- ✅ 错误自动重试（最多 3 次）

---

### 三、摘要处理器（summary_processor.py）

双阶段摘要处理，自动检测格式，生成结构化摘要。

#### 支持的输入格式

- SRT 字幕文件（`.srt`）
- 时间戳格式（`.txt`）
- 纯文本（`.txt`）

#### 运行命令

```bash
# 处理 SRT 字幕文件
python src/summary_processor.py input/subtitles.srt

# 处理带时间戳的文稿
python src/summary_processor.py input/transcript.txt

# 处理纯文本文稿
python src/summary_processor.py input/plain_text.txt

# 自定义分段参数
python src/summary_processor.py input/transcript.txt 40 50
```

#### 输出文件

- `output/{filename}_segment_summaries.md` - 各时段/段落摘要
- `output/{filename}_final_summary.md` - 最终全文摘要

#### 处理流程

```
输入文件
  ↓
格式检测（SRT/时间戳/纯文本）
  ↓
自适应分段
  ↓
阶段一：各段落摘要（流式写入）
  ↓
阶段二：合并生成最终摘要
```

#### 特性

- ✅ 自动格式检测（支持 SRT）
- ✅ 时间信息保留（SRT/时间戳格式）
- ✅ 双阶段摘要处理
- ✅ 显式进度标记，可靠的断点续传

---

## 分段参数说明

脚本支持自定义分段参数来控制每段的大小：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `min_spaces` | 每段最少空格数 | 50 |
| `max_spaces` | 每段最多空格数 | 60 |

**调整建议：**
- 输入文本较短 → 减小参数（如 30-40）
- 输入文本较长 → 增大参数（如 80-100）
- API 处理不稳定 → 减小参数

## 常见问题

### Q: 如何选择使用哪个脚本？

**A: 根据需求选择：**

| 需求 | 推荐脚本 |
|------|---------|
| 处理 SRT 字幕文件 | `preprocessor.py` |
| 预处理文本（分段、去时间戳） | `preprocessor.py` |
| 需要清洗文稿，去除口语化表达 | `transcript_processor.py` |
| 需要生成摘要，了解内容概要 | `summary_processor.py` |

### Q: preprocessor.py 和其他脚本的区别？

- `preprocessor.py`：通用处理器，支持多种格式（包括 SRT），无需 API，适合快速预处理
- 其他脚本：专门针对特定用途，如文稿清洗、摘要生成等，可能需要 API 调用

### Q: 断点续传如何工作？

**A:** 脚本使用显式进度标记机制实现可靠的断点续传：

- 输出文件末尾会写入进度标记：`<!-- PROCESSING: segment=N/TOTAL, status=processing -->`
- 处理中断后再次运行，脚本会读取标记并从断点继续
- 支持多种状态：`processing`（处理中）、`complete`（完成）、`failed`（失败）
- 每处理完一个段落立即写入文件并 flush，确保数据安全
- 向后兼容旧版本文件（无标记时使用估算方法）

### Q: 支持哪些输入格式？

**A:**
- `preprocessor.py`：SRT 字幕（`.srt`）、SRT 时间戳格式（`.txt`）、标准时间戳格式、纯文本
- `transcript_processor.py`：SRT 字幕（`.srt`）、时间戳格式、纯文本
- `summary_processor.py`：SRT 字幕（`.srt`）、时间戳格式、纯文本

### Q: API 调用失败怎么办？

**A:** 脚本内置了自动重试机制（最多 3 次，指数退避）。如果仍然失败，请检查：
1. **API key 配置**：首次运行会自动提示输入，或手动配置到 `config/api_key.txt`
2. 网络连接是否正常
3. DeepSeek API 服务是否可用
4. API key 是否有效（前往 [DeepSeek 控制台](https://api-docs.deepseek.com/zh-cn/) 检查）

### Q: 交互式初始化的工作原理？

**A:** 首次运行需要 API 的脚本时（`transcript_processor.py` 或 `summary_processor.py`）：

1. 程序检测 `config/api_key.txt` 是否存在
2. 如果不存在，显示首次运行初始化界面
3. 引导用户输入 API key（支持空值检测）
4. 自动创建 `config/` 目录并保存 API key
5. 自动创建 `output/` 目录（如果不存在）
6. 后续运行直接读取配置，无需重复输入

**目录创建逻辑：**
- `config/`：仅在首次运行时创建
- `output/`：每次运行时都会确保存在（如果被删除会自动重建）

如需禁用交互模式（如自动化脚本），可调用 `initialize_project_setup(key_path, output_path, interactive=False)`。

---

## 许可

MIT License
