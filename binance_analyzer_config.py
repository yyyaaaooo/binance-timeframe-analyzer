# -*- coding: utf-8 -*-
"""
Binance 分析器配置類別
支援現貨和永續合約市場的時間框架分析
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class BinanceAnalyzerConfig:
    # 基本設定
    symbol: str = "ETHUSDT"                    # 交易對
    exchange: str = "binance"                  # 交易所
    market_type: str = "spot"                  # 市場類型: "spot" 或 "futures"
    data_days: int = 365                       # 要抓取的天數
    auto_fetch: bool = True                    # 是否自動抓取資料
    save_csv: bool = True                      # 是否儲存CSV檔案
    
    # 資料管理設定
    force_redownload: bool = False             # 強制重新下載（覆蓋現有資料）
    incremental_update: bool = True            # 增量更新（只下載缺失的資料）
    data_quality_check: bool = True            # 啟用資料品質檢查
    min_data_quality_score: float = 0.8        # 最低資料品質分數（0-1）
    
    # 報告格式設定
    generate_csv_report: bool = True           # 生成CSV報告
    generate_txt_report: bool = True           # 生成TXT報告
    generate_md_report: bool = True            # 生成MD報告
    
    # 費率設定（現貨 vs 永續合約）
    spot_taker_fee: float = 0.001              # 現貨吃單費率 0.1%
    spot_maker_fee: float = 0.001              # 現貨掛單費率 0.1%
    futures_taker_fee: float = 0.0004          # 永續合約吃單費率 0.04%
    futures_maker_fee: float = 0.0002          # 永續合約掛單費率 0.02%
    
    # 技術指標參數
    atr_period: int = 14                       # ATR計算週期
    vr_q: int = 4                              # Variance Ratio聚合尺度
    half_life_max_lag: int = 100               # 半衰期計算最大延遲
    
    # 動態最小資料量設定
    use_dynamic_min_bars: bool = True          # 是否使用動態最小資料量
    n_min_bars_for_backtest: int = 1500        # 固定最小 bar 數（當 use_dynamic_min_bars=False 時使用）
    
    # 各時間框架的最小資料天數要求
    min_days_per_timeframe: Dict[str, int] = None
    
    # 候選時間框架（pandas resample 規則）
    timeframes: Dict[str, str] = None
    
    # 其他設定
    slippage_bps: float = 2.0                  # 滑點設定 (bps)
    use_taker: bool = True                     # 是否使用吃單費率
    tz: str = "UTC"                            # 時區設定

    def __post_init__(self):
        # 設定時間框架
        if self.timeframes is None:
            self.timeframes = {
                "1m": "1T",
                "5m": "5T", 
                "15m": "15T",
                "1h": "1H",
                "4h": "4H",
                "1d": "1D",
                "1w": "1W"
            }
        
        # 設定各時間框架的最小資料天數要求
        if self.min_days_per_timeframe is None:
            self.min_days_per_timeframe = {
                "1m": 30,    # 1分鐘需要30天
                "5m": 60,    # 5分鐘需要60天
                "15m": 90,   # 15分鐘需要90天
                "1h": 180,   # 1小時需要180天
                "4h": 365,   # 4小時需要365天
                "1d": 730,   # 1天需要730天
                "1w": 1095   # 1週需要1095天
            }
        
        # 設定CSV檔案路徑
        self.csv_path = f"./data/{self.symbol.lower()}_{self.market_type}_1m.csv"
    
    @property
    def taker_fee(self) -> float:
        """根據市場類型返回吃單費率"""
        return self.futures_taker_fee if self.market_type == "futures" else self.spot_taker_fee
    
    @property
    def maker_fee(self) -> float:
        """根據市場類型返回掛單費率"""
        return self.futures_maker_fee if self.market_type == "futures" else self.spot_maker_fee
