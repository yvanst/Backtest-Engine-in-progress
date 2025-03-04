import datetime

import polars as pl

from src.sector.base_sector import BaseSector


class VolumeSector(BaseSector):
    def __init__(self) -> None:
        self.table = f"parquet/volume/us_security_volume_daily.parquet"
        self.sector_df = self.get_sector_construction()

    def impl_sector_signal(self, observe_date):
        """
        1. construct sector
        2. generate sector signal
        """
        signal_df = self.impl_security_signal(observe_date)
        sector_signal_df = self.agg_to_sector_signal(self.sector_df, signal_df, True)
        sector_signal_df = sector_signal_df.filter(
            pl.col("weighted_signal").is_not_nan()
        ).rename({"weighted_signal": "z-score"})
        return sector_signal_df

    def impl_security_signal(self, date):
        """
        use the average volume of current month divided by
        the average volume of the past 3 months as the signal
        """
        volume_df = (
            pl.scan_parquet(self.table)
            .filter(pl.col("volume").is_not_null())
            .filter(pl.col("volume") > 0)
            .filter((pl.col("date").dt.year() >= date.year - 2))
            .filter((pl.col("date") <= date))
            .collect()
        )
        volume_df = volume_df.with_columns(
            (
                pl.lit(date.year * 12 + date.month)
                - pl.col("date").dt.year() * 12
                - pl.col("date").dt.month()
            ).alias("month_diff")
        )
        cur_df = (
            volume_df.filter(pl.col("month_diff") >= 0)
            .filter(pl.col("month_diff") <= 2)
            .group_by("sedol7")
            .agg(pl.col("volume").mean().alias("cur_avg_volume"))
        )
        hist_df = (
            volume_df.filter(pl.col("month_diff") > 0)
            .filter(pl.col("month_diff") <= 5)
            .group_by("sedol7")
            .agg(pl.col("volume").mean().alias("hist_avg_volume"))
        )
        signal_df = cur_df.join(hist_df, on="sedol7", how="inner").with_columns(
            (pl.col("cur_avg_volume") / pl.col("hist_avg_volume")).alias("signal")
        )
        signal_df = signal_df.with_columns(pl.lit(date).alias("date"))
        return signal_df
