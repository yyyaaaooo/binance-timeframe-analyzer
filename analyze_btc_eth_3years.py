# -*- coding: utf-8 -*-
"""
BTCUSDT 和 ETHUSDT 過去三年時間框架分析
==========================================

本腳本專門用於分析 BTCUSDT 和 ETHUSDT 在現貨和永續合約市場
過去三年的時間框架特性，幫助找到最適合的交易時間框架。

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


def analyze_symbol_3years(symbol: str, market_type: str) -> pd.DataFrame:
    """
    分析單個交易對過去三年的時間框架特性
    
    Args:
        symbol: 交易對名稱 (如 "BTCUSDT", "ETHUSDT")
        market_type: 市場類型 ("spot" 或 "futures")
    
    Returns:
        包含時間框架分析結果的DataFrame
    """
    print(f"\n=== 開始分析 {symbol} {market_type} 市場 (過去三年) ===")
    
    # 創建配置 - 使用1095天 (約3年)
    config = BinanceAnalyzerConfig(
        symbol=symbol,
        market_type=market_type,
        data_days=1095,  # 3年資料
        auto_fetch=True,
        save_csv=True,
        generate_csv_report=True,
        generate_txt_report=True,
        generate_md_report=True
    )
    
    # 創建分析器並執行分析
    analyzer = BinanceTimeframeAnalyzer(config)
    report_df = analyzer.analyze()
    
    print(f"✅ {symbol} {market_type} 三年分析完成")
    return report_df


def compare_btc_eth_3years() -> Dict[str, pd.DataFrame]:
    """
    比較 BTCUSDT 和 ETHUSDT 在現貨和永續合約市場的三年特性
    
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
            report_df = analyze_symbol_3years(symbol, market_type)
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
    print("📊 BTCUSDT 和 ETHUSDT 三年分析結果摘要")
    print("="*80)
    
    for key, df in results.items():
        if df is not None:
            print(f"\n🔍 {key} 分析結果:")
            print("-" * 50)
            
            # 顯示最佳成本效率的時間框架
            if 'C_over_A' in df.columns:
                best_ca = df.loc[df['C_over_A'].idxmin()]
                print(f"💰 最佳成本效率: {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
            
            # 顯示最高趨勢性的時間框架
            if 'VarianceRatio' in df.columns:
                best_vr = df.loc[df['VarianceRatio'].idxmax()]
                print(f"📈 最高趨勢性: {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
            
            # 顯示最低趨勢性的時間框架
            if 'VarianceRatio' in df.columns:
                worst_vr = df.loc[df['VarianceRatio'].idxmin()]
                print(f"📉 最低趨勢性: {worst_vr['Timeframe']} (VR: {worst_vr['VarianceRatio']:.4f})")
            
            # 顯示年化波動率
            if 'AnnualizedVolatility' in df.columns:
                avg_vol = df['AnnualizedVolatility'].mean()
                print(f"📊 平均年化波動率: {avg_vol:.2%}")
            
            print(f"📋 分析時間框架數量: {len(df)}")


def print_detailed_comparison(results: Dict[str, pd.DataFrame]):
    """
    打印詳細的比較表格
    
    Args:
        results: 分析結果字典
    """
    print("\n" + "="*100)
    print("📋 詳細比較表格")
    print("="*100)
    
    # 創建比較表格
    comparison_data = []
    
    for key, df in results.items():
        if df is not None:
            for _, row in df.iterrows():
                comparison_data.append({
                    'Symbol_Market': key,
                    'Timeframe': row['Timeframe'],
                    'C_over_A': row.get('C_over_A', float('nan')),
                    'VarianceRatio': row.get('VarianceRatio', float('nan')),
                    'AnnualizedVolatility': row.get('AnnualizedVolatility', float('nan')),
                    'Skewness': row.get('Skewness', float('nan')),
                    'Kurtosis': row.get('Kurtosis', float('nan')),
                    'Autocorrelation': row.get('Autocorrelation', float('nan')),
                    'MarketEfficiencyRatio': row.get('MarketEfficiencyRatio', float('nan'))
                })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # 格式化顯示
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 15)
        
        print(comparison_df.to_string(index=False, float_format='%.4f'))
        
        # 重置顯示選項
        pd.reset_option('display.max_columns')
        pd.reset_option('display.width')
        pd.reset_option('display.max_colwidth')


def main():
    """
    主函數 - 執行 BTCUSDT 和 ETHUSDT 三年分析
    """
    print("🚀 BTCUSDT 和 ETHUSDT 過去三年時間框架分析")
    print(f"⏰ 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📅 分析期間: 過去三年 (1095天)")
    
    try:
        # 執行分析
        results = compare_btc_eth_3years()
        
        # 打印摘要比較
        print_summary_comparison(results)
        
        # 打印詳細比較
        print_detailed_comparison(results)
        
        # 統計成功分析數量
        successful_analyses = len([r for r in results.values() if r is not None])
        print(f"\n✅ 分析完成！成功分析了 {successful_analyses}/4 個市場")
        
        # 提示查看報告檔案
        print("\n📁 詳細報告檔案已儲存至 ./data/ 目錄:")
        print("   - CSV 格式: 適合進一步分析")
        print("   - TXT 格式: 適合快速查看")
        print("   - MD 格式: 適合文檔記錄")
        
    except Exception as e:
        print(f"❌ 分析過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
