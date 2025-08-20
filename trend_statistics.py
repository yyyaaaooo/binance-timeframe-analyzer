# -*- coding: utf-8 -*-
"""
統計檢定模組
實現各種統計檢定方法用於趨勢分析
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats
from scipy.stats import chi2_contingency, f_oneway, kruskal
import warnings

warnings.filterwarnings("ignore")


class TrendStatistics:
    """趨勢統計檢定器"""
    
    def __init__(self):
        """初始化統計檢定器"""
        pass
    
    def chi_square_test(self, observed_counts: np.ndarray, expected_counts: Optional[np.ndarray] = None) -> Dict:
        """
        卡方檢定：比較觀察次數與期望次數
        
        Args:
            observed_counts: 觀察次數
            expected_counts: 期望次數（如果為 None，則假設均勻分佈）
            
        Returns:
            檢定結果字典
        """
        try:
            if expected_counts is None:
                # 假設均勻分佈
                expected_counts = np.full_like(observed_counts, np.mean(observed_counts))
            
            # 執行卡方檢定
            chi2_stat, p_value, dof, expected = chi2_contingency(
                [observed_counts, expected_counts]
            )
            
            result = {
                'test_name': 'Chi-Square Test',
                'chi2_statistic': chi2_stat,
                'p_value': p_value,
                'degrees_of_freedom': dof,
                'is_significant': p_value < 0.05,
                'observed_counts': observed_counts,
                'expected_counts': expected_counts
            }
            
            return result
            
        except Exception as e:
            print(f"卡方檢定錯誤: {e}")
            return {
                'test_name': 'Chi-Square Test',
                'error': str(e)
            }
    
    def anova_test(self, groups: List[np.ndarray]) -> Dict:
        """
        ANOVA 檢定：比較多組數據的均值差異
        
        Args:
            groups: 多組數據列表
            
        Returns:
            檢定結果字典
        """
        try:
            # 執行 ANOVA 檢定
            f_stat, p_value = f_oneway(*groups)
            
            # 計算各組統計量
            group_stats = []
            for i, group in enumerate(groups):
                group_stats.append({
                    'group': i,
                    'mean': np.mean(group),
                    'std': np.std(group),
                    'count': len(group)
                })
            
            result = {
                'test_name': 'ANOVA Test',
                'f_statistic': f_stat,
                'p_value': p_value,
                'is_significant': p_value < 0.05,
                'group_stats': group_stats
            }
            
            return result
            
        except Exception as e:
            print(f"ANOVA 檢定錯誤: {e}")
            return {
                'test_name': 'ANOVA Test',
                'error': str(e)
            }
    
    def kruskal_wallis_test(self, groups: List[np.ndarray]) -> Dict:
        """
        Kruskal-Wallis 檢定：非參數版本的多組比較
        
        Args:
            groups: 多組數據列表
            
        Returns:
            檢定結果字典
        """
        try:
            # 執行 Kruskal-Wallis 檢定
            h_stat, p_value = kruskal(*groups)
            
            # 計算各組統計量
            group_stats = []
            for i, group in enumerate(groups):
                group_stats.append({
                    'group': i,
                    'median': np.median(group),
                    'mean_rank': np.mean([stats.rankdata(np.concatenate(groups))[sum(len(g) for g in groups[:i]):sum(len(g) for g in groups[:i+1])]])
                })
            
            result = {
                'test_name': 'Kruskal-Wallis Test',
                'h_statistic': h_stat,
                'p_value': p_value,
                'is_significant': p_value < 0.05,
                'group_stats': group_stats
            }
            
            return result
            
        except Exception as e:
            print(f"Kruskal-Wallis 檢定錯誤: {e}")
            return {
                'test_name': 'Kruskal-Wallis Test',
                'error': str(e)
            }
    
    def benjamini_hochberg_correction(self, p_values: np.ndarray, alpha: float = 0.05) -> Dict:
        """
        Benjamini-Hochberg 多重比較校正
        
        Args:
            p_values: p 值陣列
            alpha: 顯著性水準
            
        Returns:
            校正結果字典
        """
        try:
            n = len(p_values)
            if n == 0:
                return {'rejected': [], 'corrected_p_values': []}
            
            # 排序 p 值
            sorted_indices = np.argsort(p_values)
            sorted_p_values = p_values[sorted_indices]
            
            # 計算校正後的 p 值
            corrected_p_values = np.zeros_like(p_values)
            for i, (idx, p_val) in enumerate(zip(sorted_indices, sorted_p_values)):
                corrected_p_values[idx] = min(p_val * n / (i + 1), 1.0)
            
            # 找出被拒絕的假設
            rejected = corrected_p_values < alpha
            
            result = {
                'original_p_values': p_values,
                'corrected_p_values': corrected_p_values,
                'rejected': rejected,
                'alpha': alpha,
                'rejected_count': np.sum(rejected)
            }
            
            return result
            
        except Exception as e:
            print(f"Benjamini-Hochberg 校正錯誤: {e}")
            return {
                'error': str(e)
            }
    
    def bootstrap_confidence_interval(self, data: np.ndarray, statistic_func: callable, 
                                    n_bootstrap: int = 1000, confidence_level: float = 0.95) -> Dict:
        """
        Bootstrap 信賴區間計算
        
        Args:
            data: 原始數據
            statistic_func: 統計量函數
            n_bootstrap: Bootstrap 重複次數
            confidence_level: 信賴水準
            
        Returns:
            Bootstrap 結果字典
        """
        try:
            n = len(data)
            if n == 0:
                return {'confidence_interval': (None, None), 'bootstrap_samples': []}
            
            # 計算原始統計量
            original_statistic = statistic_func(data)
            
            # Bootstrap 重複抽樣
            bootstrap_samples = []
            for _ in range(n_bootstrap):
                # 重複抽樣
                bootstrap_sample = np.random.choice(data, size=n, replace=True)
                bootstrap_statistic = statistic_func(bootstrap_sample)
                bootstrap_samples.append(bootstrap_statistic)
            
            bootstrap_samples = np.array(bootstrap_samples)
            
            # 計算信賴區間
            alpha = 1 - confidence_level
            lower_percentile = (alpha / 2) * 100
            upper_percentile = (1 - alpha / 2) * 100
            
            confidence_interval = (
                np.percentile(bootstrap_samples, lower_percentile),
                np.percentile(bootstrap_samples, upper_percentile)
            )
            
            result = {
                'original_statistic': original_statistic,
                'bootstrap_samples': bootstrap_samples,
                'confidence_interval': confidence_interval,
                'confidence_level': confidence_level,
                'bootstrap_mean': np.mean(bootstrap_samples),
                'bootstrap_std': np.std(bootstrap_samples)
            }
            
            return result
            
        except Exception as e:
            print(f"Bootstrap 信賴區間計算錯誤: {e}")
            return {
                'error': str(e)
            }
    
    def calculate_trend_proportions(self, trend_labels: np.ndarray, time_periods: np.ndarray) -> Dict:
        """
        計算各時段的趨勢比例
        
        Args:
            trend_labels: 趨勢標籤陣列
            time_periods: 時段標籤陣列
            
        Returns:
            各時段趨勢比例統計
        """
        try:
            # 創建交叉表
            cross_table = pd.crosstab(time_periods, trend_labels, normalize='index')
            
            # 計算各時段的趨勢比例
            trend_proportions = {}
            for period in cross_table.index:
                trend_proportions[period] = {
                    'trend': cross_table.loc[period, 'trend'] if 'trend' in cross_table.columns else 0,
                    'range': cross_table.loc[period, 'range'] if 'range' in cross_table.columns else 0,
                    'unclear': cross_table.loc[period, 'unclear'] if 'unclear' in cross_table.columns else 0,
                    'total_count': len(trend_labels[time_periods == period])
                }
            
            # 計算整體統計
            overall_stats = {
                'total_observations': len(trend_labels),
                'trend_count': np.sum(trend_labels == 'trend'),
                'range_count': np.sum(trend_labels == 'range'),
                'unclear_count': np.sum(trend_labels == 'unclear'),
                'trend_proportion': np.sum(trend_labels == 'trend') / len(trend_labels),
                'range_proportion': np.sum(trend_labels == 'range') / len(trend_labels),
                'unclear_proportion': np.sum(trend_labels == 'unclear') / len(trend_labels)
            }
            
            result = {
                'trend_proportions': trend_proportions,
                'overall_stats': overall_stats,
                'cross_table': cross_table
            }
            
            return result
            
        except Exception as e:
            print(f"趨勢比例計算錯誤: {e}")
            return {
                'error': str(e)
            }
    
    def perform_comprehensive_tests(self, trend_data: pd.DataFrame, time_column: str, 
                                  value_column: str, group_column: str) -> Dict:
        """
        執行綜合統計檢定
        
        Args:
            trend_data: 趨勢數據 DataFrame
            time_column: 時間列名
            value_column: 數值列名
            group_column: 分組列名
            
        Returns:
            綜合檢定結果
        """
        try:
            results = {}
            
            # 1. 按分組計算趨勢比例
            trend_proportions = self.calculate_trend_proportions(
                trend_data['trend_label'].values,
                trend_data[group_column].values
            )
            results['trend_proportions'] = trend_proportions
            
            # 2. 卡方檢定：比較各組趨勢分佈
            unique_groups = trend_data[group_column].unique()
            observed_counts = []
            for group in unique_groups:
                group_data = trend_data[trend_data[group_column] == group]
                trend_count = len(group_data[group_data['trend_label'] == 'trend'])
                observed_counts.append(trend_count)
            
            chi2_result = self.chi_square_test(np.array(observed_counts))
            results['chi_square_test'] = chi2_result
            
            # 3. ANOVA 檢定：比較各組數值差異
            groups = []
            for group in unique_groups:
                group_data = trend_data[trend_data[group_column] == group]
                groups.append(group_data[value_column].dropna().values)
            
            anova_result = self.anova_test(groups)
            results['anova_test'] = anova_result
            
            # 4. Kruskal-Wallis 檢定
            kw_result = self.kruskal_wallis_test(groups)
            results['kruskal_wallis_test'] = kw_result
            
            # 5. Bootstrap 信賴區間
            bootstrap_result = self.bootstrap_confidence_interval(
                trend_data[value_column].dropna().values,
                np.mean,
                n_bootstrap=1000
            )
            results['bootstrap_ci'] = bootstrap_result
            
            return results
            
        except Exception as e:
            print(f"綜合統計檢定錯誤: {e}")
            return {
                'error': str(e)
            }
