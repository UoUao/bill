import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="AI账单分析助手", page_icon="🧾", layout="wide")

CATEGORY_RULES = {
    "餐饮": ["food", "restaurant", "coffee", "cafe", "mcdonald", "kfc", "星巴克", "瑞幸", "外卖", "饭", "餐"],
    "交通": ["didi", "uber", "taxi", "metro", "bus", "地铁", "打车", "高铁", "火车", "机票", "油费", "停车"],
    "购物": ["mall", "amazon", "taobao", "tmall", "jd", "拼多多", "超市", "商店", "服饰", "衣服", "鞋", "水果"],
    "居家": ["rent", "lease", "物业", "水电", "燃气", "网费", "家具", "家居", "房租"],
    "娱乐": ["netflix", "spotify", "steam", "游戏", "电影", "演出", "门票", "会员"],
    "医疗": ["hospital", "clinic", "药房", "医生", "药"],
    "转账": ["transfer", "bank", "支付宝转账", "微信转账", "退款", "退货"],
}

SAMPLE_DATA = pd.DataFrame(
    [
        ["2026-04-01", "星巴克", "餐饮", -28.0, "早咖啡"],
        ["2026-04-01", "地铁", "交通", -4.0, "通勤"],
        ["2026-04-02", "京东", "购物", -239.0, "日用品"],
        ["2026-04-03", "美团外卖", "餐饮", -46.5, "午餐"],
        ["2026-04-05", "房租", "居家", -2800.0, "月租"],
        ["2026-04-06", "滴滴出行", "交通", -18.2, "晚高峰"],
        ["2026-04-08", "超市", "购物", -126.8, "补货"],
        ["2026-04-10", "网易云音乐", "娱乐", -15.0, "会员"],
        ["2026-04-12", "医院药房", "医疗", -68.4, "感冒药"],
        ["2026-04-15", "退款-京东", "转账", 59.0, "退货退款"],
        ["2026-04-18", "电影票", "娱乐", -78.0, "周末娱乐"],
        ["2026-04-20", "燃气", "居家", -132.0, "月结"],
        ["2026-04-22", "麦当劳", "餐饮", -36.0, "晚餐"],
        ["2026-04-24", "高铁", "交通", -128.0, "出差"],
        ["2026-04-26", "水果店", "购物", -52.0, "水果"],
    ],
    columns=["date", "merchant", "category", "amount", "note"],
)

def normalize_category(text: str) -> str:
    t = str(text).lower()
    for cat, keys in CATEGORY_RULES.items():
        for k in keys:
            if k.lower() in t:
                return cat
    return "其他"

def load_data(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        df = SAMPLE_DATA.copy()
    else:
        df = pd.read_csv(uploaded_file)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"date", "merchant", "amount"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"缺少字段：{', '.join(sorted(missing))}。至少需要 date, merchant, amount。")
        st.stop()

    if "category" not in df.columns:
        df["category"] = ""

    if "note" not in df.columns:
        df["note"] = ""

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["merchant"] = df["merchant"].astype(str).str.strip()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "merchant", "amount"]).copy()

    cleaned_category = df["category"].fillna("").astype(str).str.strip()
    df["clean_category"] = cleaned_category.where(cleaned_category != "", df["merchant"].apply(normalize_category))
    df["clean_category"] = df["clean_category"].apply(lambda x: x if x in list(CATEGORY_RULES.keys()) + ["其他"] else normalize_category(x))

    df["signed_amount"] = df["amount"].astype(float)
    df["type"] = df["signed_amount"].apply(lambda x: "收入" if x > 0 else "支出")
    df["abs_amount"] = df["signed_amount"].abs()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df.sort_values("date")

