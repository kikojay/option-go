"""
Telegram Bot 处理模块
"""
import re
from datetime import datetime
from src.database import add_transaction, get_transactions, get_portfolio_summary, get_campaigns
from src.models import Transaction, TransactionType


class TelegramHandler:
    """Telegram 消息处理器"""

    def __init__(self):
        self.commands = {
            "help": self.handle_help,
            "add": self.handle_add,
            "portfolio": self.handle_portfolio,
            "pnl": self.handle_pnl,
            "campaign": self.handle_campaign,
            "record": self.handle_record,
            "status": self.handle_status,
        }

    def process_message(self, message: str) -> str:
        """
        处理用户消息，返回回复
        """
        message = message.strip()

        # 解析命令
        for cmd, handler in self.commands.items():
            if message.lower().startswith(f"/{cmd}") or message.lower().startswith(f"{cmd}："):
                return handler(message)

        # 解析自然语言
        return self.parse_natural_language(message)

    def handle_help(self, message: str) -> str:
        """帮助命令"""
        return """
📚 **可用命令：**

**记账**
- `买入 AAPL 10股 @180` - 买入股票
- `卖出 AAPL 10股 @185` - 卖出股票
- `卖 SLV 85 put @1.5` - 卖看跌期权
- `买 SLV 85 put @1.2` - 买回看跌期权
- `接盘 SLV 100股 @80` - 被行权接盘
- `被买走 SLV @90` - 股票被买走
- `支出 餐饮 500` - 记支出
- `收入 工资 10000` - 记收入

**查询**
- `portfolio` - 总资产
- `pnl` - 盈亏情况
- `campaign SLV` - SLV 策略周期
- `status` - 账户状态

**示例**
```
卖 SLV 88 put @2.5
买入 AAPL 10股 @180
支出 餐饮 50
pnl
```
"""

    def handle_add(self, message: str) -> str:
        """添加交易"""
        # 解析格式
        return self.parse_natural_language(message)

    def handle_portfolio(self, message: str) -> str:
        """查询总资产"""
        summary = get_portfolio_summary()

        text = "💰 **资产汇总**\n\n"
        text += f"总资产: ${summary['total_assets']:,.2f}\n"
        text += f"总负债: ${summary['total_liabilities']:,.2f}\n"
        text += f"净资产: ${summary['net_worth']:,.2f}\n\n"

        text += "📈 **持仓**\n"
        for h in summary["holdings"]:
            holdings = summary["holdings"][h]
            text += f"- {h}: {holdings['shares']}股\n"
            text += f"  成本: ${holdings['avg_cost']:.2f}\n"
            text += f"  市值: ${holdings['market_value']:,.2f}\n"
            text += f"  浮动盈亏: ${holdings['unrealized_pnl']:,.2f}\n"

        return text

    def handle_pnl(self, message: str) -> str:
        """查询盈亏"""
        summary = get_portfolio_summary()

        text = "📊 **盈亏汇总**\n\n"
        text += f"已实现盈亏: ${summary['total_realized_pnl']:,.2f}\n"
        text += f"浮动盈亏: ${summary['total_unrealized_pnl']:,.2f}\n"
        text += f"总盈亏: ${summary['total_pnl']:,.2f}\n"

        return text

    def handle_campaign(self, message: str) -> str:
        """查询 Campaign"""
        parts = message.split()
        symbol = parts[1].upper() if len(parts) > 1 else None

        if not symbol:
            campaigns = get_campaigns()
            if not campaigns:
                return "暂无 Campaign"

            text = "📋 **所有 Campaign**\n\n"
            for c in campaigns:
                text += f"- {c['symbol']}: {c['status']}\n"
            return text

        summary = get_portfolio_summary()
        if symbol in summary["holdings"]:
            h = summary["holdings"][symbol]
            return f"""
📋 **{symbol} Campaign**

状态: {h.get('status', 'active')}
持仓: {h['shares']}股
调整后成本: ${h['avg_cost']:.2f}
已实现盈亏: ${h.get('realized_pnl', 0):,.2f}
浮动盈亏: ${h.get('unrealized_pnl', 0):,.2f}
"""
        return f"未找到 {symbol} 的 Campaign"

    def handle_record(self, message: str) -> str:
        """记录收支"""
        return self.parse_natural_language(message)

    def handle_status(self, message: str) -> str:
        """账户状态"""
        return self.handle_portfolio(message)

    def parse_natural_language(self, message: str) -> str:
        """
        解析自然语言消息
        """
        message = message.strip()

        # 卖出 Put: "卖 SLV 88 put @2.5" 或 "Sell SLV 88 put @2.5"
        match = re.search(r"(?:卖|sell)\s+(\w+)\s+(\d+)\s*(?:put|call)?\s*(?:@|at)\s*([\d.]+)", message, re.I)
        if match:
            symbol = match.group(1).upper()
            quantity = int(match.group(2))
            premium = float(match.group(3))
            subtype = "sell_put" if "put" in message.lower() else "sell_call"

            tx = Transaction(
                type=TransactionType.OPTION.value,
                subtype=subtype,
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=quantity * 100,  # 期权是100股
                price=premium,
                amount=premium * 100 * -1  # 收入为负数
            )
            add_transaction(tx)
            return f"✅ 已记录: 卖 {quantity}张 {symbol} {subtype.replace('sell_', '').upper()} @ ${premium}"

        # 买回期权: "买 SLV 88 put @1.2"
        match = re.search(r"(?:买|buy|平仓)\s+(\w+)\s+(\d+)\s*(?:put|call)?\s*(?:@|at)\s*([\d.]+)", message, re.I)
        if match:
            symbol = match.group(1).upper()
            quantity = int(match.group(2))
            premium = float(match.group(3))
            subtype = "buy_put" if "put" in message.lower() else "buy_call"

            tx = Transaction(
                type=TransactionType.OPTION.value,
                subtype=subtype,
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=quantity * 100,
                price=premium,
                amount=premium * 100  # 支出为正数
            )
            add_transaction(tx)
            return f"✅ 已记录: 买 {quantity}张 {symbol} {subtype.replace('buy_', '').upper()} @ ${premium}"

        # 买入股票: "买入 AAPL 10股 @180"
        match = re.search(r"(?:买入|buy)\s+(\w+)\s*(\d+)\s*(?:股|shares?)?\s*(?:@|at)\s*([\d.]+)", message, re.I)
        if match:
            symbol = match.group(1).upper()
            quantity = int(match.group(2))
            price = float(match.group(3))

            tx = Transaction(
                type=TransactionType.STOCK.value,
                subtype="buy",
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=price * quantity * -1  # 支出为负数
            )
            add_transaction(tx)
            return f"✅ 已记录: 买入 {symbol} {quantity}股 @ ${price}"

        # 卖出股票: "卖出 AAPL 10股 @185"
        match = re.search(r"(?:卖出|sell)\s+(\w+)\s*(\d+)\s*(?:股|shares?)?\s*(?:@|at)\s*([\d.]+)", message, re.I)
        if match:
            symbol = match.group(1).upper()
            quantity = int(match.group(2))
            price = float(match.group(3))

            tx = Transaction(
                type=TransactionType.STOCK.value,
                subtype="sell",
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=price * quantity  # 收入为正数
            )
            add_transaction(tx)
            return f"✅ 已记录: 卖出 {symbol} {quantity}股 @ ${price}"

        # 接盘股票（被行权）: "接盘 SLV 100股 @80"
        match = re.search(r"(?:接盘|assignment)\s+(\w+)\s*(\d+)\s*(?:股|shares?)?\s*(?:@|at)\s*([\d.]+)", message, re.I)
        if match:
            symbol = match.group(1).upper()
            quantity = int(match.group(2))
            price = float(match.group(3))

            tx = Transaction(
                type=TransactionType.STOCK.value,
                subtype="assignment",
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=quantity,
                price=price,
                amount=price * quantity * -1
            )
            add_transaction(tx)
            return f"✅ 已记录: 接盘 {symbol} {quantity}股 @ ${price}"

        # 被买走（股票被 call 走）: "被买走 SLV @90"
        match = re.search(r"(?:被买走|called.?away)\s+(\w+)\s*(?:@|at)?\s*([\d.]+)?", message, re.I)
        if match:
            symbol = match.group(1).upper()
            price = float(match.group(2)) if match.group(2) else None

            # 获取接盘时的成本
            tx = Transaction(
                type=TransactionType.STOCK.value,
                subtype="called_away",
                date=datetime.now().strftime("%Y-%m-%d"),
                symbol=symbol,
                quantity=100,  # 默认100股
                price=price or 0,
                amount=(price or 0) * 100
            )
            add_transaction(tx)
            return f"✅ 已记录: {symbol} 股票被买走 @ ${price}"

        # 支出: "支出 餐饮 500"
        match = re.search(r"(?:支出|expense)\s+(\w+)\s+([\d.]+)", message, re.I)
        if match:
            category = match.group(1)
            amount = float(match.group(2))

            tx = Transaction(
                type=TransactionType.EXPENSE.value,
                subtype="expense",
                date=datetime.now().strftime("%Y-%m-%d"),
                amount=amount,
                note=category
            )
            add_transaction(tx)
            return f"✅ 已记录: 支出 {category} ${amount}"

        # 收入: "收入 工资 10000"
        match = re.search(r"(?:收入|income)\s+(\w+)\s+([\d.]+)", message, re.I)
        if match:
            category = match.group(1)
            amount = float(match.group(2))

            tx = Transaction(
                type=TransactionType.INCOME.value,
                subtype="income",
                date=datetime.now().strftime("%Y-%m-%d"),
                amount=amount * -1,  # 收入为负数
                note=category
            )
            add_transaction(tx)
            return f"✅ 已记录: 收入 {category} ${amount}"

        return """
❓ 没理解，请用以下格式：

**期权**
- `卖 SLV 88 put @2.5`
- `买 SLV 88 put @1.2`
- `接盘 SLV 100股 @80`

**股票**
- `买入 AAPL 10股 @180`
- `卖出 AAPL 10股 @185`

**记账**
- `支出 餐饮 500`
- `收入 工资 10000`

输入 `help` 查看更多示例
"""


# 全局处理器实例
telegram_handler = TelegramHandler()
