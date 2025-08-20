# -*- coding: utf-8 -*-
"""
BTCUSDT 和 ETHUSDT 完整歷史時間框架分析
==========================================

本腳本專門用於分析 BTCUSDT 和 ETHUSDT 在現貨和永續合約市場
從最早可得資料日期開始的完整歷史時間框架特性。

根據上線時間：
- BTCUSDT 現貨: 2017年8月17日
- BTCUSDT 期貨: 2019年9月13日
- ETHUSDT 現貨: 2017年8月17日
- ETHUSDT 期貨: 2020年8月21日

分析內容：
1. 成本/波動比分析 (C/A)
2. 市場特性分析 (Variance Ratio)
3. 統計特性分析
4. 時間框架比較
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


def analyze_symbol_full_history(symbol: str, market_type: str) -> pd.DataFrame:
    """
    分析單個交易對從最早可得資料開始的完整歷史
    
    Args:
        symbol: 交易對名稱 (如 "BTCUSDT", "ETHUSDT")
        market_type: 市場類型 ("spot" 或 "futures")
    
    Returns:
        包含時間框架分析結果的DataFrame
    """
    print(f"\n=== 開始分析 {symbol} {market_type} 市場 (完整歷史) ===")
    
    # 根據上線時間設定資料天數
    # 使用一個很大的數字來確保獲取所有可用資料
    data_days = 3000  # 約8年多，確保涵蓋所有歷史資料
    
    # 創建配置
    config = BinanceAnalyzerConfig(
        symbol=symbol,
        market_type=market_type,
        data_days=data_days,
        auto_fetch=True,
        save_csv=True
        # 注意：報告格式設定已在配置文件中設定為只生成 txt
    )
    
    # 創建分析器並執行分析
    analyzer = BinanceTimeframeAnalyzer(config)
    report_df = analyzer.analyze()
    
    print(f"✅ {symbol} {market_type} 完整歷史分析完成")
    return report_df


def compare_btc_eth_full_history() -> Dict[str, pd.DataFrame]:
    """
    比較 BTCUSDT 和 ETHUSDT 在現貨和永續合約市場的完整歷史特性
    
    Returns:
        包含所有分析結果的字典
    """
    results = {}
    
    # 要分析的交易對和市場類型
    symbols_to_analyze = [
        ("BTCUSDT", "spot"),
        ("BTCUSDT", "futures"),
        ("ETHUSDT", "spot"),
        ("ETHUSDT", "futures")
    ]
    
    for symbol, market_type in symbols_to_analyze:
        try:
            report_df = analyze_symbol_full_history(symbol, market_type)
            results[f"{symbol}_{market_type}"] = report_df
            print(f"✅ {symbol} {market_type} 分析完成")
        except Exception as e:
            print(f"❌ {symbol} {market_type} 分析失敗: {e}")
            results[f"{symbol}_{market_type}"] = None
    
    return results


def print_summary_comparison(results: Dict[str, pd.DataFrame]):
    """
    打印分析結果摘要比較
    
    Args:
        results: 分析結果字典
    """
    print("\n" + "="*80)
    print("📊 BTCUSDT 和 ETHUSDT 完整歷史分析結果摘要")
    print("="*80)
    
    # 檢查哪些分析成功完成
    successful_analyses = {k: v for k, v in results.items() if v is not None and not v.empty}
    
    if not successful_analyses:
        print("❌ 沒有成功完成的分析")
        return
    
    print(f"✅ 成功完成 {len(successful_analyses)} 個分析")
    
    # 為每個成功的分析顯示最佳時間框架
    for analysis_name, report_df in successful_analyses.items():
        print(f"\n🔍 {analysis_name} 分析結果:")
        
        if 'C_over_A' in report_df.columns:
            # 找到最佳成本效率時間框架
            best_ca_row = report_df.loc[report_df['C_over_A'].idxmin()]
            print(f"   最佳成本效率: {best_ca_row['Timeframe']} (C/A: {best_ca_row['C_over_A']:.4f})")
        
        if 'VarianceRatio' in report_df.columns:
            # 找到最高趨勢性時間框架
            best_vr_row = report_df.loc[report_df['VarianceRatio'].idxmax()]
            print(f"   最高趨勢性: {best_vr_row['Timeframe']} (VR: {best_vr_row['VarianceRatio']:.4f})")
        
        # 顯示通過 C/A < 0.25 測試的時間框架
        if 'Pass_CA_0.25' in report_df.columns:
            passed_timeframes = report_df[report_df['Pass_CA_0.25']]['Timeframe'].tolist()
            if passed_timeframes:
                print(f"   通過C/A測試: {', '.join(passed_timeframes)}")
            else:
                print(f"   通過C/A測試: 無")
    
    print("\n" + "="*80)
    print("📋 報告文件已生成在 data/ 目錄中")
    print("   格式: {symbol}_{market_type}_timeframe_report_{date_range}.txt")
    print("="*80)


def main():
    """
    主函數 - 執行完整的歷史分析
    """
    print("🚀 開始 BTCUSDT 和 ETHUSDT 完整歷史時間框架分析")
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📅 上線時間參考:")
    print("   BTCUSDT 現貨: 2017年8月17日")
    print("   BTCUSDT 期貨: 2019年9月13日")
    print("   ETHUSDT 現貨: 2017年8月17日")
    print("   ETHUSDT 期貨: 2020年8月21日")
    
    try:
        # 執行分析
        results = compare_btc_eth_full_history()
        
        # 顯示摘要
        print_summary_comparison(results)
        
        print(f"\n✅ 分析完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ 分析過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
