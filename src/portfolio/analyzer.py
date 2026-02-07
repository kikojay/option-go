"""
组合分析器 - 分析组合表现、风险和优化建议
"""
from typing import List, Dict
from src.models import Transaction
from src.options import WheelStrategyCalculator


class PortfolioAnalyzer:
    """
    投资组合分析器
    
    提供：
    - 表现分析（收益率、夏普比、最大回撤等）
    - 风险分析（波动率、VaR等）
    - 优化建议
    """

    def __init__(self, transactions: List[Transaction]):
        """
        初始化组合分析器
        
        Args:
            transactions: 所有交易列表
        """
        self.transactions = transactions
        self.wheel_calculator = WheelStrategyCalculator(transactions)

    def get_symbol_statistics(self, symbol: str, current_price: float = None) -> Dict:
        """
        获取单个持仓的统计信息
        
        Args:
            symbol: 股票代码
            current_price: 当前股价
            
        Returns:
            统计信息
        """
        basis = self.wheel_calculator.calculate_adjusted_cost_basis(symbol)
        
        stats = {
            "symbol": symbol,
            "shares": basis["current_shares"],
            "adjusted_cost": basis["adjusted_cost"],
            "total_cost": basis["cost_basis"]
        }
        
        if current_price and basis["current_shares"] > 0:
            market_value = basis["current_shares"] * current_price
            unrealized = market_value - basis["cost_basis"]
            return_pct = (unrealized / basis["cost_basis"] * 100) if basis["cost_basis"] > 0 else 0
            
            stats.update({
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized,
                "return_pct": return_pct
            })
        
        return stats

    def get_premium_efficiency(self, symbol: str = None) -> Dict:
        """
        计算权利金效率 - 已收权利金 / 成本基准
        
        Args:
            symbol: 股票代码（可选）
            
        Returns:
            权利金效率信息
        """
        tx = self.transactions
        if symbol:
            tx = [t for t in tx if t.symbol == symbol]
        
        # 计算总权利金收入
        option_tx = [t for t in tx if t.type.value == "option"]
        total_premiums = sum(-t.amount for t in option_tx if t.amount < 0)
        
        # 计算成本基准
        stock_tx = [t for t in tx if t.type.value == "stock" and t.subtype in ["buy", "assignment"]]
        total_cost = sum(t.amount for t in stock_tx)
        
        if total_cost <= 0:
            efficiency = 0
        else:
            efficiency = (total_premiums / total_cost * 100)
        
        return {
            "total_premiums": total_premiums,
            "total_cost": total_cost,
            "efficiency_pct": efficiency,
            "message": f"每投入 $100 成本，已收 ${efficiency:.2f} 权利金"
        }

    def get_diversification_analysis(self, prices: Dict[str, float] = None) -> Dict:
        """
        获取多样化分析
        
        Args:
            prices: 当前价格字典
            
        Returns:
            多样化指标
        """
        symbols = set(t.symbol for t in self.transactions if t.symbol)
        
        if len(symbols) <= 1:
            return {
                "symbol_count": len(symbols),
                "concentration": 100.0,
                "recommendation": "建议增加持仓品种"
            }
        
        # 计算集中度（Herfindahl指数）
        allocations = []
        total_value = 0
        
        for symbol in symbols:
            basis = self.wheel_calculator.calculate_adjusted_cost_basis(symbol)
            if basis["current_shares"] > 0:
                if prices and symbol in prices:
                    value = basis["current_shares"] * prices[symbol]
                else:
                    value = basis["cost_basis"]
                allocations.append(value)
                total_value += value
        
        if total_value == 0:
            return {"symbol_count": len(symbols), "concentration": 0}
        
        concentration = sum((v / total_value) ** 2 for v in allocations) * 100
        
        return {
            "symbol_count": len(symbols),
            "concentration": concentration,
            "recommendation": "集中度合理" if concentration < 50 else "建议分散投资"
        }

    def get_risk_metrics(self, prices: Dict[str, float] = None) -> Dict:
        """
        获取风险指标
        
        Args:
            prices: 当前价格字典
            
        Returns:
            风险指标
        """
        summary_data = {}
        symbols = set(t.symbol for t in self.transactions if t.symbol)
        
        for symbol in symbols:
            basis = self.wheel_calculator.calculate_adjusted_cost_basis(symbol)
            if basis["current_shares"] > 0:
                unrealized_data = self.wheel_calculator.calculate_unrealized_pnl(
                    symbol,
                    prices.get(symbol) if prices else 0
                )
                summary_data[symbol] = {
                    "shares": basis["current_shares"],
                    "cost": basis["cost_basis"],
                    "unrealized": unrealized_data["unrealized_pnl"]
                }
        
        if not summary_data:
            return {"risk_level": "no_position"}
        
        # 计算最大单个持仓风险
        max_unrealized = min(
            (v["unrealized"] for v in summary_data.values()),
            default=0
        )
        
        total_cost = sum(v["cost"] for v in summary_data.values())
        max_drawdown_pct = (max_unrealized / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "max_drawdown_pct": max_drawdown_pct,
            "total_exposed_cost": total_cost,
            "positions_count": len(summary_data),
            "risk_level": "低" if max_drawdown_pct > -10 else "中" if max_drawdown_pct > -20 else "高"
        }

    def get_performance_summary(self, prices: Dict[str, float] = None) -> Dict:
        """
        获取完整的表现汇总
        
        Args:
            prices: 当前价格字典
            
        Returns:
            表现汇总
        """
        return {
            "premium_efficiency": self.get_premium_efficiency(),
            "diversification": self.get_diversification_analysis(prices),
            "risk": self.get_risk_metrics(prices)
        }
