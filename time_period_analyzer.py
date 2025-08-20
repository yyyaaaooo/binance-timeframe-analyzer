# -*- coding: utf-8 -*-
"""
時段分析模組
實現時區轉換和時段彙總功能
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import pytz
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")


class TimePeriodAnalyzer:
    """時段分析器"""
    
    def __init__(self, target_timezone: str = 'Asia/Taipei'):
        """
        初始化時段分析器
        
        Args:
            target_timezone: 目標時區，預設為台北時區
        """
        self.target_timezone = target_timezone
        self.tz_target = pytz.timezone(target_timezone)
        
    def convert_timezone(self, df: pd.DataFrame, timestamp_column: str = 'timestamp') -> pd.DataFrame:
        """
        轉換時區到目標時區
        
        Args:
            df: 包含時間戳記的 DataFrame
            timestamp_column: 時間戳記列名
            
        Returns:
            轉換時區後的 DataFrame
        """
        try:
            df_copy = df.copy()
            
            # 確保時間戳記是 datetime 格式
            if not pd.api.types.is_datetime64_any_dtype(df_copy[timestamp_column]):
                df_copy[timestamp_column] = pd.to_datetime(df_copy[timestamp_column])
            
            # 如果沒有時區資訊，假設為 UTC
            if df_copy[timestamp_column].dt.tz is None:
                df_copy[timestamp_column] = df_copy[timestamp_column].dt.tz_localize('UTC')
            
            # 轉換到目標時區
            df_copy[timestamp_column] = df_copy[timestamp_column].dt.tz_convert(self.target_timezone)
            
            return df_copy
            
        except Exception as e:
            print(f"時區轉換錯誤: {e}")
            return df
    
    def extract_time_features(self, df: pd.DataFrame, timestamp_column: str = 'timestamp') -> pd.DataFrame:
        """
        提取時間特徵
        
        Args:
            df: 包含時間戳記的 DataFrame
            timestamp_column: 時間戳記列名
            
        Returns:
            包含時間特徵的 DataFrame
        """
        try:
            df_copy = df.copy()
            
            # 提取小時 (0-23)
            df_copy['hour'] = df_copy[timestamp_column].dt.hour
            
            # 提取星期幾 (0=Monday, 6=Sunday)
            df_copy['weekday'] = df_copy[timestamp_column].dt.weekday
            
            # 提取星期幾名稱
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            df_copy['weekday_name'] = df_copy['weekday'].map(lambda x: weekday_names[x])
            
            # 提取月份 (1-12)
            df_copy['month'] = df_copy[timestamp_column].dt.month
            
            # 提取月份名稱
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            df_copy['month_name'] = df_copy['month'].map(lambda x: month_names[x])
            
            # 提取年份
            df_copy['year'] = df_copy[timestamp_column].dt.year
            
            # 提取日期
            df_copy['date'] = df_copy[timestamp_column].dt.date
            
            return df_copy
            
        except Exception as e:
            print(f"時間特徵提取錯誤: {e}")
            return df
    
    def aggregate_by_time_period(self, df: pd.DataFrame, period_type: str = 'hour') -> Dict:
        """
        按時段彙總趨勢數據
        
        Args:
            df: 包含趨勢數據的 DataFrame
            period_type: 時段類型 ('hour', 'weekday', 'month')
            
        Returns:
            時段彙總結果
        """
        try:
            if period_type not in ['hour', 'weekday', 'month']:
                raise ValueError("period_type 必須是 'hour', 'weekday', 或 'month'")
            
            period_column = period_type
            
            # 按時段分組計算統計量
            grouped = df.groupby(period_column)
            
            aggregation_results = {}
            
            for period, group_data in grouped:
                # 基本統計
                total_count = len(group_data)
                trend_count = len(group_data[group_data['trend_label'] == 'trend'])
                range_count = len(group_data[group_data['trend_label'] == 'range'])
                unclear_count = len(group_data[group_data['trend_label'] == 'unclear'])
                
                # 比例計算
                trend_proportion = trend_count / total_count if total_count > 0 else 0
                range_proportion = range_count / total_count if total_count > 0 else 0
                unclear_proportion = unclear_count / total_count if total_count > 0 else 0
                
                # 趨勢分數統計
                trend_scores = group_data['trend_score'].dropna()
                avg_trend_score = trend_scores.mean() if len(trend_scores) > 0 else 0
                std_trend_score = trend_scores.std() if len(trend_scores) > 0 else 0
                
                # 回報統計
                returns = group_data['cumulative_return'].dropna()
                avg_return = returns.mean() if len(returns) > 0 else 0
                std_return = returns.std() if len(returns) > 0 else 0
                
                # 勝率計算（多空分開）
                positive_returns = returns[returns > 0]
                negative_returns = returns[returns < 0]
                win_rate_long = len(positive_returns) / len(returns) if len(returns) > 0 else 0
                win_rate_short = len(negative_returns) / len(returns) if len(returns) > 0 else 0
                
                # ADX 統計
                adx_values = group_data['adx'].dropna()
                avg_adx = adx_values.mean() if len(adx_values) > 0 else 0
                
                # R² 統計
                r_squared_values = group_data['r_squared'].dropna()
                avg_r_squared = r_squared_values.mean() if len(r_squared_values) > 0 else 0
                
                aggregation_results[period] = {
                    'total_count': total_count,
                    'trend_count': trend_count,
                    'range_count': range_count,
                    'unclear_count': unclear_count,
                    'trend_proportion': trend_proportion,
                    'range_proportion': range_proportion,
                    'unclear_proportion': unclear_proportion,
                    'avg_trend_score': avg_trend_score,
                    'std_trend_score': std_trend_score,
                    'avg_return': avg_return,
                    'std_return': std_return,
                    'win_rate_long': win_rate_long,
                    'win_rate_short': win_rate_short,
                    'avg_adx': avg_adx,
                    'avg_r_squared': avg_r_squared
                }
            
            return aggregation_results
            
        except Exception as e:
            print(f"時段彙總錯誤: {e}")
            return {}
    
    def create_24x7_heatmap_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        創建 24x7 熱力圖數據
        
        Args:
            df: 包含趨勢數據的 DataFrame
            
        Returns:
            24x7 熱力圖數據
        """
        try:
            # 確保有小時和星期幾的列
            if 'hour' not in df.columns or 'weekday' not in df.columns:
                df = self.extract_time_features(df)
            
            # 創建交叉表
            heatmap_data = pd.crosstab(
                df['weekday_name'], 
                df['hour'], 
                values=df['trend_label'], 
                aggfunc=lambda x: (x == 'trend').mean()
            )
            
            # 重新排序星期幾
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = heatmap_data.reindex(weekday_order)
            
            return heatmap_data
            
        except Exception as e:
            print(f"熱力圖數據創建錯誤: {e}")
            return pd.DataFrame()
    
    def calculate_trend_direction_stats(self, df: pd.DataFrame) -> Dict:
        """
        計算趨勢方向統計
        
        Args:
            df: 包含趨勢數據的 DataFrame
            
        Returns:
            趨勢方向統計結果
        """
        try:
            # 只考慮趨勢期間
            trend_data = df[df['trend_label'] == 'trend'].copy()
            
            if len(trend_data) == 0:
                return {
                    'total_trends': 0,
                    'long_trends': 0,
                    'short_trends': 0,
                    'long_proportion': 0,
                    'short_proportion': 0
                }
            
            # 根據斜率判斷趨勢方向
            trend_data['trend_direction'] = np.where(trend_data['slope'] > 0, 'long', 'short')
            
            # 統計
            total_trends = len(trend_data)
            long_trends = len(trend_data[trend_data['trend_direction'] == 'long'])
            short_trends = len(trend_data[trend_data['trend_direction'] == 'short'])
            
            long_proportion = long_trends / total_trends if total_trends > 0 else 0
            short_proportion = short_trends / total_trends if total_trends > 0 else 0
            
            # 按時段統計趨勢方向
            direction_by_hour = {}
            for hour in range(24):
                hour_data = trend_data[trend_data['hour'] == hour]
                if len(hour_data) > 0:
                    hour_long = len(hour_data[hour_data['trend_direction'] == 'long'])
                    hour_short = len(hour_data[hour_data['trend_direction'] == 'short'])
                    direction_by_hour[hour] = {
                        'long': hour_long,
                        'short': hour_short,
                        'long_proportion': hour_long / len(hour_data),
                        'short_proportion': hour_short / len(hour_data)
                    }
            
            # 按星期統計趨勢方向
            direction_by_weekday = {}
            for weekday in range(7):
                weekday_data = trend_data[trend_data['weekday'] == weekday]
                if len(weekday_data) > 0:
                    weekday_long = len(weekday_data[weekday_data['trend_direction'] == 'long'])
                    weekday_short = len(weekday_data[weekday_data['trend_direction'] == 'short'])
                    direction_by_weekday[weekday] = {
                        'long': weekday_long,
                        'short': weekday_short,
                        'long_proportion': weekday_long / len(weekday_data),
                        'short_proportion': weekday_short / len(weekday_data)
                    }
            
            return {
                'total_trends': total_trends,
                'long_trends': long_trends,
                'short_trends': short_trends,
                'long_proportion': long_proportion,
                'short_proportion': short_proportion,
                'direction_by_hour': direction_by_hour,
                'direction_by_weekday': direction_by_weekday
            }
            
        except Exception as e:
            print(f"趨勢方向統計錯誤: {e}")
            return {}
    
    def analyze_time_periods(self, trend_data: pd.DataFrame) -> Dict:
        """
        綜合時段分析
        
        Args:
            trend_data: 趨勢數據 DataFrame
            
        Returns:
            綜合時段分析結果
        """
        try:
            # 1. 轉換時區
            df_tz = self.convert_timezone(trend_data)
            
            # 2. 提取時間特徵
            df_features = self.extract_time_features(df_tz)
            
            # 3. 按不同時段彙總
            hour_aggregation = self.aggregate_by_time_period(df_features, 'hour')
            weekday_aggregation = self.aggregate_by_time_period(df_features, 'weekday')
            month_aggregation = self.aggregate_by_time_period(df_features, 'month')
            
            # 4. 創建熱力圖數據
            heatmap_data = self.create_24x7_heatmap_data(df_features)
            
            # 5. 計算趨勢方向統計
            direction_stats = self.calculate_trend_direction_stats(df_features)
            
            results = {
                'timezone': self.target_timezone,
                'hour_aggregation': hour_aggregation,
                'weekday_aggregation': weekday_aggregation,
                'month_aggregation': month_aggregation,
                'heatmap_data': heatmap_data,
                'direction_stats': direction_stats,
                'processed_data': df_features
            }
            
            return results
            
        except Exception as e:
            print(f"時段分析錯誤: {e}")
            return {}
