import datetime

import joblib
import polars as pl
from sklearn.linear_model import Lasso

from src.factor_aggregator.factor_aggregator import FactorAggregator
from src.market import Market
from src.sector.cape import CapeSector
from src.sector.dividend_yield import DividendYieldSector
from src.sector.fifty_two_week_high import FiftyTwoWeekHighSector
from src.sector.roe import RoeSector
from src.sector.sales_growth import SalesGrowthSector
from src.sector.volume import VolumeSector


class LassoAggregator(FactorAggregator):
    def __init__(self, security_universe, factor_type):
        super().__init__(security_universe, factor_type)
        self.lasso_model = joblib.load("lasso_model.pkl")
        self.feature_names = [
            "RoeSector",
            "VolumeSector",
            "SalesGrowthSector",
            # "FiftyTwoWeekHighSector",
            # "DividendYieldSector",
            # "CapeSector",
        ]
        self.normal_factors = [
            "RoeSector",
            # "FiftyTwoWeekHighSector",
            # "DividendYieldSector",
            # "CapeSector",
        ]
        self.reversed_factors = ["VolumeSector", "SalesGrowthSector"]

    def get_internal_sectors(self):
        roe = RoeSector()
        volume = VolumeSector()
        sales_growth = SalesGrowthSector()
        # fifty_two_week_high = FiftyTwoWeekHighSector()
        # dividend_yield = DividendYieldSector()
        # cape = CapeSector()
        return [
            roe,
            volume,
            sales_growth,
            # fifty_two_week_high,
            # dividend_yield,
            # cape,
        ]

    def get_fund_list(self, date):
        assert self.lasso_model is not None
        sector_score_df: pl.DataFrame = self.get_sector_scores(
            date, self.normal_factors, self.reversed_factors
        ).with_columns(pl.col("date").dt.month_end().alias("date"))
        sector_score_df = sector_score_df.pivot(
            index=["sector", "date"], columns="class_name", values="z-score"
        ).drop_nulls()
        lasso_predict_reuturn = pl.DataFrame(
            {
                "lasso_predict_return": self.lasso_model.predict(
                    sector_score_df.select(self.feature_names) * 1000
                )
            }
        )
        sector_score_df = pl.concat(
            [sector_score_df, lasso_predict_reuturn], how="horizontal"
        )
        sector_list = (
            sector_score_df.sort(pl.col("lasso_predict_return"), descending=True)
            .get_column("sector")
            .to_list()
        )
        fund_list = []
        for sector in sector_list:
            for security in self.security_universe:
                if security.sector == sector:
                    fund_list.append(security)
        return fund_list


class LassoModel:
    def __init__(
        self,
        security_universe,
        start_date,
        end_date,
        lasso_aggregator: LassoAggregator,
        market: Market,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.security_universe = security_universe
        self.lasso_aggregator = lasso_aggregator
        self.market = market
        self.model = Lasso(alpha=0.99, fit_intercept=False)
        self.melt_X = self.get_melt_X()
        self.fill_in_melt_X()
        self.X, self.y = self.get_X_and_y()

    def get_melt_X(self):
        X = pl.DataFrame(
            pl.date_range(
                start=datetime.date(start_date.year, start_date.month, 1),
                end=datetime.date(end_date.year, end_date.month, 1),
                interval="1mo",
                eager=True,
            ).alias("start_date")
        )
        X = X.with_columns(pl.col("start_date").dt.month_end().alias("end_date"))
        for fund in security_universe:
            X = X.with_columns(pl.lit(0).alias(str(fund.sector)))
        X = X.with_columns(pl.lit(0).alias("forward_1mo_return"))
        X = X.filter(pl.col("end_date") < end_date)
        self.start_date_list = X.get_column("start_date").unique().sort().to_list()
        self.end_date_list = X.get_column("end_date").unique().sort().to_list()
        melt_X = X.melt(
            id_vars=["start_date", "end_date", "forward_1mo_return"],
            value_vars=[str(fund.sector) for fund in self.security_universe],
            variable_name="sector",
            value_name="z-score",
        )
        return melt_X

    def fill_in_melt_X(self):
        # fill in factor and z-score
        sector_score_list = []
        for observe_date in self.end_date_list:
            sector_score_df = self.lasso_aggregator.get_sector_scores(
                observe_date,
                self.lasso_aggregator.normal_factors,
                self.lasso_aggregator.reversed_factors,
            )
            sector_score_df = sector_score_df.select(
                "sector", "date", "z-score", "class_name"
            )
            sector_score_list.append(sector_score_df)
        self.multi_day_sector_score_df = pl.concat(sector_score_list)
        self.multi_day_sector_score_df = self.multi_day_sector_score_df.with_columns(
            pl.col("date").dt.month_end().alias("date")
        )
        self.melt_X = self.melt_X.select(pl.all().exclude("z-score")).join(
            self.multi_day_sector_score_df,
            how="inner",
            left_on=[pl.col("sector"), pl.col("end_date")],
            right_on=[pl.col("sector"), pl.col("date")],
        )

        # fill in forward_1mo_return
        sector_ticker_mapping = {
            security_ticker.sector: security_ticker
            for security_ticker in self.security_universe
        }
        self.range_return_df = (
            self.melt_X.select("start_date", "end_date", "sector", "forward_1mo_return")
            .unique()
            .sort(by="end_date")
        )
        self.range_return_df = self.range_return_df.select(
            pl.col("sector"),
            pl.col("end_date"),
            (pl.col("end_date") + pl.duration(days=1))
            .dt.month_start()
            .alias("forward_start_date"),
            (pl.col("end_date") + pl.duration(days=1))
            .dt.month_end()
            .alias("forward_end_date"),
        )
        self.range_return_df = self.range_return_df.with_columns(
            pl.struct(["sector", "forward_start_date", "forward_end_date"])
            .map_elements(
                lambda x: self.market.query_range_return(
                    sector_ticker_mapping[x["sector"]],
                    x["forward_start_date"],
                    x["forward_end_date"],
                )
            )
            .alias("forward_1mo_return")
        )
        self.melt_X = self.melt_X.select(pl.all().exclude("forward_1mo_return")).join(
            self.range_return_df.select("end_date", "sector", "forward_1mo_return"),
            how="inner",
            left_on=["sector", "end_date"],
            right_on=["sector", "end_date"],
        )

    def get_X_and_y(self):
        X = self.melt_X.pivot(
            index=["start_date", "end_date", "sector", "forward_1mo_return"],
            columns="class_name",
            values="z-score",
            aggregate_function="max",
        ).drop_nulls()
        y = X.select("forward_1mo_return")
        X = X.select(pl.all().exclude("forward_1mo_return"))
        return X, y

    def train_model(self):
        self.model.fit(
            self.X.select(self.lasso_aggregator.feature_names) * 1000, self.y * 1e6
        )

    def save_model(self):
        joblib.dump(self.model, "lasso_model.pkl")


if __name__ == "__main__":
    from src.fund_universe import ISHARE_SECTOR_ETF_TICKER

    start_date = datetime.date(2012, 12, 31)
    end_date = datetime.date(2023, 10, 31)
    security_universe = ISHARE_SECTOR_ETF_TICKER
    market = Market(security_universe, start_date, end_date)
    lasso_aggregator = LassoAggregator(security_universe, "long")
    model = LassoModel(
        security_universe, start_date, end_date, lasso_aggregator, market
    )
    model.train_model()
    print("feature names:", model.model.feature_names_in_)
    print("lasso coef:", model.model.coef_)
    print("lasso intercept:", model.model.intercept_)
    model.save_model()
