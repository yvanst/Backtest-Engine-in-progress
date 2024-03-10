from datetime import date
from src.security_symbol import SecurityTicker
from src.market import Market
from src.portfolio import Portfolio
from src.analysis import Analysis, Benchmark, Metric
from src.rebalance import Rebalance
from src.strategy import StopGainAndLoss
from src.backtest import BackTest
from src.factor.cape import CapeFactor
from src.factor.sales_growth import SalesGrowthFactor
from src.fund_universe import SECTOR_ETF_TICKER, SECTOR_ETF_LIPPER

start_date = date(2013, 1, 1)
end_date = date(2023, 10, 31)
security_universe = SECTOR_ETF_TICKER

market = Market(security_universe, start_date, end_date)


### Long factor
long_factor = CapeFactor(security_universe, "long")
long_portfolio = Portfolio(100.0, start_date, end_date)
long_factor.set_portfolio_at_start(long_portfolio)

blacklist = []
strategy = StopGainAndLoss(long_portfolio, blacklist)
strategy.set_limit(1, 1)
rebalance = Rebalance(60, long_portfolio, long_factor, blacklist)

backtest = BackTest(long_portfolio, strategy, market, rebalance)
backtest.run()

# print(long_portfolio.value_book)


### Short factor
short_factor = CapeFactor(security_universe, "short")
short_portfolio = Portfolio(100.0, start_date, end_date)
short_factor.set_portfolio_at_start(short_portfolio)

blacklist = []
strategy = StopGainAndLoss(short_portfolio, blacklist)
strategy.set_limit(1, 1)
rebalance = Rebalance(60, short_portfolio, short_factor, blacklist)

backtest = BackTest(short_portfolio, strategy, market, rebalance)
backtest.run()

# print(short_portfolio.value_book)

### plot
benchmark = Benchmark(
    SecurityTicker("^SPX", "index"), start_date, end_date
).get_performance()

metric = Metric(long_portfolio, benchmark)
print(f"portfolio annulized return: {metric.annualized_return()}")
print(
    f"portfolio annulized return relative to benchmark: {metric.annualized_return_relative_to_benchmark()}"
)
print(f"information ratio: {metric.information_ratio()}")

analysis = Analysis(
    long_portfolio,
    short_portfolio,
    benchmark,
    "SPX",
)
analysis.draw()