def ai_summary(df: pd.DataFrame) -> str:
    spend = df.loc[df["signed_amount"] < 0, "abs_amount"].sum()
    income = df.loc[df["signed_amount"] > 0, "signed_amount"].sum()
    top_cat = (
        df.loc[df["signed_amount"] < 0]
        .groupby("clean_category")["abs_amount"]
        .sum()
        .sort_values(ascending=False)
    )
    top_cat_name = top_cat.index[0] if not top_cat.empty else "暂无"
    top_cat_amt = float(top_cat.iloc[0]) if not top_cat.empty else 0.0
    refund_count = int(df["merchant"].str.contains("退款|退货", case=False, regex=True).sum())

    prompt = f"""
你是一个个人财务分析助手。请用中文输出 3 句以内的简洁分析，并给出 1 条优化建议。
数据摘要：
- 总收入：{income:.2f}
- 总支出：{spend:.2f}
- 最大支出类别：{top_cat_name}，金额 {top_cat_amt:.2f}
- 退款/退货记录数：{refund_count}
要求：语气专业、简洁、适合放在产品演示页面。
"""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                input=prompt,
            )
            txt = resp.output_text.strip()
            if txt:
                return txt
        except Exception as e:
            return f"AI 摘要生成失败，已使用本地规则结果。原因：{e}"

    return (
        f"本月总收入 {income:.2f} 元，总支出 {spend:.2f} 元。"
        f"支出最高的类别是 {top_cat_name}（{top_cat_amt:.2f} 元）。"
        f"{'检测到退款或退货记录，已单独识别。' if refund_count else '未检测到明显退款记录。'}"
        f"建议优先压缩高频支出类别，先从 {top_cat_name} 开始优化。"
    )

st.title("🧾 AI账单分析助手")
st.caption("上传账单 CSV，自动清洗分类、生成统计图，并输出可用于演示的 AI 分析。")

with st.sidebar:
    st.header("输入")
    uploaded = st.file_uploader("上传账单 CSV", type=["csv"])
    st.markdown("**字段要求**：date, merchant, amount；可选 category, note")
    st.markdown("**示例**：date=2026-04-01, merchant=星巴克, amount=-28")
    st.divider()
    use_sample = st.checkbox("使用内置示例数据", value=(uploaded is None))
    st.info("如需更像 AI，可设置环境变量 OPENAI_API_KEY。")

df = load_data(None if use_sample or uploaded is None else uploaded)

col1, col2, col3, col4 = st.columns(4)
total_spend = df.loc[df["signed_amount"] < 0, "abs_amount"].sum()
total_income = df.loc[df["signed_amount"] > 0, "signed_amount"].sum()
txn_count = len(df)
refund_count = int(df["merchant"].str.contains("退款|退货", case=False, regex=True).sum())

col1.metric("交易笔数", f"{txn_count}")
col2.metric("总收入", f"{total_income:.2f}")
col3.metric("总支出", f"{total_spend:.2f}")
col4.metric("退款/退货", f"{refund_count}")

ai_text = ai_summary(df)
st.subheader("AI 账单解读")
st.write(ai_text)

left, right = st.columns([1.1, 0.9])

with left:
    st.subheader("月度趋势")
    monthly = df.groupby("month", as_index=False)["signed_amount"].sum()
    fig1 = px.line(monthly, x="month", y="signed_amount", markers=True, title="每月净收支")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("分类占比")
    spend_df = df[df["signed_amount"] < 0].groupby("clean_category", as_index=False)["abs_amount"].sum()
    if not spend_df.empty:
        fig2 = px.pie(spend_df, values="abs_amount", names="clean_category", title="支出分类占比")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("暂无支出数据")

with right:
    st.subheader("高频商户")
    top_merchants = (
        df[df["signed_amount"] < 0]
        .groupby("merchant", as_index=False)["abs_amount"]
        .sum()
        .sort_values("abs_amount", ascending=False)
        .head(10)
    )
    if not top_merchants.empty:
        fig3 = px.bar(top_merchants, x="abs_amount", y="merchant", orientation="h", title="Top 10 支出商户")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("清洗结果预览")
    preview_cols = ["date", "merchant", "category", "clean_category", "amount", "note"]
    st.dataframe(df[preview_cols].head(20), use_container_width=True)

st.subheader("导出")
csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("下载清洗后的 CSV", csv_bytes, "cleaned_bill.csv", "text/csv")

st.caption("提示：这是一个可直接部署到 GitHub 的演示项目。默认不依赖外部 API，设置 OPENAI_API_KEY 后可启用更强的 AI 摘要能力。")