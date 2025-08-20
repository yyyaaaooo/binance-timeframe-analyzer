# -*- coding: utf-8 -*-
"""
趨勢分析主腳本
整合所有模組並提供完整的趨勢分析流程
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# 導入自定義模組
from trend_detector import TrendDetector
from trend_statistics import TrendStatistics
from time_period_analyzer import TimePeriodAnalyzer
from trend_visualizer import TrendVisualizer
from binance_timeframe_analyzer import BinanceTimeframeAnalyzer
from binance_analyzer_config import BinanceAnalyzerConfig


class TrendAnalysisMain:
    """趨勢分析主類別"""
    
    def __init__(self, symbol: str = 'BTCUSDT', market_type: str = 'spot', 
                 data_days: int = 1095, windows: List[int] = [30, 60, 240]):
        """
        初始化趨勢分析主類別
        
        Args:
            symbol: 交易對符號
            market_type: 市場類型 ('spot' 或 'futures')
            data_days: 資料天數
            windows: 滾動窗格大小（分鐘）
        """
        self.symbol = symbol
        self.market_type = market_type
        self.data_days = data_days
        self.windows = windows
        
        # 初始化組件
        self.config = BinanceAnalyzerConfig(
            symbol=symbol,
            market_type=market_type,
            data_days=data_days,
            auto_fetch=True,
            save_csv=True
        )
        
        self.analyzer = BinanceTimeframeAnalyzer(self.config)
        self.trend_detector = TrendDetector(windows=windows)
        self.statistics = TrendStatistics()
        self.time_analyzer = TimePeriodAnalyzer()
        self.visualizer = TrendVisualizer()
        
        # 結果儲存
        self.trend_results = {}
        self.time_analysis_results = {}
        self.statistical_results = {}
        
    def load_data(self) -> pd.DataFrame:
        """載入資料"""
        print("=== 載入資料 ===")
        try:
            df = self.analyzer.load_or_fetch_data()
            print(f"成功載入 {len(df)} 筆資料")
            print(f"資料時間範圍: {df.index.min()} 到 {df.index.max()}")
            return df
        except Exception as e:
            print(f"資料載入失敗: {e}")
            raise
    
    def detect_trends(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """檢測趨勢"""
        print("\n=== 趨勢檢測 ===")
        try:
            trend_results = self.trend_detector.detect_trends(df)
            
            for timeframe, result_df in trend_results.items():
                print(f"{timeframe} 時間框架: {len(result_df)} 筆趨勢分析結果")
                print(f"  趨勢期間: {result_df.index.min()} 到 {result_df.index.max()}")
                
                # 統計趨勢分類
                trend_counts = result_df['trend_label'].value_counts()
                print(f"  趨勢分類統計:")
                for label, count in trend_counts.items():
                    proportion = count / len(result_df) * 100
                    print(f"    {label}: {count} ({proportion:.1f}%)")
            
            self.trend_results = trend_results
            return trend_results
            
        except Exception as e:
            print(f"趨勢檢測失敗: {e}")
            raise
    
    def analyze_time_periods(self, trend_data: pd.DataFrame) -> Dict:
        """分析時段"""
        print("\n=== 時段分析 ===")
        try:
            # 重置索引以便處理時間戳記
            trend_data_reset = trend_data.reset_index()
            
            time_analysis = self.time_analyzer.analyze_time_periods(trend_data_reset)
            
            if time_analysis:
                print(f"時區: {time_analysis['timezone']}")
                print(f"小時彙總: {len(time_analysis['hour_aggregation'])} 個小時")
                print(f"星期彙總: {len(time_analysis['weekday_aggregation'])} 個星期")
                print(f"月份彙總: {len(time_analysis['month_aggregation'])} 個月份")
                
                # 顯示熱力圖統計
                if not time_analysis['heatmap_data'].empty:
                    print(f"熱力圖數據: {time_analysis['heatmap_data'].shape}")
                
                # 顯示趨勢方向統計
                direction_stats = time_analysis['direction_stats']
                if direction_stats:
                    print(f"趨勢方向統計:")
                    print(f"  總趨勢數: {direction_stats['total_trends']}")
                    print(f"  多頭趨勢: {direction_stats['long_trends']} ({direction_stats['long_proportion']:.1%})")
                    print(f"  空頭趨勢: {direction_stats['short_trends']} ({direction_stats['short_proportion']:.1%})")
            
            return time_analysis
            
        except Exception as e:
            print(f"時段分析失敗: {e}")
            raise
    
    def perform_statistical_tests(self, trend_data: pd.DataFrame, time_analysis: Dict) -> Dict:
        """執行統計檢定"""
        print("\n=== 統計檢定 ===")
        try:
            statistical_results = {}
            
            # 重置索引
            trend_data_reset = trend_data.reset_index()
            
            # 按小時執行綜合統計檢定
            print("執行按小時的統計檢定...")
            hour_tests = self.statistics.perform_comprehensive_tests(
                time_analysis['processed_data'], 
                'timestamp', 
                'trend_score', 
                'hour'
            )
            statistical_results['hour_tests'] = hour_tests
            
            # 按星期執行綜合統計檢定
            print("執行按星期的統計檢定...")
            weekday_tests = self.statistics.perform_comprehensive_tests(
                time_analysis['processed_data'], 
                'timestamp', 
                'trend_score', 
                'weekday'
            )
            statistical_results['weekday_tests'] = weekday_tests
            
            # 顯示檢定結果
            for test_type, results in statistical_results.items():
                print(f"\n{test_type} 檢定結果:")
                
                if 'chi_square_test' in results:
                    chi2_result = results['chi_square_test']
                    if 'is_significant' in chi2_result:
                        print(f"  卡方檢定: {'顯著' if chi2_result['is_significant'] else '不顯著'} (p={chi2_result.get('p_value', 'N/A'):.4f})")
                
                if 'anova_test' in results:
                    anova_result = results['anova_test']
                    if 'is_significant' in anova_result:
                        print(f"  ANOVA 檢定: {'顯著' if anova_result['is_significant'] else '不顯著'} (p={anova_result.get('p_value', 'N/A'):.4f})")
                
                if 'kruskal_wallis_test' in results:
                    kw_result = results['kruskal_wallis_test']
                    if 'is_significant' in kw_result:
                        print(f"  Kruskal-Wallis 檢定: {'顯著' if kw_result['is_significant'] else '不顯著'} (p={kw_result.get('p_value', 'N/A'):.4f})")
            
            self.statistical_results = statistical_results
            return statistical_results
            
        except Exception as e:
            print(f"統計檢定失敗: {e}")
            raise
    
    def create_visualizations(self, trend_data: pd.DataFrame, time_analysis: Dict, 
                            save_dir: Optional[str] = None) -> List:
        """創建視覺化圖表"""
        print("\n=== 創建視覺化圖表 ===")
        try:
            if save_dir is None:
                save_dir = f"trend_analysis_results_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 重置索引
            trend_data_reset = trend_data.reset_index()
            
            # 創建綜合儀表板
            figures = self.visualizer.create_comprehensive_dashboard(
                trend_data_reset, 
                time_analysis, 
                save_dir
            )
            
            print(f"已創建 {len(figures)} 個圖表")
            print(f"圖表儲存目錄: {save_dir}")
            
            return figures
            
        except Exception as e:
            print(f"視覺化創建失敗: {e}")
            raise
    
    def generate_report(self, trend_data: pd.DataFrame, time_analysis: Dict, 
                       statistical_results: Dict, save_path: Optional[str] = None) -> str:
        """生成分析報告"""
        print("\n=== 生成分析報告 ===")
        try:
            if save_path is None:
                save_path = f"trend_analysis_report_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            report_lines = []
            
            # 報告標題
            report_lines.append("=" * 80)
            report_lines.append(f"趨勢分析報告 - {self.symbol} ({self.market_type})")
            report_lines.append("=" * 80)
            report_lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"分析時間範圍: {trend_data.index.min()} 到 {trend_data.index.max()}")
            report_lines.append(f"滾動窗格: {self.windows} 分鐘")
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
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"報告已儲存至: {save_path}")
            return report_content
            
        except Exception as e:
            print(f"報告生成失敗: {e}")
            raise
    
    def run_complete_analysis(self, save_results: bool = True) -> Dict:
        """執行完整分析流程"""
        print("=" * 80)
        print(f"開始趨勢分析 - {self.symbol} ({self.market_type})")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            # 1. 載入資料
            df = self.load_data()
            
            # 2. 檢測趨勢（使用最長的時間框架進行時段分析）
            trend_results = self.detect_trends(df)
            
            # 3. 時段分析（使用最長的時間框架）
            longest_timeframe = f"{max(self.windows)}m"
            if longest_timeframe in trend_results:
                trend_data = trend_results[longest_timeframe]
                time_analysis = self.analyze_time_periods(trend_data)
                
                # 4. 統計檢定
                statistical_results = self.perform_statistical_tests(trend_data, time_analysis)
                
                # 5. 創建視覺化
                if save_results:
                    save_dir = f"trend_analysis_results_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    figures = self.create_visualizations(trend_data, time_analysis, save_dir)
                else:
                    figures = self.create_visualizations(trend_data, time_analysis)
                
                # 6. 生成報告
                if save_results:
                    report_content = self.generate_report(trend_data, time_analysis, statistical_results)
                else:
                    report_content = self.generate_report(trend_data, time_analysis, statistical_results, 
                                                        save_path=None)
                
                # 7. 整理結果
                results = {
                    'trend_results': trend_results,
                    'time_analysis': time_analysis,
                    'statistical_results': statistical_results,
                    'figures': figures,
                    'report_content': report_content
                }
                
                elapsed_time = time.time() - start_time
                print(f"\n分析完成！總耗時: {elapsed_time:.2f} 秒")
                
                return results
                
            else:
                raise ValueError(f"找不到 {longest_timeframe} 時間框架的趨勢數據")
                
        except Exception as e:
            print(f"分析失敗: {e}")
            raise


def main():
    """主函數"""
    # 設定分析參數
    symbol = 'BTCUSDT'
    market_type = 'spot'  # 或 'futures'
    data_days = 1095  # 3年
    windows = [30, 60, 240]  # 30分鐘、1小時、4小時
    
    # 創建分析器
    analyzer = TrendAnalysisMain(
        symbol=symbol,
        market_type=market_type,
        data_days=data_days,
        windows=windows
    )
    
    # 執行完整分析
    results = analyzer.run_complete_analysis(save_results=True)
    
    print("\n分析完成！")
    print("結果包含:")
    print("- 趨勢檢測結果")
    print("- 時段分析結果")
    print("- 統計檢定結果")
    print("- 視覺化圖表")
    print("- 分析報告")


if __name__ == "__main__":
    main()
