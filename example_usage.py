# -*- coding: utf-8 -*-
"""
ETHUSDT 時間框架特性分析工具 - 使用範例
=================================================

本範例展示如何使用時間框架特性分析工具來分析不同交易對和市場類型的時間框架特性。

主要功能：
1. 分析現貨和永續合約市場的時間框架特性
2. 比較不同交易對的市場特性
3. 自定義分析參數
4. 批量分析多個交易對

使用方式：
python example_usage.py
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance_analyzer_config import BinanceAnalyzerConfig
from binance_timeframe_analyzer import BinanceTimeframeAnalyzer


def analyze_symbol(symbol: str, market_type: str, days: int = 365) -> pd.DataFrame:
    """
    分析單個交易對的時間框架特性
    
    Args:
        symbol: 交易對名稱 (如 "ETHUSDT")
        market_type: 市場類型 ("spot" 或 "futures")
        days: 分析天數
    
    Returns:
        包含時間框架分析結果的DataFrame
    """
    print(f"開始分析 {symbol} {market_type} 市場...")
    
    # 創建配置
    config = BinanceAnalyzerConfig(
        symbol=symbol,
        market_type=market_type,
        data_days=days,
        auto_fetch=True,
        save_csv=True,
        generate_csv_report=True,
        generate_txt_report=True,
        generate_md_report=True
    )
    
    # 創建分析器並執行分析
    analyzer = BinanceTimeframeAnalyzer(config)
    report_df = analyzer.analyze()
    
    print(f"✅ {symbol} {market_type} 分析完成")
    return report_df


def compare_markets(symbol: str = "ETHUSDT", days: int = 365) -> Dict[str, pd.DataFrame]:
    """
    比較同一交易對在現貨和永續合約市場的特性
    
    Args:
        symbol: 交易對名稱
        days: 分析天數
    
    Returns:
        包含兩個市場分析結果的字典
    """
    results = {}
    
    # 分析現貨市場
    try:
        spot_config = BinanceAnalyzerConfig(
            symbol=symbol,
            market_type="spot",
            data_days=days
        )
        spot_analyzer = BinanceTimeframeAnalyzer(spot_config)
        results["spot"] = spot_analyzer.analyze()
        print(f"✅ {symbol} 現貨市場分析完成")
    except Exception as e:
        print(f"❌ {symbol} 現貨市場分析失敗: {e}")
        results["spot"] = None
    
    # 分析永續合約市場
    try:
        futures_config = BinanceAnalyzerConfig(
            symbol=symbol,
            market_type="futures",
            data_days=days
        )
        futures_analyzer = BinanceTimeframeAnalyzer(futures_config)
        results["futures"] = futures_analyzer.analyze()
        print(f"✅ {symbol} 永續合約市場分析完成")
    except Exception as e:
        print(f"❌ {symbol} 永續合約市場分析失敗: {e}")
        results["futures"] = None
    
    return results


def batch_analyze_symbols(symbols_to_analyze: List[Tuple[str, str]], days: int = 90) -> Dict[str, pd.DataFrame]:
    """
    批量分析多個交易對
    
    Args:
        symbols_to_analyze: 要分析的交易對列表，格式為 [(symbol, market_type), ...]
        days: 分析天數
    
    Returns:
        包含所有分析結果的字典
    """
    results = {}
    
    for symbol, market_type in symbols_to_analyze:
        print(f"\n正在分析 {symbol} {market_type}...")
        try:
            report_df = analyze_symbol(symbol, market_type, days)  # 3個月資料
            results[f"{symbol}_{market_type}"] = report_df
            print(f"✅ {symbol} {market_type} 分析完成")
        except Exception as e:
            print(f"❌ {symbol} {market_type} 分析失敗: {e}")
            results[f"{symbol}_{market_type}"] = None
    
    return results


def custom_analysis_example():
    """
    自定義分析範例
    展示如何設定自定義參數進行分析
    """
    print("\n=== 自定義分析範例 ===")
    
    # 創建自定義配置
    custom_config = BinanceAnalyzerConfig(
        symbol="BTCUSDT",
        market_type="spot",
        data_days=180,  # 6個月資料
        
        # 自定義技術指標參數
        atr_period=20,           # 使用20期ATR
        vr_q=5,                  # 使用5期Variance Ratio
        half_life_max_lag=50,    # 減少半衰期計算延遲
        
        # 自定義時間框架（只分析部分時間框架）
        timeframes={
            "5m": "5T",
            "15m": "15T", 
            "1h": "1H",
            "4h": "4H"
        },
        
        # 自定義費率設定
        spot_maker_fee=0.001,   # 0.1%
        
        # 報告設定
        generate_csv_report=True,
        generate_txt_report=False,
        generate_md_report=True
    )
    
    # 執行分析
    try:
        analyzer = BinanceTimeframeAnalyzer(custom_config)
        report_df = analyzer.analyze()
        
        print("✅ 自定義分析完成")
        print(f"分析結果包含 {len(report_df)} 個時間框架")
        
        # 顯示最佳成本效率的時間框架
        if 'C_over_A' in report_df.columns:
            best_ca = report_df.loc[report_df['C_over_A'].idxmin()]
            print(f"最佳成本效率時間框架: {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
        
        # 顯示最高趨勢性的時間框架
        if 'VarianceRatio' in report_df.columns:
            best_vr = report_df.loc[report_df['VarianceRatio'].idxmax()]
            print(f"最高趨勢性時間框架: {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
        
        return report_df
        
    except Exception as e:
        print(f"❌ 自定義分析失敗: {e}")
        return None


def main():
    """
    主函數 - 執行各種分析範例
    """
    print("=== ETHUSDT 時間框架特性分析工具 - 使用範例 ===")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 範例1: 分析單個交易對
    print("\n1. 分析 ETHUSDT 現貨市場")
    try:
        eth_spot_result = analyze_symbol("ETHUSDT", "spot", 90)
        print(f"分析完成，結果包含 {len(eth_spot_result)} 個時間框架")
    except Exception as e:
        print(f"分析失敗: {e}")
    
    # 範例2: 比較現貨和永續合約市場
    print("\n2. 比較 ETHUSDT 現貨和永續合約市場")
    try:
        market_comparison = compare_markets("ETHUSDT", 90)
        
        if market_comparison["spot"] is not None:
            print(f"現貨市場: {len(market_comparison['spot'])} 個時間框架")
        if market_comparison["futures"] is not None:
            print(f"永續合約市場: {len(market_comparison['futures'])} 個時間框架")
            
    except Exception as e:
        print(f"比較分析失敗: {e}")
    
    # 範例3: 批量分析多個交易對
    print("\n3. 批量分析多個交易對")
    symbols_to_analyze = [
        ("BTCUSDT", "spot"),
        ("ETHUSDT", "futures"),
        ("ADAUSDT", "spot")
    ]
    
    try:
        batch_results = batch_analyze_symbols(symbols_to_analyze, 60)
        print(f"批量分析完成，成功分析 {len([r for r in batch_results.values() if r is not None])} 個交易對")
    except Exception as e:
        print(f"批量分析失敗: {e}")
    
    # 範例4: 自定義分析
    print("\n4. 自定義分析範例")
    try:
        custom_result = custom_analysis_example()
        if custom_result is not None:
            print("自定義分析成功完成")
    except Exception as e:
        print(f"自定義分析失敗: {e}")
    
    print("\n=== 所有範例執行完成 ===")
    print("請查看 ./data/ 目錄下的分析報告檔案")


if __name__ == "__main__":
    main()
