# AI账单分析助手

一个可直接部署到 GitHub 的演示项目，适合展示“AI 驱动的数据清洗 + 账单分析 + 可视化”能力。

## 功能
- 上传 CSV 账单文件
- 自动清洗字段并归类支出
- 生成月度趋势图、分类占比图、Top 商户图
- 输出 AI 风格的账单总结
- 支持导出清洗后的 CSV
- 可选接入 OpenAI API，增强总结能力

## CSV 字段
至少需要：

- `date`
- `merchant`
- `amount`

可选：

- `category`
- `note`

金额建议：
- 支出用负数
- 收入用正数

## 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 可选 AI 能力
配置环境变量：

```bash
export OPENAI_API_KEY="你的key"
export OPENAI_MODEL="gpt-4o-mini"
```

然后重新启动应用。

## 适合提交的项目描述
这是一个面向个人财务分析的轻量级 AI 应用。它能自动清洗混乱账单数据、识别退款记录、聚合消费分类，并生成可视化报表与摘要结论，帮助用户快速理解消费结构和优化预算。