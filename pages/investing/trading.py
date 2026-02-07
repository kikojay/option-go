"""交易日志页面 — 买卖记录 · 期权操作 · 手续费"""
import streamlit as st
from datetime import datetime

from ui import UI
from services import TradingService
from config import TRADE_ACTION_OPTIONS
from api.stock_names import get_stock_label as stock_label
import db


def render():
    UI.inject_css()
    UI.header("交易日志", "买卖记录 · 期权操作 · 手续费")

    usd_rmb = st.session_state.usd_rmb

    # 添加交易表单
    _add_trade_form()

    # 数据
    df = TradingService.load(usd_rmb)
    if df is None or df.empty:
        UI.empty("暂无交易记录")
        return

    # 汇总指标
    m = TradingService.metrics(df)
    UI.metric_row([
        ("买入总额", f"¥{m['buy']:,.0f}"),
        ("卖出总额", f"¥{m['sell']:,.0f}"),
        ("权利金(收)", f"¥{m['prem_in']:,.0f}"),
        ("权利金(支)", f"¥{m['prem_out']:,.0f}"),
        ("手续费", f"¥{m['fees']:,.0f}"),
    ])

    # 明细表
    UI.sub_heading("交易明细")
    detail = TradingService.detail(df, stock_label)
    display = detail.rename(columns={
        "date": "日期",
        "symbol": "标的",
        "action_label": "操作",
        "quantity": "数量",
        "price": "单价",
        "fees": "手续费",
        "currency": "币种",
        "amount_rmb": "金额(RMB)",
    })
    UI.table(display, max_height=500)


def _add_trade_form():
    """交易录入表单。"""
    with UI.expander("添加交易", expanded=False):
        c1, c2, c3 = st.columns(3)
        action = c1.selectbox("操作", TRADE_ACTION_OPTIONS, key="tl_act")
        symbol = c2.text_input("标的代码", placeholder="AAPL",
                               key="tl_sym").upper()
        cur = c3.selectbox("币种", ["USD", "HKD", "CNY"], key="tl_cur")

        c4, c5, c6 = st.columns(3)
        qty = c4.number_input("数量", min_value=0, step=1, value=100,
                              key="tl_qty")
        price = c5.number_input("单价", min_value=0.0, step=0.01,
                                key="tl_price")
        fees = c6.number_input("手续费", min_value=0.0, step=0.01,
                               key="tl_fees")

        c7, c8 = st.columns(2)
        strike = c7.number_input("行权价", min_value=0.0, step=0.5,
                                 key="tl_strike")
        exp = c8.date_input("到期日", key="tl_exp")
        note = st.text_input("备注", key="tl_note")

        real_action = action.split(" ")[0] if " " in action else action

        if st.button("提交交易", key="btn_add_trade",
                     use_container_width=True):
            if not symbol:
                st.error("请输入标的代码")
            else:
                extra = ""
                if strike > 0:
                    extra = (f" | 行权价:{strike} "
                             f"到期:{exp.strftime('%Y-%m-%d')}")
                db.transactions.add(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    real_action, symbol=symbol,
                    quantity=qty, price=price, fees=fees, currency=cur,
                    subcategory=real_action,
                    note=(note + extra) if extra else note)
                st.rerun()
