# 内容运营 Agent

作者：靳思嘉

从 Hacker News 热榜发现有传播潜力的选题，并生成经过人工确认的多平台内容包。

## 这是什么

内容运营 Agent 从 Hacker News 热榜发现有传播潜力的选题。

LLM 完成选题判断和多平台内容生成。

经过两道人工确认后输出内容包。

流程：`Hacker News 热榜采集 → 选题判断 → 人工选题确认 → 多平台内容生成 → 人工内容确认 → 输出内容包`

## 环境准备

建议使用 Python 虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

设置 LLM 服务所需的环境变量：

```bash
export LLM_API_KEY="your_api_key"
export LLM_BASE_URL="https://your-llm-base-url/v1"
```

## 运行方式

```bash
python scripts/run_content_agent.py
```

运行过程中会进行两次交互式确认：

- 选题确认：输入要保留的选题编号。
- 内容确认：对生成的平台内容输入 `y` 通过、`n` 丢弃，或输入 `e` 编辑/查看后再确认。

## 项目结构

```text
collectors/hackernews.py       # 采集 Hacker News 热榜和原始来源
intelligence/prompts.py        # LLM 任务提示词
intelligence/llm_client.py     # LLM API 客户端
publishing/                    # 内容整理和输出文件生成
scripts/run_content_agent.py   # Agent 运行入口
config/settings.yaml           # 项目配置
output/                        # 运行生成的内容和中间结果
```

## 输出文件说明

`output/` 目录中的主要文件：

- `latest-content.json`：最新一次运行的结构化内容包，供程序或 Demo 引用。
- `latest-workbench.html`：最新一次运行的 HTML 内容工作台，可直接在浏览器查看。
- `latest-workbench.md`：最新一次运行的 Markdown 内容工作台，便于阅读和版本管理。
- `content-package-YYYY-MM-DD.json`：按日期保存的结构化内容包归档。
- `content-workbench-YYYY-MM-DD.md`：按日期保存的 Markdown 工作台归档。
- `llm-response-*`：LLM 调用产生的原始响应和解析结果，便于排查单次运行内容。

`latest-*` 使用固定文件名，方便 `demo.html` 和其他外部引用始终指向最近一次运行结果。
