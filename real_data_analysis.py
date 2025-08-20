# -*- coding: utf-8 -*-
"""
真實數據趨勢分析
使用3年真實交易數據進行趨勢分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import os

# 導入自定義模組
from trend_detector import TrendDetector
from trend_statistics import TrendStatistics
from time_period_analyzer import TimePeriodAnalyzer
from trend_visualizer import TrendVisualizer

warnings.filterwarnings("ignore")


def load_real_data(symbol='BTCUSDT', market_type='spot', years=3):
    """載入真實交易數據"""
    print(f"=== 載入 {symbol} {market_type} 數據 ===")
    
    try:
        # 構建檔案路徑
        filename = f"{symbol.lower()}_{market_type}_1m.csv"
        filepath = os.path.join('data', filename)
        
        if not os.path.exists(filepath):
            print(f"檔案不存在: {filepath}")
            return None
        
        print(f"載入檔案: {filepath}")
        
        # 載入數據
        df = pd.read_csv(filepath)
        
        # 轉換時間戳記
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # 設定時區
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        
        # 轉換資料類型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df = df.set_index('timestamp').sort_index()
        
        # 只取最近 N 年的數據
        end_date = df.index.max()
        start_date = end_date - timedelta(days=365 * years)
        recent_df = df[df.index >= start_date]
        
        print(f"原始數據: {len(df)} 筆")
        print(f"篩選後數據: {len(recent_df)} 筆")
        print(f"數據時間範圍: {recent_df.index.min()} 到 {recent_df.index.max()}")
        print(f"數據欄位: {list(recent_df.columns)}")
        
        # 基本統計
        print(f"價格範圍: ${recent_df['close'].min():.2f} - ${recent_df['close'].max():.2f}")
        print(f"平均價格: ${recent_df['close'].mean():.2f}")
        print(f"價格標準差: ${recent_df['close'].std():.2f}")
        
        return recent_df
        
    except Exception as e:
        print(f"載入數據失敗: {e}")
        return None


def analyze_trends(df, windows=[30, 60, 240]):
    """分析趨勢"""
    print(f"\n=== 趨勢檢測分析 ===")
    print(f"使用時間框架: {windows} 分鐘")
    
    # 創建趨勢檢測器
    detector = TrendDetector(windows=windows)
    
    # 執行趨勢檢測
    trend_results = detector.detect_trends(df)
    
    # 顯示結果
    for timeframe, result_df in trend_results.items():
        print(f"\n{timeframe} 時間框架分析結果:")
        print(f"  總分析筆數: {len(result_df)}")
        
        # 趨勢分類統計
        trend_counts = result_df['trend_label'].value_counts()
        print(f"  趨勢分類統計:")
        for label, count in trend_counts.items():
            proportion = count / len(result_df) * 100
            print(f"    {label}: {count} ({proportion:.1f}%)")
        
        # 趨勢分數統計
        print(f"  趨勢分數統計:")
        print(f"    平均值: {result_df['trend_score'].mean():.2f}")
        print(f"    標準差: {result_df['trend_score'].std():.2f}")
        print(f"    最小值: {result_df['trend_score'].min():.2f}")
        print(f"    最大值: {result_df['trend_score'].max():.2f}")
        
        # 顯示一些具體例子
        print(f"  趨勢期間範例:")
        trend_periods = result_df[result_df['trend_label'] == 'trend'].head(3)
        for idx, row in trend_periods.iterrows():
            print(f"    {idx}: 分數={row['trend_score']:.1f}, ADX={row['adx']:.1f}, R²={row['r_squared']:.3f}")
    
    return trend_results


def analyze_time_periods(trend_data):
    """分析時段"""
    print(f"\n=== 時段分析 ===")
    
    # 重置索引以便處理時間戳記
    trend_data_reset = trend_data.reset_index()
    
    # 創建時段分析器
    time_analyzer = TimePeriodAnalyzer()
    
    # 執行時段分析
    time_analysis = time_analyzer.analyze_time_periods(trend_data_reset)
    
    if time_analysis:
        print(f"時區: {time_analysis['timezone']}")
        
        # 小時分析
        if 'hour_aggregation' in time_analysis:
            hour_agg = time_analysis['hour_aggregation']
            print(f"\n按小時分析 (共 {len(hour_agg)} 個小時):")
            
            # 找出趨勢比例最高和最低的時段
            trend_proportions = {hour: stats['trend_proportion'] for hour, stats in hour_agg.items()}
            max_trend_hour = max(trend_proportions.keys(), key=lambda h: trend_proportions[h])
            min_trend_hour = min(trend_proportions.keys(), key=lambda h: trend_proportions[h])
            
            print(f"  趨勢比例最高的時段: {max_trend_hour} 時 ({trend_proportions[max_trend_hour]:.1%})")
            print(f"  趨勢比例最低的時段: {min_trend_hour} 時 ({trend_proportions[min_trend_hour]:.1%})")
            
            # 顯示前10個趨勢比例最高的時段
            sorted_hours = sorted(trend_proportions.items(), key=lambda x: x[1], reverse=True)
            print(f"  趨勢比例前10名:")
            for hour, prop in sorted_hours[:10]:
                stats = hour_agg[hour]
                print(f"    {hour:2d}時: {prop:.1%} (平均分數: {stats['avg_trend_score']:.1f}, 樣本數: {stats['total_count']})")
        
        # 星期分析
        if 'weekday_aggregation' in time_analysis:
            weekday_agg = time_analysis['weekday_aggregation']
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            print(f"\n按星期分析:")
            for weekday in sorted(weekday_agg.keys()):
                stats = weekday_agg[weekday]
                weekday_name = weekday_names[weekday]
                print(f"  {weekday_name}: 趨勢比例={stats['trend_proportion']:.1%}, "
                      f"平均分數={stats['avg_trend_score']:.1f}, 樣本數={stats['total_count']}")
        
        # 趨勢方向分析
        if 'direction_stats' in time_analysis:
            direction_stats = time_analysis['direction_stats']
            print(f"\n趨勢方向分析:")
            print(f"  總趨勢數: {direction_stats['total_trends']}")
            print(f"  多頭趨勢: {direction_stats['long_trends']} ({direction_stats['long_proportion']:.1%})")
            print(f"  空頭趨勢: {direction_stats['short_trends']} ({direction_stats['short_proportion']:.1%})")
    
    return time_analysis


def perform_statistical_tests(trend_data, time_analysis):
    """執行統計檢定"""
    print(f"\n=== 統計檢定 ===")
    
    # 重置索引
    trend_data_reset = trend_data.reset_index()
    
    # 創建統計檢定器
    stats = TrendStatistics()
    
    # 按小時執行統計檢定
    print("執行按小時的統計檢定...")
    hour_tests = stats.perform_comprehensive_tests(
        time_analysis['processed_data'], 
        'timestamp', 
        'trend_score', 
        'hour'
    )
    
    # 顯示檢定結果
    if 'hour_tests' in hour_tests:
        hour_test_results = hour_tests['hour_tests']
        
        print(f"\n統計檢定結果:")
        
        if 'chi_square_test' in hour_test_results:
            chi2_result = hour_test_results['chi_square_test']
            if 'is_significant' in chi2_result:
                significance = "顯著" if chi2_result['is_significant'] else "不顯著"
                p_value = chi2_result.get('p_value', 'N/A')
                chi2_stat = chi2_result.get('chi2_statistic', 'N/A')
                print(f"  卡方檢定: {significance}")
                print(f"    統計量: {chi2_stat:.4f}")
                print(f"    p值: {p_value:.4f}")
        
        if 'anova_test' in hour_test_results:
            anova_result = hour_test_results['anova_test']
            if 'is_significant' in anova_result:
                significance = "顯著" if anova_result['is_significant'] else "不顯著"
                p_value = anova_result.get('p_value', 'N/A')
                f_stat = anova_result.get('f_statistic', 'N/A')
                print(f"  ANOVA 檢定: {significance}")
                print(f"    F統計量: {f_stat:.4f}")
                print(f"    p值: {p_value:.4f}")
        
        if 'kruskal_wallis_test' in hour_test_results:
            kw_result = hour_test_results['kruskal_wallis_test']
            if 'is_significant' in kw_result:
                significance = "顯著" if kw_result['is_significant'] else "不顯著"
                p_value = kw_result.get('p_value', 'N/A')
                h_stat = kw_result.get('h_statistic', 'N/A')
                print(f"  Kruskal-Wallis 檢定: {significance}")
                print(f"    H統計量: {h_stat:.4f}")
                print(f"    p值: {p_value:.4f}")
    
    return hour_tests


def create_visualizations(trend_data, time_analysis, symbol, market_type):
    """創建視覺化圖表"""
    print(f"\n=== 創建視覺化圖表 ===")
    
    # 重置索引
    trend_data_reset = trend_data.reset_index()
    
    # 創建視覺化器
    visualizer = TrendVisualizer()
    
    # 創建圖表（儲存到結果目錄）
    save_dir = f"real_analysis_results_{symbol}_{market_type}"
    figures = visualizer.create_comprehensive_dashboard(
        trend_data_reset, 
        time_analysis, 
        save_dir
    )
    
    print(f"成功創建 {len(figures)} 個圖表")
    print(f"圖表儲存目錄: {save_dir}")
    
    # 顯示圖表說明
    chart_descriptions = [
        "24×7 趨勢熱力圖 - 顯示星期×小時的趨勢比例",
        "趨勢分數箱形圖 - 比較各小時的趨勢強度",
        "趨勢方向玫瑰圖 - 展示多空趨勢分佈",
        "趨勢比例長條圖 - 堆疊式時段分析",
        "ADX vs R² 散點圖 - 分析技術指標關係"
    ]
    
    print(f"\n生成的圖表:")
    for i, description in enumerate(chart_descriptions, 1):
        print(f"  {i}. {description}")
    
    return figures, save_dir


def generate_report(trend_data, time_analysis, statistical_results, symbol, market_type, save_dir):
    """生成分析報告"""
    print(f"\n=== 生成分析報告 ===")
    
    report_path = f"real_analysis_report_{symbol}_{market_type}.txt"
    
    report_lines = []
    
    # 報告標題
    report_lines.append("=" * 80)
    report_lines.append(f"真實數據趨勢分析報告 - {symbol} ({market_type})")
    report_lines.append("=" * 80)
    report_lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"分析時間範圍: {trend_data.index.min()} 到 {trend_data.index.max()}")
    report_lines.append(f"滾動窗格: [30, 60, 240] 分鐘")
    report_lines.append("")
    
    # 基本統計
    report_lines.append("一、基本統計")
    report_lines.append("-" * 40)
    total_observations = len(trend_data)
    trend_counts = trend_data['trend_label'].value_counts()
    
    report_lines.append(f"總觀察數: {total_observations}")
    for label, count in trend_counts.items():
        proportion = count / total_observations * 100
        report_lines.append(f"{label}: {count} ({proportion:.1f}%)")
    
    # 趨勢分數統計
    report_lines.append("")
    report_lines.append("趨勢分數統計:")
    trend_score_stats = trend_data['trend_score'].describe()
    report_lines.append(f"  平均值: {trend_score_stats['mean']:.2f}")
    report_lines.append(f"  標準差: {trend_score_stats['std']:.2f}")
    report_lines.append(f"  最小值: {trend_score_stats['min']:.2f}")
    report_lines.append(f"  最大值: {trend_score_stats['max']:.2f}")
    
    # 時段分析結果
    report_lines.append("")
    report_lines.append("二、時段分析結果")
    report_lines.append("-" * 40)
    
    # 小時分析
    if 'hour_aggregation' in time_analysis:
        report_lines.append("按小時分析:")
        hour_agg = time_analysis['hour_aggregation']
        for hour in sorted(hour_agg.keys()):
            stats = hour_agg[hour]
            report_lines.append(f"  {hour:2d}時: 趨勢比例={stats['trend_proportion']:.1%}, "
                              f"平均分數={stats['avg_trend_score']:.1f}, "
                              f"樣本數={stats['total_count']}")
    
    # 星期分析
    if 'weekday_aggregation' in time_analysis:
        report_lines.append("")
        report_lines.append("按星期分析:")
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_agg = time_analysis['weekday_aggregation']
        for weekday in sorted(weekday_agg.keys()):
            stats = weekday_agg[weekday]
            weekday_name = weekday_names[weekday]
            report_lines.append(f"  {weekday_name}: 趨勢比例={stats['trend_proportion']:.1%}, "
                              f"平均分數={stats['avg_trend_score']:.1f}, "
                              f"樣本數={stats['total_count']}")
    
    # 趨勢方向分析
    if 'direction_stats' in time_analysis:
        report_lines.append("")
        report_lines.append("趨勢方向分析:")
        direction_stats = time_analysis['direction_stats']
        report_lines.append(f"  總趨勢數: {direction_stats['total_trends']}")
        report_lines.append(f"  多頭趨勢: {direction_stats['long_trends']} ({direction_stats['long_proportion']:.1%})")
        report_lines.append(f"  空頭趨勢: {direction_stats['short_trends']} ({direction_stats['short_proportion']:.1%})")
    
    # 統計檢定結果
    report_lines.append("")
    report_lines.append("三、統計檢定結果")
    report_lines.append("-" * 40)
    
    for test_type, results in statistical_results.items():
        report_lines.append(f"{test_type}:")
        
        if 'chi_square_test' in results:
            chi2_result = results['chi_square_test']
            if 'is_significant' in chi2_result:
                significance = "顯著" if chi2_result['is_significant'] else "不顯著"
                p_value = chi2_result.get('p_value', 'N/A')
                report_lines.append(f"  卡方檢定: {significance} (p={p_value:.4f})")
        
        if 'anova_test' in results:
            anova_result = results['anova_test']
            if 'is_significant' in anova_result:
                significance = "顯著" if anova_result['is_significant'] else "不顯著"
                p_value = anova_result.get('p_value', 'N/A')
                report_lines.append(f"  ANOVA 檢定: {significance} (p={p_value:.4f})")
        
        if 'kruskal_wallis_test' in results:
            kw_result = results['kruskal_wallis_test']
            if 'is_significant' in kw_result:
                significance = "顯著" if kw_result['is_significant'] else "不顯著"
                p_value = kw_result.get('p_value', 'N/A')
                report_lines.append(f"  Kruskal-Wallis 檢定: {significance} (p={p_value:.4f})")
    
    # 結論
    report_lines.append("")
    report_lines.append("四、結論")
    report_lines.append("-" * 40)
    
    # 分析統計檢定結果
    has_significant_differences = False
    for test_type, results in statistical_results.items():
        for test_name in ['chi_square_test', 'anova_test', 'kruskal_wallis_test']:
            if test_name in results and 'is_significant' in results[test_name]:
                if results[test_name]['is_significant']:
                    has_significant_differences = True
                    break
    
    if has_significant_differences:
        report_lines.append("統計檢定顯示趨勢在不同時段間存在顯著差異，")
        report_lines.append("表明趨勢確實集中在某些特定時段。")
        
        # 找出趨勢比例最高的時段
        if 'hour_aggregation' in time_analysis:
            hour_agg = time_analysis['hour_aggregation']
            max_trend_hour = max(hour_agg.keys(), key=lambda h: hour_agg[h]['trend_proportion'])
            max_trend_prop = hour_agg[max_trend_hour]['trend_proportion']
            report_lines.append(f"趨勢比例最高的時段為 {max_trend_hour} 時 ({max_trend_prop:.1%})。")
    else:
        report_lines.append("統計檢定顯示趨勢在不同時段間無顯著差異，")
        report_lines.append("表明趨勢分佈相對均勻，無明顯的時段集中性。")
    
    # 寫入檔案
    report_content = "\n".join(report_lines)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"報告已儲存至: {report_path}")
    return report_content


def main():
    """主函數"""
    print("真實數據趨勢分析")
    print("=" * 60)
    
    # 分析參數
    symbol = 'BTCUSDT'
    market_type = 'spot'  # 或 'futures'
    years = 3
    windows = [30, 60, 240]  # 30分鐘、1小時、4小時
    
    try:
        # 1. 載入真實數據
        df = load_real_data(symbol, market_type, years)
        if df is None:
            print("無法載入數據，分析結束")
            return
        
        # 2. 趨勢檢測分析
        trend_results = analyze_trends(df, windows)
        
        # 3. 時段分析（使用最長的時間框架）
        longest_timeframe = f"{max(windows)}m"
        if longest_timeframe in trend_results:
            trend_data = trend_results[longest_timeframe]
            time_analysis = analyze_time_periods(trend_data)
            
            # 4. 統計檢定
            statistical_results = perform_statistical_tests(trend_data, time_analysis)
            
            # 5. 創建視覺化
            figures, save_dir = create_visualizations(trend_data, time_analysis, symbol, market_type)
            
            # 6. 生成報告
            report_content = generate_report(trend_data, time_analysis, statistical_results, symbol, market_type, save_dir)
            
            # 7. 總結
            print("\n" + "=" * 60)
            print("分析完成！")
            print("=" * 60)
            print("本次分析包含:")
            print(f"✓ {symbol} {market_type} 3年真實數據")
            print("✓ 多時間框架趨勢檢測")
            print("✓ 時段分析（小時、星期）")
            print("✓ 統計檢定（卡方、ANOVA、Kruskal-Wallis）")
            print("✓ 視覺化圖表生成")
            print(f"✓ 結果儲存到 {save_dir} 目錄")
            print("✓ 詳細分析報告")
            print("\n您可以查看生成的圖表和報告來了解詳細的分析結果。")
        
    except Exception as e:
        print(f"分析過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
