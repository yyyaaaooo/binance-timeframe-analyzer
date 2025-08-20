# -*- coding: utf-8 -*-
"""
ETHUSDT 時間框架特性分析工具
=================================================
功能：
1) 自動從 Binance 抓取 ETHUSDT 1分鐘歷史資料
2) 從 1 分鐘 OHLCV CSV 重採樣成多個時間框架 (1m/5m/15m/1h/4h/1d/1w)
3) 計算時間框架特性指標：
   - 成本/波動比 C/A（Cost-to-ATR）
   - 走勢一致性（Variance Ratio, VR）
   - 訊號半衰期（基於報酬自相關的近似）
4) 生成時間框架特性分析報告
5) 匯出每個時間框架的彙整指標到 CSV、TXT、MD 格式

使用方式：
- 設定 CONFIG 區的資料抓取參數後執行本程式
- 程式會自動從 Binance 抓取 ETHUSDT 1分鐘歷史資料
- 產出檔案：./data/ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.csv
- 產出檔案：./data/ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.txt
- 產出檔案：./data/ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.md

注意：
- 本工具專注於分析各時間框架的市場特性，不包含策略回測
- 分析結果基於技術指標，提供時間框架選擇的客觀參考
"""

import math
import warnings
import requests
import time
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# =======================
# ======== CONFIG =======
# =======================

@dataclass
class Config:
    # 資料抓取設定
    symbol: str = "ETHUSDT"                    # 交易對
    exchange: str = "binance"                  # 交易所 (目前支援 binance)
    data_days: int = 1095                      # 要抓取的天數 (3年)
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
    
    # CSV 檔案路徑（如果 auto_fetch=False 則使用此路徑）
    csv_path: str = "./data/ethusdt_1m.csv"

    # CSV 欄位名（大小寫與實際一致或由 detect_columns() 自動對映）
    ts_col: str = "timestamp"
    open_col: str = "open"
    high_col: str = "high"
    low_col: str = "low"
    close_col: str = "close"
    vol_col: str = "volume"

    # 時區字串（若 timestamp 已為 UTC，可維持 "UTC"）
    tz: str = "UTC"

    # 候選時間框架（pandas resample 規則）
    # 1min 已是來源頻率，保留以便統一流程
    timeframes: Dict[str, str] = None

    # 成本假設（單邊，一次成交）
    taker_fee: float = 0.0004     # 0.04%
    maker_fee: float = 0.0002     # 0.02%
    slippage_bps: float = 2.0     # 2 bps = 0.02%
    use_taker: bool = True        # True: 用吃單費率；False: 用掛單費率

    # ATR 參數
    atr_period: int = 14

    # Variance Ratio 參數（以 q 表示聚合尺度）
    vr_q: int = 4

    # 訊號半衰期計算的最大延遲（單位：bar）
    half_life_max_lag: int = 100

    # 動態最小資料量設定
    use_dynamic_min_bars: bool = True          # 是否使用動態最小資料量
    n_min_bars_for_backtest: int = 1500       # 固定最小 bar 數（當 use_dynamic_min_bars=False 時使用）
    
    # 各時間框架的最小資料天數要求
    min_days_per_timeframe: Dict[str, int] = None

    def __post_init__(self):
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


CFG = Config()


# =======================
# ====== DATA FETCH =====
# =======================

