# 游戏术语提取工具

## 快速启动

```bash
# 双击 run.bat（首次自动安装环境）
# 或手动：
pip install -r requirements.txt
streamlit run ui/app.py
```

## 目录结构

```
├── core/               # 核心流水线
│   ├── main.py         # 流水线编排
│   ├── llm_extractor.py   # LLM 术语提取 (3轮投票)
│   ├── llm_translator.py  # LLM 术语翻译
│   ├── prompt_base.py     # Prompt 构造
│   ├── embed_store.py     # text-embedding-3-large 向量库
│   ├── header_detect.py   # AI 表头自动识别
│   ├── checkpoint.py      # 断点续跑
│   └── logger.py
├── ui/                 # Web 前端 (Streamlit)
│   ├── app.py          # UI 入口
│   └── ui_backend.py   # UI 适配层
├── scripts/            # CLI 工具
│   └── eval.py
├── profiles/           # 项目配置 (YAML)
├── config.py           # 引擎参数
├── config_template.py  # 配置模板
├── requirements.txt
├── run.bat             # Windows 一键启动
└── setup.bat           # 自动安装 Python 环境
```

## 数据流

```
source.xlsx + glossary.xlsx
  → 表头自动识别 (规则 + AI)
  → LLM 术语提取 (NER 预扫 + 3轮投票)
  → 嵌入匹配 (text-embedding-3-large)
  → LLM 翻译
  → 结果预览 + xlsx 下载
```

## 添加项目配置

1. 上传已有 profile YAML 或下载模板填写
2. 在「设置 → 高级设置」中上传
3. 切换配置即可使用
