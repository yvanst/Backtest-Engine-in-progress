from src.security_symbol import SecurityTicker, SecurityLipper


# source: https://www.cnbc.com/sector-etfs/
cnbc_ticker_sector_etf = {
    "Consumer Discretionary": "XLY",
    "Energy": "XLE",
    "Real Estate": "VNQ",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Information Technology": "XLK",
    "Communication Services": "XTL",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Financials": "XLF",
}

invesco_sp500_sector_etf = {
    "Consumer Discretionary": "40111945",
    "Energy": "40205516",  # not from invesco
    "Real Estate": "40212980",
    "Materials": "40111951",
    "Utilities": "40111953",
    "Information Technology": "40111952",
    "Communication Services": "40225234",
    "Health Care": "40111949",
    "Industrials": "40111950",
    "Consumer Staples": "40111946",
    "Financials": "40111948",
}

blackrock_sector_etf = {
    "Consumer Discretionary": "40056100",
    "Energy": "40205516",  # not from blackrock
    "Real Estate": "40056109",
    "Materials": "40056098",
    "Utilities": "40056106",
    "Information Technology": "40056080",
    "Communication Services": "40056094",
    "Health Care": "40056104",
    "Industrials": "40056105",
    "Consumer Staples": "40056101",
    "Financials": "40056093",
}


SECTOR_ETF_TICKER = [SecurityTicker(v, k) for k, v in cnbc_ticker_sector_etf.items()]
SECTOR_ETF_LIPPER = [SecurityLipper(v, k) for k, v in invesco_sp500_sector_etf.items()]