def fetch_binance_klines(symbol: str, interval: str, start_time: int, end_time: int) -> List[List]:
    """
    從 Binance API 抓取 K線資料
    
    Args:
        symbol: 交易對 (如 "ETHUSDT")
        interval: 時間間隔 ("1m", "5m", "1h", "1d" 等)
        start_time: 開始時間戳記 (毫秒)
        end_time: 結束時間戳記 (毫秒)
    
    Returns:
        K線資料列表
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time,
        "limit": 1000  # Binance 單次請求最大限制
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"抓取資料時發生錯誤: {e}")
        return []


def fetch_historical_data(symbol: str, days: int, interval: str = "1m") -> pd.DataFrame:
    """
    抓取指定天數的歷史資料
    
    Args:
        symbol: 交易對
        days: 要抓取的天數
        interval: 時間間隔
    
    Returns:
        包含 OHLCV 資料的 DataFrame
    """
    print(f"開始從 Binance 抓取 {symbol} {interval} 資料，共 {days} 天...")
    
    # 計算時間範圍
    end_time = int(time.time() * 1000)  # 現在時間 (毫秒)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)  # days 天前
    
    all_data = []
    current_start = start_time
    
    while current_start < end_time:
        current_end = min(current_start + (1000 * 60 * 1000), end_time)  # 每次最多1000根K線
        
        print(f"抓取 {datetime.fromtimestamp(current_start/1000)} 到 {datetime.fromtimestamp(current_end/1000)} 的資料...")
        
        klines = fetch_binance_klines(symbol, interval, current_start, current_end)
        
        if not klines:
            print("警告：此時間範圍沒有資料，跳過...")
            current_start = current_end
            continue
        
        all_data.extend(klines)
        current_start = current_end
        
        # 避免請求過於頻繁
        time.sleep(0.1)
    
    if not all_data:
        raise ValueError("沒有抓取到任何資料")
    
    # 轉換為 DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # 轉換資料類型
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # 設定時區
    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
    
    # 排序並去重
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
    df = df.set_index('timestamp')
    
    print(f"成功抓取 {len(df)} 根K線資料")
    print(f"資料時間範圍: {df.index.min()} 到 {df.index.max()}")
    
    return df


def save_data_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """將資料儲存為 CSV 檔案"""
    try:
        df.to_csv(filepath, encoding='utf-8-sig')
        print(f"資料已儲存至: {filepath}")
    except Exception as e:
        print(f"儲存CSV時發生錯誤: {e}")


def load_or_fetch_data(cfg: Config) -> pd.DataFrame:
    """
    根據設定載入或抓取資料
    
    Returns:
        包含 OHLCV 資料的 DataFrame
    """
    if cfg.auto_fetch:
        print("=== 自動抓取模式 ===")
        try:
            df = fetch_historical_data(cfg.symbol, cfg.data_days)
            
            if cfg.save_csv:
                save_data_to_csv(df, cfg.csv_path)
            
            return df
            
        except Exception as e:
            print(f"自動抓取失敗: {e}")
            print("嘗試使用本地CSV檔案...")
            return load_1m_csv(cfg.csv_path, cfg)
    else:
        print("=== 本地CSV模式 ===")
        return load_1m_csv(cfg.csv_path, cfg)


def check_existing_data(cfg: Config) -> Tuple[bool, pd.DataFrame, Dict]:
    """
    檢查現有資料的狀態
    
    Returns:
        (資料是否存在, DataFrame, 資料狀態報告)
    """
    import os
    
    if not os.path.exists(cfg.csv_path):
        return False, None, {"status": "檔案不存在"}
    
    try:
        df = load_1m_csv(cfg.csv_path, cfg)
        if df.empty:
            return False, df, {"status": "檔案存在但為空"}
        
        # 計算資料狀態
        start_time = df.index.min()
        end_time = df.index.max()
        total_days = (end_time - start_time).total_seconds() / (24 * 3600)
        expected_days = cfg.data_days
        
        status = {
            "status": "資料存在",
            "start_time": start_time,
            "end_time": end_time,
            "total_days": total_days,
            "expected_days": expected_days,
            "data_completeness": min(total_days / expected_days, 1.0),
            "total_bars": len(df),
            "missing_bars": 0,
            "duplicate_bars": df.index.duplicated().sum(),
            "null_values": df.isnull().sum().sum()
        }
        
        # 檢查是否有缺失的時間點
        expected_bars = int(expected_days * 24 * 60)  # 預期的分鐘數
        status["missing_bars"] = max(0, expected_bars - len(df))
        
        return True, df, status
        
    except Exception as e:
        return False, None, {"status": f"讀取失敗: {e}"}


def check_data_quality(df: pd.DataFrame, cfg: Config) -> Dict:
    """
    檢查資料品質並產生報告
    
    Returns:
        資料品質報告字典
    """
    if df is None or df.empty:
        return {"quality_score": 0.0, "issues": ["資料為空"]}
    
    issues = []
    score = 1.0
    
    # 1. 檢查基本結構
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        issues.append(f"缺少必要欄位: {missing_cols}")
        score -= 0.3
    
    # 2. 檢查時間序列完整性
    time_diff = df.index.to_series().diff().dropna()
    expected_diff = pd.Timedelta(minutes=1)
    irregular_intervals = (time_diff != expected_diff).sum()
    if irregular_intervals > 0:
        issues.append(f"時間間隔不規則: {irregular_intervals} 處")
        score -= min(0.2, irregular_intervals / len(df) * 0.5)
    
    # 3. 檢查重複資料
    duplicates = df.index.duplicated().sum()
    if duplicates > 0:
        issues.append(f"重複時間戳記: {duplicates} 個")
        score -= min(0.2, duplicates / len(df) * 0.5)
    
    # 4. 檢查缺失值
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    if total_nulls > 0:
        issues.append(f"缺失值: {total_nulls} 個")
        score -= min(0.2, total_nulls / (len(df) * len(df.columns)) * 0.5)
    
    # 5. 檢查價格邏輯
    price_errors = ((df['high'] < df['low']) | 
                   (df['open'] > df['high']) | 
                   (df['close'] > df['high']) |
                   (df['open'] < df['low']) | 
                   (df['close'] < df['low'])).sum()
    if price_errors > 0:
        issues.append(f"價格邏輯錯誤: {price_errors} 筆")
        score -= min(0.3, price_errors / len(df) * 0.5)
    
    # 6. 檢查異常值
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            # 檢查是否有零值或負值
            zero_or_negative = (df[col] <= 0).sum()
            if zero_or_negative > 0:
                issues.append(f"{col} 欄位有零值或負值: {zero_or_negative} 筆")
                score -= min(0.1, zero_or_negative / len(df) * 0.3)
    
    # 7. 檢查成交量
    if 'volume' in df.columns:
        negative_volume = (df['volume'] < 0).sum()
        if negative_volume > 0:
            issues.append(f"負成交量: {negative_volume} 筆")
            score -= min(0.1, negative_volume / len(df) * 0.3)
    
    # 8. 檢查時間範圍
    now = pd.Timestamp.now(tz='UTC')
    if df.index.max() > now:
        issues.append("資料包含未來時間")
        score -= 0.1
    
    score = max(0.0, score)
    
    return {
        "quality_score": score,
        "issues": issues,
        "total_bars": len(df),
        "time_range": f"{df.index.min()} 到 {df.index.max()}",
        "data_completeness": len(df) / (cfg.data_days * 24 * 60) if cfg.data_days > 0 else 1.0
    }


def get_missing_date_ranges(df: pd.DataFrame, target_days: int) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    找出缺失的日期範圍
    
    Returns:
        缺失日期範圍列表 [(start, end), ...]
    """
    if df is None or df.empty:
        # 如果沒有資料，返回完整的目標範圍
        end_time = pd.Timestamp.now(tz='UTC')
        start_time = end_time - pd.Timedelta(days=target_days)
        return [(start_time, end_time)]
    
    end_time = pd.Timestamp.now(tz='UTC')
    start_time = end_time - pd.Timedelta(days=target_days)
    
    missing_ranges = []
    
    # 檢查開始時間
    if df.index.min() > start_time:
        missing_ranges.append((start_time, df.index.min()))
    
    # 檢查結束時間
    if df.index.max() < end_time:
        missing_ranges.append((df.index.max(), end_time))
    
    # 檢查中間的間隙
    time_diff = df.index.to_series().diff().dropna()
    expected_diff = pd.Timedelta(minutes=1)
    gap_indices = time_diff[time_diff > expected_diff].index
    
    for gap_start in gap_indices:
        gap_end = gap_start + time_diff[gap_start]
        missing_ranges.append((gap_start, gap_end))
    
    return missing_ranges


