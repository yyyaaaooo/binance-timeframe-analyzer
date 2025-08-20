# -*- coding: utf-8 -*-
"""
Binance 完整歷史資料分析
========================

本腳本下載從 Binance 官方開始時間（2017年7月14日）的完整資料
並進行時間框架分析，提供最全面的市場特性分析。

分析內容：
1. 從官方開始時間的完整歷史資料
2. 成本/波動比分析 (C/A)
3. 市場特性分析 (Variance Ratio)
4. 統計特性分析
5. 時間框架比較
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance_analyzer_config import BinanceAnalyzerConfig
from binance_timeframe_analyzer import BinanceTimeframeAnalyzer


def calculate_days_since_binance_launch() -> int:
    """計算從 Binance 成立（2017年7月14日）到現在的天數"""
    binance_launch_date = datetime(2017, 7, 14)
    current_date = datetime.now()
    delta = current_date - binance_launch_date
    return delta.days


def analyze_symbol_full_history(symbol: str, market_type: str) -> pd.DataFrame:
    """
    分析單個交易對從 Binance 官方開始時間的完整歷史資料
    
    Args:
        symbol: 交易對名稱 (如 "BTCUSDT", "ETHUSDT")
        market_type: 市場類型 ("spot" 或 "futures")
    
    Returns:
        包含時間框架分析結果的DataFrame
    """
    print(f"\n=== 開始分析 {symbol} {market_type} 市場 (完整歷史資料) ===")
    
    # 計算從 Binance 成立到現在的天數
    total_days = calculate_days_since_binance_launch()
    
    # 根據市場類型調整開始時間
    if market_type == "futures":
        if symbol == "BTCUSDT":
            # BTCUSDT 期貨從 2019年9月13日開始
            futures_start_date = datetime(2019, 9, 13)
            current_date = datetime.now()
            days = (current_date - futures_start_date).days
        elif symbol == "ETHUSDT":
            # ETHUSDT 期貨從 2020年8月21日開始
            futures_start_date = datetime(2020, 8, 21)
            current_date = datetime.now()
            days = (current_date - futures_start_date).days
        else:
            # 其他期貨交易對使用預設值
            days = total_days
    else:
        # 現貨市場從 2017年7月14日開始
        days = total_days
    
    print(f"📅 資料範圍: {days} 天")
    print(f"📊 預計K線數量: {days * 24 * 60:,} (1分鐘)")
    
    # 創建配置
    config = BinanceAnalyzerConfig(
        symbol=symbol,
        market_type=market_type,
        data_days=days,
        auto_fetch=True,
        save_csv=True,
        generate_csv_report=False,
        generate_txt_report=True,
        generate_md_report=False,
        force_redownload=True  # 強制重新下載完整資料
    )
    
    # 創建分析器並執行分析
    analyzer = BinanceTimeframeAnalyzer(config)
    report_df = analyzer.analyze()
    
    print(f"✅ {symbol} {market_type} 完整歷史分析完成")
    return report_df


def compare_full_history() -> Dict[str, pd.DataFrame]:
    """
    比較所有主要交易對的完整歷史資料分析
    
    Returns:
        包含所有分析結果的字典
    """
    print("🚀 開始完整歷史資料分析")
    print("=" * 60)
    
    # 要分析的交易對和市場類型
    symbols_to_analyze = [
        ("BTCUSDT", "spot"),
        ("ETHUSDT", "spot"),
        ("BTCUSDT", "futures"),
        ("ETHUSDT", "futures")
    ]
    
    results = {}
    
    for symbol, market_type in symbols_to_analyze:
        try:
            print(f"\n📈 分析 {symbol} {market_type} 市場...")
            report_df = analyze_symbol_full_history(symbol, market_type)
            results[f"{symbol}_{market_type}"] = report_df
            print(f"✅ {symbol} {market_type} 分析完成")
        except Exception as e:
            print(f"❌ {symbol} {market_type} 分析失敗: {e}")
            continue
    
    return results


def generate_summary_report(results: Dict[str, pd.DataFrame]) -> None:
    """生成總結報告"""
    print("\n" + "=" * 60)
    print("📊 完整歷史資料分析總結")
    print("=" * 60)
    
    for key, df in results.items():
        print(f"\n🔍 {key.upper()}")
        print("-" * 40)
        
        if df is not None and not df.empty:
            # 顯示通過 C/A < 0.25 測試的時間框架
            passed_tests = df[df['ca_ratio'] < 0.25]
            if not passed_tests.empty:
                print("✅ 通過 C/A < 0.25 測試的時間框架:")
                for _, row in passed_tests.iterrows():
                    print(f"   {row['timeframe']:>4}: C/A={row['ca_ratio']:.4f}, VR={row['variance_ratio']:.4f}")
            else:
                print("❌ 沒有時間框架通過 C/A < 0.25 測試")
            
            # 顯示最佳時間框架
            best_timeframe = df.loc[df['ca_ratio'].idxmin()]
            print(f"🏆 最佳時間框架: {best_timeframe['timeframe']} (C/A={best_timeframe['ca_ratio']:.4f})")
        else:
            print("❌ 無分析結果")


def main():
    """主函數"""
    print("🚀 Binance 完整歷史資料分析工具")
    print("=" * 60)
    print(f"📅 Binance 成立時間: 2017年7月14日")
    print(f"📅 現貨市場開始: 2017年7月14日")
    print(f"📅 期貨市場開始: 2019年9月13日 (BTCUSDT)")
    print(f"📅 ETHUSDT 期貨開始: 2020年8月21日")
    print("=" * 60)
    
    # 執行完整歷史分析
    results = compare_full_history()
    
    # 生成總結報告
    generate_summary_report(results)
    
    print("\n🎉 完整歷史資料分析完成！")
    print("📁 分析報告已儲存在 data/ 目錄中")


if __name__ == "__main__":
    main()
