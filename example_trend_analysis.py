# -*- coding: utf-8 -*-
"""
趨勢分析使用範例
展示如何使用趨勢分析系統
"""

from trend_analysis_main import TrendAnalysisMain


def example_btc_spot_analysis():
    """BTC 現貨趨勢分析範例"""
    print("=== BTC 現貨趨勢分析範例 ===")
    
    # 創建分析器
    analyzer = TrendAnalysisMain(
        symbol='BTCUSDT',
        market_type='spot',
        data_days=365,  # 1年資料
        windows=[30, 60, 240]  # 30分鐘、1小時、4小時
    )
    
    # 執行分析
    results = analyzer.run_complete_analysis(save_results=True)
    
    print("分析完成！")
    return results


def example_eth_futures_analysis():
    """ETH 永續合約趨勢分析範例"""
    print("=== ETH 永續合約趨勢分析範例 ===")
    
    # 創建分析器
    analyzer = TrendAnalysisMain(
        symbol='ETHUSDT',
        market_type='futures',
        data_days=730,  # 2年資料
        windows=[30, 60, 240]  # 30分鐘、1小時、4小時
    )
    
    # 執行分析
    results = analyzer.run_complete_analysis(save_results=True)
    
    print("分析完成！")
    return results


def example_custom_analysis():
    """自定義趨勢分析範例"""
    print("=== 自定義趨勢分析範例 ===")
    
    # 可以修改這些參數來進行不同的分析
    symbol = 'BTCUSDT'  # 交易對
    market_type = 'spot'  # 市場類型: 'spot' 或 'futures'
    data_days = 1095  # 資料天數 (3年)
    windows = [15, 30, 60, 240]  # 滾動窗格 (分鐘)
    
    # 創建分析器
    analyzer = TrendAnalysisMain(
        symbol=symbol,
        market_type=market_type,
        data_days=data_days,
        windows=windows
    )
    
    # 執行分析
    results = analyzer.run_complete_analysis(save_results=True)
    
    print("分析完成！")
    return results


def main():
    """主函數"""
    print("趨勢分析系統使用範例")
    print("=" * 50)
    
    # 選擇要執行的範例
    print("請選擇要執行的分析範例:")
    print("1. BTC 現貨趨勢分析 (1年資料)")
    print("2. ETH 永續合約趨勢分析 (2年資料)")
    print("3. 自定義趨勢分析 (3年資料)")
    
    choice = input("請輸入選擇 (1-3): ").strip()
    
    try:
        if choice == '1':
            results = example_btc_spot_analysis()
        elif choice == '2':
            results = example_eth_futures_analysis()
        elif choice == '3':
            results = example_custom_analysis()
        else:
            print("無效選擇，執行預設的 BTC 現貨分析...")
            results = example_btc_spot_analysis()
        
        # 顯示結果摘要
        if results:
            print("\n=== 分析結果摘要 ===")
            print(f"趨勢檢測結果: {len(results['trend_results'])} 個時間框架")
            print(f"時段分析: 完成")
            print(f"統計檢定: 完成")
            print(f"視覺化圖表: {len(results['figures'])} 個圖表")
            print("詳細結果請查看生成的報告和圖表檔案")
        
    except Exception as e:
        print(f"分析過程中發生錯誤: {e}")
        print("請檢查網路連接和依賴項是否正確安裝")


if __name__ == "__main__":
    main()