def fetch_incremental_data(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """
    增量下載缺失的資料
    
    Returns:
        合併後的完整DataFrame
    """
    print("=== 增量資料更新 ===")
    
    missing_ranges = get_missing_date_ranges(df, cfg.data_days)
    
    if not missing_ranges:
        print("資料已完整，無需增量更新")
        return df
    
    print(f"發現 {len(missing_ranges)} 個缺失時間範圍")
    
    new_data = []
    for i, (start_time, end_time) in enumerate(missing_ranges):
        print(f"下載缺失資料 {i+1}/{len(missing_ranges)}: {start_time} 到 {end_time}")
        
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        klines = fetch_binance_klines(cfg.symbol, "1m", start_ms, end_ms)
        
        if klines:
            # 轉換為DataFrame
            temp_df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                temp_df[col] = temp_df[col].astype(float)
            
            temp_df['timestamp'] = temp_df['timestamp'].dt.tz_localize('UTC')
            temp_df = temp_df.set_index('timestamp')
            
            new_data.append(temp_df)
        
        time.sleep(0.1)  # 避免API限制
    
    if new_data:
        # 合併新資料
        new_df = pd.concat(new_data)
        combined_df = pd.concat([df, new_df])
        combined_df = combined_df.sort_index().drop_duplicates()
        
        print(f"增量更新完成，新增 {len(new_df)} 根K線")
        return combined_df
    else:
        print("沒有新資料需要下載")
        return df


def smart_data_loader(cfg: Config) -> pd.DataFrame:
    """
    智能資料載入器：檢查現有資料，決定是否需要下載或更新
    
    Returns:
        完整的DataFrame
    """
    print("=== 智能資料管理 ===")
    
    # 檢查現有資料
    data_exists, existing_df, status = check_existing_data(cfg)
    
    if data_exists:
        print(f"發現現有資料: {status['total_bars']} 根K線")
        print(f"時間範圍: {status['start_time']} 到 {status['end_time']}")
        print(f"資料完整度: {status['data_completeness']:.2%}")
        
        # 資料品質檢查
        if cfg.data_quality_check:
            quality_report = check_data_quality(existing_df, cfg)
            print(f"資料品質分數: {quality_report['quality_score']:.2f}")
            
            if quality_report['issues']:
                print("發現資料問題:")
                for issue in quality_report['issues']:
                    print(f"  - {issue}")
            
            if quality_report['quality_score'] < cfg.min_data_quality_score:
                print(f"資料品質分數 ({quality_report['quality_score']:.2f}) 低於閾值 ({cfg.min_data_quality_score})")
                if not cfg.force_redownload:
                    print("建議重新下載資料或檢查資料來源")
        
        # 決定是否需要重新下載
        if cfg.force_redownload:
            print("強制重新下載模式")
            return fetch_historical_data(cfg.symbol, cfg.data_days)
        
        # 檢查是否需要增量更新
        if cfg.incremental_update and status['data_completeness'] < 0.95:
            print("資料不完整，進行增量更新...")
            return fetch_incremental_data(existing_df, cfg)
        
        print("使用現有資料")
        return existing_df
    
    else:
        print("沒有現有資料，開始下載...")
        return fetch_historical_data(cfg.symbol, cfg.data_days)


def generate_data_report(df: pd.DataFrame, cfg: Config) -> str:
    """
    產生詳細的資料報告
    
    Returns:
        報告文字
    """
    if df is None or df.empty:
        return "資料報告: 無資料"
    
    quality_report = check_data_quality(df, cfg)
    
    report = []
    report.append("=" * 50)
    report.append("資料品質報告")
    report.append("=" * 50)
    report.append(f"資料來源: {cfg.exchange.upper()}")
    report.append(f"交易對: {cfg.symbol}")
    report.append(f"時間範圍: {df.index.min()} 到 {df.index.max()}")
    report.append(f"總K線數: {len(df):,}")
    report.append(f"資料完整度: {quality_report['data_completeness']:.2%}")
    report.append(f"品質分數: {quality_report['quality_score']:.2f}")
    report.append("")
    
    if quality_report['issues']:
        report.append("發現的問題:")
        for issue in quality_report['issues']:
            report.append(f"  ❌ {issue}")
    else:
        report.append("✅ 資料品質良好，未發現問題")
    
    report.append("")
    report.append("基本統計:")
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            report.append(f"  {col.upper()}: {df[col].min():.2f} - {df[col].max():.2f}")
    
    if 'volume' in df.columns:
        report.append(f"  Volume: {df['volume'].min():.2f} - {df['volume'].max():.2f}")
    
    report.append("=" * 50)
    
    return "\n".join(report)


def generate_txt_report(report_df: pd.DataFrame, cfg: Config, df_1m: pd.DataFrame) -> str:
    """
    生成TXT格式的詳細報告
    
    Args:
        report_df: 時間框架分析結果DataFrame
        cfg: 配置物件
        df_1m: 原始1分鐘資料
    
    Returns:
        TXT格式報告文字
    """
    report = []
    report.append("=" * 80)
    report.append("ETHUSDT 時間框架選擇分析報告")
    report.append("=" * 80)
    report.append("")
    
    # 基本資訊
    report.append("📊 基本資訊")
    report.append("-" * 40)
    report.append(f"交易對: {cfg.symbol}")
    report.append(f"交易所: {cfg.exchange.upper()}")
    report.append(f"測試日期範圍: {df_1m.index.min().strftime('%Y-%m-%d %H:%M:%S')} 到 {df_1m.index.max().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"總測試天數: {(df_1m.index.max() - df_1m.index.min()).days} 天")
    report.append(f"原始資料K線數: {len(df_1m):,}")
    report.append(f"報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 成本設定
    cost_one_way = (cfg.taker_fee if cfg.use_taker else cfg.maker_fee) + cfg.slippage_bps / 10000.0
    report.append("💰 成本設定")
    report.append("-" * 40)
    report.append(f"費率類型: {'吃單費率' if cfg.use_taker else '掛單費率'}")
    report.append(f"單邊成本: {cost_one_way:.6f} ({cost_one_way*100:.4f}%)")
    report.append(f"來回成本: {cost_one_way*2:.6f} ({cost_one_way*2*100:.4f}%)")
    report.append("")
    
    # 分析設定
    report.append("⚙️ 分析設定")
    report.append("-" * 40)
    report.append(f"ATR週期: {cfg.atr_period}")
    report.append(f"Variance Ratio聚合尺度: {cfg.vr_q}")
    report.append(f"半衰期最大延遲: {cfg.half_life_max_lag}")
    report.append("")
    
    # 時間框架分析結果
    report.append("📈 時間框架分析結果")
    report.append("-" * 40)
    report.append("")
    
    # 創建已測試時間框架的集合
    tested_timeframes = set(report_df['Timeframe'].tolist())
    
    # 遍歷所有配置的時間框架
    for tf_label, rule in cfg.timeframes.items():
        if tf_label in tested_timeframes:
            # 找到對應的測試結果
            row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
            report.append(f"🕐 {row['Timeframe']} 時間框架")
            report.append(f"    K線數量: {row['Bars']:,}")
            report.append(f"    平均ATR: {row['Avg_ATR_pct']:.4f} ({row['Avg_ATR_pct']*100:.2f}%)")
            report.append(f"    成本/波動比 (C/A): {row['C_over_A']:.4f}")
            report.append(f"    走勢一致性 (VR): {row['VarianceRatio']:.4f}")
            report.append(f"    訊號半衰期: {row['HalfLife_bars']:.1f} bars")
            report.append(f"    年化波動率: {row['Volatility_Ann']:.4f}")
            report.append(f"    報酬偏度: {row['Skewness']:.4f}")
            report.append(f"    報酬峰度: {row['Kurtosis']:.4f}")
            report.append(f"    自相關(Lag1): {row['Autocorr_Lag1']:.4f}")
            report.append(f"    市場效率比率: {row['Market_Efficiency']:.4f}")
            
            # 可行性評估
            if row['Pass_CA_0.25']:
                report.append(f"    ✅ 通過C/A < 0.25測試")
            else:
                report.append(f"    ❌ 未通過C/A < 0.25測試")
        else:
            # 未測試的時間框架
            report.append(f"🕐 {tf_label} 時間框架")
            report.append(f"    ❌ 未進行測試")
            min_bars_required = get_min_bars_for_timeframe(tf_label, cfg)
            min_days_required = cfg.min_days_per_timeframe.get(tf_label, 365) if cfg.use_dynamic_min_bars else "N/A"
            report.append(f"    原因: 資料量不足（需要至少 {min_bars_required} 根K線）")
            if cfg.use_dynamic_min_bars:
                report.append(f"    要求: 至少 {min_days_required} 天的資料")
            report.append(f"    建議: 增加資料天數或調整最小資料量設定")
        
        report.append("")
    
    # 綜合建議
    report.append("💡 綜合建議")
    report.append("-" * 40)
    
    # 找出最佳時間框架
    best_ca = report_df.loc[report_df['C_over_A'].idxmin()] if 'C_over_A' in report_df.columns else None
    best_vr = report_df.loc[report_df['VarianceRatio'].idxmax()] if 'VarianceRatio' in report_df.columns else None
    
    if best_ca is not None and not pd.isna(best_ca['C_over_A']):
        report.append(f"最佳成本效率時間框架: {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
    
    if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
        report.append(f"最高趨勢性時間框架: {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
    
    report.append("")
    report.append("📋 指標解讀指南:")
    report.append("• C/A < 0.25: 成本相對於波動率較低，適合交易")
    report.append("• VR > 1: 偏趨勢市場，適合趨勢策略")
    report.append("• VR < 1: 偏均值回歸市場，適合均值回歸策略")
    report.append("• 半衰期: 建議bar週期約為0.5~1倍半衰期")
    report.append("• 波動率: 反映市場波動程度")
    report.append("• 偏度: 正偏度表示右尾較長，負偏度表示左尾較長")
    report.append("• 峰度: 高峰度表示極端值較多")
    report.append("• 自相關: 正值表示趨勢性，負值表示均值回歸")
    report.append("• 市場效率比率: 越接近1表示市場越有效率")
    
    # 添加詳細指標解釋
    report.append("")
    report.append("📊 詳細指標解釋")
    report.append("-" * 40)
    report.append("")
    
    report.append("🔍 成本/波動比 (C/A Ratio)")
    report.append("意義: 衡量交易成本相對於市場波動的比率")
    report.append("解讀: ")
    report.append("• C/A < 0.25: 成本相對較低，適合頻繁交易")
    report.append("• C/A 0.25-0.5: 成本適中，需要謹慎選擇入場點")
    report.append("• C/A > 0.5: 成本過高，不適合短線交易")
    report.append("")
    
    report.append("🔍 走勢一致性 (Variance Ratio, VR)")
    report.append("意義: 衡量價格變動的趨勢性強度")
    report.append("解讀:")
    report.append("• VR > 1: 價格變動具有趨勢性，適合趨勢跟隨策略")
    report.append("• VR < 1: 價格變動偏向隨機遊走，適合均值回歸策略")
    report.append("• VR ≈ 1: 價格變動接近隨機遊走")
    report.append("")
    
    report.append("🔍 訊號半衰期 (Signal Half-Life)")
    report.append("意義: 衡量價格訊號的持續時間")
    report.append("解讀:")
    report.append("• 半衰期越長，訊號越持久，適合較長期的策略")
    report.append("• 半衰期越短，訊號變化越快，需要更頻繁的調整")
    report.append("")
    
    report.append("🔍 年化波動率 (Annualized Volatility)")
    report.append("意義: 衡量價格變動的劇烈程度")
    report.append("解讀:")
    report.append("• 波動率越高，價格變動越劇烈，風險越大")
    report.append("• 波動率越低，價格變動越平穩，風險較小")
    report.append("")
    
    report.append("🔍 報酬偏度 (Return Skewness)")
    report.append("意義: 衡量報酬分布的對稱性")
    report.append("解讀:")
    report.append("• 正偏度: 右尾較長，大幅上漲機率較高")
    report.append("• 負偏度: 左尾較長，大幅下跌機率較高")
    report.append("")
    
    report.append("🔍 報酬峰度 (Return Kurtosis)")
    report.append("意義: 衡量報酬分布的尖銳程度")
    report.append("解讀:")
    report.append("• 高峰度: 極端值出現機率較高，風險較大")
    report.append("• 低峰度: 分布較平坦，極端值較少")
    report.append("")
    
    report.append("🔍 自相關 (Autocorrelation)")
    report.append("意義: 衡量當前價格與過去價格的相關性")
    report.append("解讀:")
    report.append("• 正值: 價格具有趨勢性，過去走勢對未來有影響")
    report.append("• 負值: 價格具有均值回歸特性")
    report.append("")
    
    report.append("🔍 市場效率比率 (Market Efficiency Ratio)")
    report.append("意義: 衡量市場的資訊效率")
    report.append("解讀:")
    report.append("• 接近1: 市場效率較高，價格充分反映資訊")
    report.append("• 遠離1: 市場效率較低，可能存在套利機會")
    report.append("")
    
    # 添加市場分析結論
    report.append("📈 市場分析結論")
    report.append("-" * 40)
    report.append("")
    
    # 分析整體市場特性
    avg_volatility = report_df['Volatility_Ann'].mean() if 'Volatility_Ann' in report_df.columns else None
    avg_vr = report_df['VarianceRatio'].mean() if 'VarianceRatio' in report_df.columns else None
    avg_autocorr = report_df['Autocorr_Lag1'].mean() if 'Autocorr_Lag1' in report_df.columns else None
    avg_me = report_df['Market_Efficiency'].mean() if 'Market_Efficiency' in report_df.columns else None
    
    report.append("🎯 整體市場特性:")
    if avg_volatility and not pd.isna(avg_volatility):
        volatility_level = "高" if avg_volatility > 0.5 else "中" if avg_volatility > 0.3 else "低"
        report.append(f"1. 波動性: {cfg.symbol}年化波動率約{avg_volatility:.1%}，屬於{volatility_level}波動資產")
    
    if avg_me and not pd.isna(avg_me):
        efficiency_level = "高" if abs(avg_me - 1) < 0.1 else "中" if abs(avg_me - 1) < 0.2 else "低"
        report.append(f"2. 市場效率: 各時間框架的市場效率比率都接近1，顯示市場資訊效率較{efficiency_level}")
    
    if avg_autocorr and not pd.isna(avg_autocorr):
        if avg_autocorr < -0.01:
            report.append("3. 均值回歸: 大部分時間框架顯示負自相關，表示價格具有均值回歸特性")
        elif avg_autocorr > 0.01:
            report.append("3. 趨勢性: 大部分時間框架顯示正自相關，表示價格具有趨勢性")
        else:
            report.append("3. 隨機性: 大部分時間框架顯示接近零的自相關，表示價格變動接近隨機")
    
    # 分析偏度特性
    long_term_timeframes = ['1d', '1w']
    long_term_skewness = []
    for tf in long_term_timeframes:
        if tf in report_df['Timeframe'].values:
            row = report_df[report_df['Timeframe'] == tf].iloc[0]
            if 'Skewness' in row and not pd.isna(row['Skewness']):
                long_term_skewness.append(row['Skewness'])
    
    if long_term_skewness:
        avg_long_skew = sum(long_term_skewness) / len(long_term_skewness)
        if avg_long_skew > 0.1:
            report.append("4. 長期正偏度: 較長時間框架顯示正偏度，長期來看上漲機率較高")
        elif avg_long_skew < -0.1:
            report.append("4. 長期負偏度: 較長時間框架顯示負偏度，長期來看下跌機率較高")
        else:
            report.append("4. 長期對稱性: 較長時間框架顯示接近對稱的分布")
    
    report.append("")
    report.append("🎯 交易策略建議:")
    
    # 分析通過C/A測試的時間框架
    passed_timeframes = report_df[report_df['Pass_CA_0.25'] == True]['Timeframe'].tolist()
    short_timeframes = [tf for tf in passed_timeframes if tf in ['1m', '5m', '15m']]
    medium_timeframes = [tf for tf in passed_timeframes if tf in ['1h', '4h']]
    long_timeframes = [tf for tf in passed_timeframes if tf in ['1d', '1w']]
    
    if short_timeframes:
        report.append(f"1. 短線交易({', '.join(short_timeframes)}): 適合，成本效率較好")
    else:
        report.append("1. 短線交易(1m-15m): 不建議，因為交易成本相對波動率過高(C/A > 0.25)")
    
    if medium_timeframes:
        report.append(f"2. 中線交易({', '.join(medium_timeframes)}): 適合，成本效率較好")
    
    if long_timeframes:
        report.append(f"3. 長線交易({', '.join(long_timeframes)}): 最適合，成本效率最佳，適合趨勢跟隨策略")
    
    report.append("")
    report.append("🎯 風險管理建議:")
    report.append("1. 由於高波動性，建議使用較小的倉位規模")
    report.append("2. 設置適當的止損位，避免極端價格變動造成的損失")
    report.append("3. 考慮使用期權等衍生品進行風險對沖")
    report.append("4. 關注市場情緒指標，避免在極端市場條件下交易")
    
    report.append("")
    report.append("🎯 最佳時間框架選擇:")
    
    # 找出最佳時間框架
    if best_ca is not None and not pd.isna(best_ca['C_over_A']):
        if best_ca['Timeframe'] in ['1h', '4h']:
            report.append(f"• 日內交易: {best_ca['Timeframe']}時間框架 (C/A: {best_ca['C_over_A']:.4f})")
        elif best_ca['Timeframe'] in ['1d', '1w']:
            report.append(f"• 長期投資: {best_ca['Timeframe']}時間框架 (C/A: {best_ca['C_over_A']:.4f}，成本效率最佳)")
    
    if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
        if best_vr['VarianceRatio'] > 1.05:
            report.append(f"• 波段交易: {best_vr['Timeframe']}時間框架 (VR: {best_vr['VarianceRatio']:.4f}，趨勢性最強)")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def generate_md_report(report_df: pd.DataFrame, cfg: Config, df_1m: pd.DataFrame) -> str:
    """
    生成Markdown格式的詳細報告
    
    Args:
        report_df: 時間框架分析結果DataFrame
        cfg: 配置物件
        df_1m: 原始1分鐘資料
    
    Returns:
        Markdown格式報告文字
    """
    report = []
    report.append("# ETHUSDT 時間框架選擇分析報告")
    report.append("")
    report.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 基本資訊
    report.append("## 📊 基本資訊")
    report.append("")
    report.append("| 項目 | 數值 |")
    report.append("|------|------|")
    report.append(f"| 交易對 | {cfg.symbol} |")
    report.append(f"| 交易所 | {cfg.exchange.upper()} |")
    report.append(f"| 測試開始時間 | {df_1m.index.min().strftime('%Y-%m-%d %H:%M:%S')} |")
    report.append(f"| 測試結束時間 | {df_1m.index.max().strftime('%Y-%m-%d %H:%M:%S')} |")
    report.append(f"| 總測試天數 | {(df_1m.index.max() - df_1m.index.min()).days} 天 |")
    report.append(f"| 原始資料K線數 | {len(df_1m):,} |")
    report.append("")
    
    # 成本設定
    cost_one_way = (cfg.taker_fee if cfg.use_taker else cfg.maker_fee) + cfg.slippage_bps / 10000.0
    report.append("## 💰 成本設定")
    report.append("")
    report.append("| 項目 | 數值 |")
    report.append("|------|------|")
    report.append(f"| 費率類型 | {'吃單費率' if cfg.use_taker else '掛單費率'} |")
    report.append(f"| 單邊成本 | {cost_one_way:.6f} ({cost_one_way*100:.4f}%) |")
    report.append(f"| 來回成本 | {cost_one_way*2:.6f} ({cost_one_way*2*100:.4f}%) |")
    report.append("")
    
    # 分析設定
    report.append("## ⚙️ 分析設定")
    report.append("")
    report.append("| 項目 | 數值 |")
    report.append("|------|------|")
    report.append(f"| ATR週期 | {cfg.atr_period} |")
    report.append(f"| Variance Ratio聚合尺度 | {cfg.vr_q} |")
    report.append(f"| 半衰期最大延遲 | {cfg.half_life_max_lag} |")
    report.append("")
    
    # 時間框架分析結果
    report.append("## 📈 時間框架分析結果")
    report.append("")
    
    # 創建已測試時間框架的集合
    tested_timeframes = set(report_df['Timeframe'].tolist())
    
    # 建立結果表格
    table_headers = ["時間框架", "K線數", "C/A", "VR", "半衰期", "波動率", "偏度", "峰度", "自相關", "市場效率", "通過C/A測試", "狀態"]
    report.append("| " + " | ".join(table_headers) + " |")
    report.append("|" + "|".join(["---"] * len(table_headers)) + "|")
    
    # 遍歷所有配置的時間框架
    for tf_label, rule in cfg.timeframes.items():
        if tf_label in tested_timeframes:
            # 找到對應的測試結果
            row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
            volatility = f"{row['Volatility_Ann']:.4f}" if 'Volatility_Ann' in row and not pd.isna(row['Volatility_Ann']) else "N/A"
            skewness = f"{row['Skewness']:.4f}" if 'Skewness' in row and not pd.isna(row['Skewness']) else "N/A"
            kurtosis = f"{row['Kurtosis']:.4f}" if 'Kurtosis' in row and not pd.isna(row['Kurtosis']) else "N/A"
            autocorr = f"{row['Autocorr_Lag1']:.4f}" if 'Autocorr_Lag1' in row and not pd.isna(row['Autocorr_Lag1']) else "N/A"
            market_eff = f"{row['Market_Efficiency']:.4f}" if 'Market_Efficiency' in row and not pd.isna(row['Market_Efficiency']) else "N/A"
            pass_ca = "✅" if row['Pass_CA_0.25'] else "❌"
            
            table_row = [
                row['Timeframe'],
                f"{row['Bars']:,}",
                f"{row['C_over_A']:.4f}",
                f"{row['VarianceRatio']:.4f}",
                f"{row['HalfLife_bars']:.1f}",
                volatility,
                skewness,
                kurtosis,
                autocorr,
                market_eff,
                pass_ca,
                "✅ 已測試"
            ]
        else:
            # 未測試的時間框架
            table_row = [
                tf_label,
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "❌ 未測試"
            ]
        report.append("| " + " | ".join(table_row) + " |")
    
    report.append("")
    
    # 詳細分析
    report.append("### 🔍 詳細分析")
    report.append("")
    
    # 遍歷所有配置的時間框架
    for tf_label, rule in cfg.timeframes.items():
        if tf_label in tested_timeframes:
            # 找到對應的測試結果
            row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
            report.append(f"#### 🕐 {row['Timeframe']} 時間框架")
            report.append("")
            report.append(f"**基本統計:**")
            report.append(f"- K線數量: {row['Bars']:,}")
            report.append(f"- 平均ATR: {row['Avg_ATR_pct']:.4f} ({row['Avg_ATR_pct']*100:.2f}%)")
            report.append(f"- 成本/波動比 (C/A): {row['C_over_A']:.4f}")
            report.append(f"- 走勢一致性 (VR): {row['VarianceRatio']:.4f}")
            report.append(f"- 訊號半衰期: {row['HalfLife_bars']:.1f} bars")
            report.append("")
            
            # 統計特性
            if 'Volatility_Ann' in row and not pd.isna(row['Volatility_Ann']):
                report.append(f"**統計特性:**")
                report.append(f"- 年化波動率: {row['Volatility_Ann']:.4f}")
                report.append(f"- 報酬偏度: {row['Skewness']:.4f}")
                report.append(f"- 報酬峰度: {row['Kurtosis']:.4f}")
                report.append(f"- 自相關(Lag1): {row['Autocorr_Lag1']:.4f}")
                report.append(f"- 市場效率比率: {row['Market_Efficiency']:.4f}")
                report.append("")
            
            # 可行性評估
            if row['Pass_CA_0.25']:
                report.append("**可行性評估:** ✅ 通過C/A < 0.25測試")
            else:
                report.append("**可行性評估:** ❌ 未通過C/A < 0.25測試")
        else:
            # 未測試的時間框架
            report.append(f"#### 🕐 {tf_label} 時間框架")
            report.append("")
            report.append("**狀態:** ❌ 未進行測試")
            report.append("")
            report.append("**原因:**")
            min_bars_required = get_min_bars_for_timeframe(tf_label, cfg)
            min_days_required = cfg.min_days_per_timeframe.get(tf_label, 365) if cfg.use_dynamic_min_bars else "N/A"
            report.append(f"- 資料量不足（需要至少 {min_bars_required} 根K線）")
            if cfg.use_dynamic_min_bars:
                report.append(f"- 要求至少 {min_days_required} 天的資料")
            report.append("")
            report.append("**建議:**")
            report.append("- 增加資料天數")
            report.append("- 或調整最小資料量設定")
        
        report.append("")
    
    # 綜合建議
    report.append("## 💡 綜合建議")
    report.append("")
    
    # 找出最佳時間框架
            best_ca = report_df.loc[report_df['C_over_A'].idxmin()] if 'C_over_A' in report_df.columns else None
        best_vr = report_df.loc[report_df['VarianceRatio'].idxmax()] if 'VarianceRatio' in report_df.columns else None
        
        if best_ca is not None and not pd.isna(best_ca['C_over_A']):
            report.append(f"**最佳成本效率時間框架:** {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
        
        if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
            report.append(f"**最高趨勢性時間框架:** {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
    
    report.append("")
    report.append("### 📋 指標解讀指南")
    report.append("")
    report.append("| 指標 | 解讀 |")
    report.append("|------|------|")
    report.append("| C/A < 0.25 | 成本相對於波動率較低，適合交易 |")
    report.append("| VR > 1 | 偏趨勢市場，適合趨勢策略 |")
    report.append("| VR < 1 | 偏均值回歸市場，適合均值回歸策略 |")
    report.append("| 半衰期 | 建議bar週期約為0.5~1倍半衰期 |")
    report.append("| 樣本外夏普比率 | 越高越好，表示策略穩定性 |")
    report.append("| 樣本外最大回撤 | 越低越好，表示風險控制 |")
    report.append("")
    
    return "\n".join(report)


# =======================
# ====== UTILITIES ======
# =======================

def detect_columns(df: pd.DataFrame, cfg: Config) -> Dict[str, str]:
    """嘗試以寬鬆規則對映欄位名。"""
    cols = {c.lower(): c for c in df.columns}
    mapping = {}

    def pick(cands):
        for c in cands:
            if c in cols:
                return cols[c]
        return None

    mapping['ts'] = pick([cfg.ts_col.lower(), 'timestamp', 'date', 'time', 'datetime'])
    mapping['open'] = pick([cfg.open_col.lower(), 'open', 'o'])
    mapping['high'] = pick([cfg.high_col.lower(), 'high', 'h'])
    mapping['low'] = pick([cfg.low_col.lower(), 'low', 'l'])
    mapping['close'] = pick([cfg.close_col.lower(), 'close', 'c', 'price'])
    mapping['vol'] = pick([cfg.vol_col.lower(), 'volume', 'vol', 'v'])

    missing = [k for k, v in mapping.items() if v is None and k != 'vol']  # volume 可選
    if missing:
        raise ValueError(f"找不到必要欄位（大小寫不拘）: {missing}，請檢查 CSV 欄名。")

    return mapping


def load_1m_csv(path: str, cfg: Config) -> pd.DataFrame:
    """讀取 1m CSV，標準化欄位，設定為時序索引（UTC）。"""
    df = pd.read_csv(path)
    mapping = detect_columns(df, cfg)

    ts = pd.to_datetime(df[mapping['ts']], unit='ms', errors='coerce')
    if ts.isna().mean() > 0.5:
        # 多半代表不是毫秒，改用自然解析
        ts = pd.to_datetime(df[mapping['ts']], errors='coerce')

    if ts.isna().any():
        df = df.loc[~ts.isna()].copy()
        ts = pd.to_datetime(df[mapping['ts']], errors='coerce')
        if ts.isna().any():
            raise ValueError("timestamp 欄位解析失敗，請確認格式。")

    # 處理時區
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='NaT')
    else:
        ts = ts.dt.tz_convert('UTC')
    
    # 轉換到目標時區
    import pytz
    target_tz = pytz.timezone(cfg.tz) if isinstance(cfg.tz, str) else cfg.tz
    ts = ts.dt.tz_convert(target_tz)
    
    df = df.assign(
        timestamp=ts,
        open=df[mapping['open']].astype(float),
        high=df[mapping['high']].astype(float),
        low=df[mapping['low']].astype(float),
        close=df[mapping['close']].astype(float),
        volume=df[mapping['vol']].astype(float) if mapping['vol'] is not None else np.nan,
    ).dropna(subset=['open', 'high', 'low', 'close'])

    df = df.drop_duplicates(subset=['timestamp']).set_index('timestamp').sort_index()
    # 嘗試補齊缺漏分鐘（可選）
    # all_minutes = pd.date_range(df.index.min(), df.index.max(), freq='1T', tz=cfg.tz)
    # df = df.reindex(all_minutes).ffill()
    return df


def resample_ohlcv(df_1m: pd.DataFrame, rule: str) -> pd.DataFrame:
    """以 OHLCV 規則重採樣。"""
    agg = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    return df_1m.resample(rule, label='right', closed='right').agg(agg).dropna(subset=['open', 'high', 'low', 'close'])


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """簡易 ATR（SMA 版）。"""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    return atr


def variance_ratio(returns: pd.Series, q: int) -> float:
    """計算 Lo-MacKinlay 型的簡化 Variance Ratio。"""
    r = returns.dropna()
    if len(r) < q + 2:
        return np.nan
    var_1 = np.var(r, ddof=1)
    r_q = r.rolling(q).sum()
    var_q = np.var(r_q.dropna(), ddof=1)
    if var_1 == 0:
        return np.nan
    return float(var_q / (q * var_1))


def estimate_half_life_by_autocorr(returns: pd.Series, max_lag: int) -> Optional[float]:
    """
    用報酬自相關的衰減來近似「訊號半衰期」：
    找出 lag=1 的自相關 rho1，往後尋找第一個 lag=k 使得 |rho_k| <= 0.5*|rho1|。
    回傳 k（單位：bar）。若 rho1 無意義或找不到，回傳 None。
    """
    r = returns.dropna()
    if len(r) < max_lag + 5:
        return None

    r = r - r.mean()
    var = (r ** 2).sum()
    if var == 0:
        return None

    def autocorr(lag: int) -> float:
        return float((r[lag:] * r.shift(lag)[lag:]).sum() / var)

    rho1 = autocorr(1)
    if np.isnan(rho1) or abs(rho1) < 1e-6:
        return None

    target = 0.5 * abs(rho1)
    for k in range(2, max_lag + 1):
        rhok = autocorr(k)
        if np.isnan(rhok):
            continue
        if abs(rhok) <= target:
            return float(k)
    return None


def bar_minutes(label: str) -> float:
    mapping = {
        "1m": 1, "5m": 5, "15m": 15,
        "1h": 60, "4h": 240,
        "1d": 1440, "1w": 10080
    }
    return float(mapping.get(label, 1.0))


def get_min_bars_for_timeframe(tf_label: str, cfg: Config) -> int:
    """
    根據時間框架動態計算最小資料量要求
    
    Args:
        tf_label: 時間框架標籤 (如 "1m", "1h", "4h")
        cfg: 配置物件
    
    Returns:
        該時間框架需要的最小K線數量
    """
    if not cfg.use_dynamic_min_bars:
        return cfg.n_min_bars_for_backtest
    
    # 獲取該時間框架的最小天數要求
    min_days = cfg.min_days_per_timeframe.get(tf_label, 365)
    
    # 計算該時間框架每根K線的分鐘數
    minutes_per_bar = bar_minutes(tf_label)
    
    # 計算最小K線數量
    min_bars = int((min_days * 24 * 60) / minutes_per_bar)
    
    # 確保至少有100根K線作為絕對最小值
    min_bars = max(min_bars, 100)
    
    return min_bars


def annualization_factor(tf_label: str) -> float:
    """以 365*24*60 分鐘/年 換算每個 bar 的年化倍數。"""
    bars_per_year = (365.0 * 24.0 * 60.0) / bar_minutes(tf_label)
    return bars_per_year


# =======================
# ====== 技術指標計算 =======
# =======================

def calculate_volatility(returns: pd.Series, ann_factor: float) -> float:
    """計算年化波動率"""
    r = returns.dropna()
    if len(r) < 2:
        return np.nan
    return float(r.std(ddof=1) * math.sqrt(ann_factor))


def calculate_skewness(returns: pd.Series) -> float:
    """計算報酬偏度"""
    r = returns.dropna()
    if len(r) < 3:
        return np.nan
    return float(r.skew())


def calculate_kurtosis(returns: pd.Series) -> float:
    """計算報酬峰度"""
    r = returns.dropna()
    if len(r) < 4:
        return np.nan
    return float(r.kurtosis())


def calculate_autocorrelation(returns: pd.Series, lag: int = 1) -> float:
    """計算報酬自相關"""
    r = returns.dropna()
    if len(r) < lag + 1:
        return np.nan
    return float(r.autocorr(lag=lag))


def calculate_market_efficiency_ratio(returns: pd.Series) -> float:
    """計算市場效率比率（基於方差比）"""
    r = returns.dropna()
    if len(r) < 10:
        return np.nan
    
    # 計算不同時間間隔的方差比
    var_1 = r.var()
    var_2 = r.rolling(2).sum().dropna().var()
    
    if var_1 == 0:
        return np.nan
    
    return float(var_2 / (2 * var_1))


# =======================
# ====== PIPELINE =======
# =======================

def main(cfg: Config):
    print("=== 時間框架選擇工具 ===")
    
    try:
        df_1m = smart_data_loader(cfg)
        print(generate_data_report(df_1m, cfg))
    except Exception as e:
        print("資料載入失敗：", e)
        print("請確認網路連線或檢查 CSV 路徑與欄位。")
        return

    report_rows = []

    # 成本（單邊）
    cost_one_way = (cfg.taker_fee if cfg.use_taker else cfg.maker_fee) + cfg.slippage_bps / 10000.0
    print(f"採用 {'吃單' if cfg.use_taker else '掛單'} 費率；單邊成本 = {cost_one_way:.6f} ({cost_one_way*100:.4f}%)")

    for tf_label, rule in cfg.timeframes.items():
        print(f"\n--- 時間框架：{tf_label} ({rule}) ---")
        ohlc = resample_ohlcv(df_1m, rule)
        
        # 動態計算該時間框架的最小資料量要求
        min_bars_required = get_min_bars_for_timeframe(tf_label, cfg)
        
        if len(ohlc) < min_bars_required:
            min_days_required = cfg.min_days_per_timeframe.get(tf_label, 365) if cfg.use_dynamic_min_bars else "N/A"
            print(f"資料量不足（{len(ohlc)} < {min_bars_required} bars），略過。")
            if cfg.use_dynamic_min_bars:
                print(f"  該時間框架需要至少 {min_days_required} 天的資料")
            continue

        ann_factor = annualization_factor(tf_label)

        # C/A
        atr = compute_atr(ohlc, cfg.atr_period)
        atr_pct = (atr / ohlc['close']).dropna()
        avg_atr_pct = float(atr_pct.mean()) if len(atr_pct) else np.nan
        cost_roundtrip = 2.0 * cost_one_way
        c_over_a = float(cost_roundtrip / avg_atr_pct) if avg_atr_pct and avg_atr_pct > 0 else np.nan

        # VR
        ret = ohlc['close'].pct_change()
        vr = variance_ratio(np.log1p(ret), cfg.vr_q)

        # 半衰期（報酬自相關近似）
        hl = estimate_half_life_by_autocorr(np.log1p(ret), cfg.half_life_max_lag)

        # 計算額外的技術指標
        volatility = calculate_volatility(ret, ann_factor)
        skewness = calculate_skewness(ret)
        kurtosis = calculate_kurtosis(ret)
        autocorr_1 = calculate_autocorrelation(ret, lag=1)
        market_efficiency = calculate_market_efficiency_ratio(ret)

        row = {
            "Timeframe": tf_label,
            "Bars": len(ohlc),
            "Avg_ATR_pct": avg_atr_pct,
            "Cost_RoundTrip_pct": cost_roundtrip,
            "C_over_A": c_over_a,
            "VR_q": cfg.vr_q,
            "VarianceRatio": vr,
            "HalfLife_bars": hl,
            "Volatility_Ann": volatility,
            "Skewness": skewness,
            "Kurtosis": kurtosis,
            "Autocorr_Lag1": autocorr_1,
            "Market_Efficiency": market_efficiency,
        }

        # 簡單可行性標記
        row["Pass_CA_0.25"] = (c_over_a < 0.25) if not (pd.isna(c_over_a)) else False

        report_rows.append(row)

    if not report_rows:
        print("沒有可用的時間框架結果。請確認資料量或調整最小資料量設定。")
        if cfg.use_dynamic_min_bars:
            print("\n各時間框架的最小資料量要求：")
            for tf_label in cfg.timeframes.keys():
                min_bars = get_min_bars_for_timeframe(tf_label, cfg)
                min_days = cfg.min_days_per_timeframe.get(tf_label, 365)
                print(f"  {tf_label}: {min_bars} 根K線 ({min_days} 天)")
        return

    report = pd.DataFrame(report_rows).sort_values(
        by=["Pass_CA_0.25", "C_over_A", "VarianceRatio"],
        ascending=[False, True, False]
    )

    # 確保輸出目錄存在
    os.makedirs("./data", exist_ok=True)
    
    # 生成包含日期區間的檔名
    start_date = df_1m.index.min().strftime('%Y%m%d')
    end_date = df_1m.index.max().strftime('%Y%m%d')
    date_range = f"{start_date}-{end_date}"
    
    # 生成CSV報告
    if cfg.generate_csv_report:
        out_csv = f"./data/ethusdt_timeframe_report_{date_range}.csv"
        report.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"\n✅ 已輸出CSV報表：{out_csv}")
    
    # 生成TXT報告
    if cfg.generate_txt_report:
        txt_report = generate_txt_report(report, cfg, df_1m)
        out_txt = f"./data/ethusdt_timeframe_report_{date_range}.txt"
        with open(out_txt, 'w', encoding='utf-8') as f:
            f.write(txt_report)
        print(f"✅ 已輸出TXT報表：{out_txt}")
    
    # 生成MD報告
    if cfg.generate_md_report:
        md_report = generate_md_report(report, cfg, df_1m)
        out_md = f"./data/ethusdt_timeframe_report_{date_range}.md"
        with open(out_md, 'w', encoding='utf-8') as f:
            f.write(md_report)
        print(f"✅ 已輸出MD報表：{out_md}")
    
    print("\n📋 報告解讀指南：")
    print("1) 先看 C_over_A 是否 < 0.25（越低越好，表示交易成本相對波動較低）。")
    print("2) VarianceRatio > 1 表示偏趨勢市場，適合趨勢策略；< 1 表示偏均值回歸市場。")
    print("3) HalfLife_bars 提示適合的bar週期（建議bar週期約為0.5~1倍半衰期）。")
    print("4) 波動率、偏度、峰度等指標反映市場特性。")
    print("5) 詳細報告包含測試日期範圍、成本設定等完整資訊。")


if __name__ == "__main__":
    main(CFG)
