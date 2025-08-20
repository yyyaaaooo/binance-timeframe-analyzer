# -*- coding: utf-8 -*-
"""
趨勢檢測核心模組
實現多時間框架趨勢檢測和技術指標計算
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats
from scipy.stats import linregress
import warnings

warnings.filterwarnings("ignore")


class TrendDetector:
    """趨勢檢測器"""
    
    def __init__(self, windows: List[int] = [30, 60, 240]):
        """
        初始化趨勢檢測器
        
        Args:
            windows: 滾動窗格大小（分鐘），預設 [30, 60, 240]
        """
        self.windows = windows
        self.trend_scores = {}
        self.trend_labels = {}
        
    def calculate_linear_regression_metrics(self, prices: np.ndarray, times: np.ndarray) -> Tuple[float, float, float]:
        """
        計算線性回歸擬合度（R²）與斜率 t 統計量
        
        Args:
            prices: 價格序列（log價格）
            times: 時間序列
            
        Returns:
            (R², 斜率, t統計量絕對值)
        """
        try:
            # 對 log(價格) 對時間做 OLS
            log_prices = np.log(prices)
            slope, intercept, r_value, p_value, std_err = linregress(times, log_prices)
            r_squared = r_value ** 2
            
            # 計算 t 統計量
            n = len(prices)
            if n > 2:
                t_stat = abs(slope / std_err) if std_err > 0 else 0
            else:
                t_stat = 0
                
            return r_squared, slope, t_stat
            
        except Exception as e:
            print(f"線性回歸計算錯誤: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        計算 ADX 指標
        
        Args:
            high: 最高價序列
            low: 最低價序列
            close: 收盤價序列
            period: ADX 週期，預設 14
            
        Returns:
            ADX 值序列
        """
        try:
            # 計算 True Range
            tr1 = high - low
            tr2 = np.abs(high - np.roll(close, 1))
            tr3 = np.abs(low - np.roll(close, 1))
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            
            # 計算 Directional Movement
            dm_plus = np.where((high - np.roll(high, 1)) > (np.roll(low, 1) - low), 
                              np.maximum(high - np.roll(high, 1), 0), 0)
            dm_minus = np.where((np.roll(low, 1) - low) > (high - np.roll(high, 1)), 
                               np.maximum(np.roll(low, 1) - low, 0), 0)
            
            # 計算平滑值
            tr_smooth = pd.Series(tr).rolling(window=period).mean().values
            dm_plus_smooth = pd.Series(dm_plus).rolling(window=period).mean().values
            dm_minus_smooth = pd.Series(dm_minus).rolling(window=period).mean().values
            
            # 計算 DI+ 和 DI-
            di_plus = 100 * (dm_plus_smooth / tr_smooth)
            di_minus = 100 * (dm_minus_smooth / tr_smooth)
            
            # 計算 DX
            dx = 100 * np.abs(di_plus - di_minus) / (di_plus + di_minus)
            
            # 計算 ADX
            adx = pd.Series(dx).rolling(window=period).mean().values
            
            return adx
            
        except Exception as e:
            print(f"ADX 計算錯誤: {e}")
            return np.full(len(high), np.nan)
    
    def calculate_direction_consistency(self, returns: np.ndarray) -> float:
        """
        計算方向一致性
        
        Args:
            returns: 報酬率序列
            
        Returns:
            方向一致性比例 (0-1)
        """
        try:
            if len(returns) == 0:
                return 0.0
                
            # 計算同號比例
            positive_count = np.sum(returns > 0)
            negative_count = np.sum(returns < 0)
            total_count = len(returns)
            
            if total_count == 0:
                return 0.0
                
            # 取較大的一方作為方向一致性
            consistency = max(positive_count, negative_count) / total_count
            return consistency
            
        except Exception as e:
            print(f"方向一致性計算錯誤: {e}")
            return 0.0
    
    def calculate_range_volatility_ratio(self, high: np.ndarray, low: np.ndarray, returns: np.ndarray) -> float:
        """
        計算移動幅度/實現波動比
        
        Args:
            high: 最高價序列
            low: 最低價序列
            returns: 報酬率序列
            
        Returns:
            移動幅度/實現波動比
        """
        try:
            if len(high) == 0 or len(returns) == 0:
                return 0.0
                
            # 計算移動幅度
            price_range = high.max() - low.min()
            
            # 計算實現波動
            realized_volatility = np.sqrt(np.sum(returns ** 2))
            
            if realized_volatility == 0:
                return 0.0
                
            ratio = price_range / realized_volatility
            return ratio
            
        except Exception as e:
            print(f"移動幅度/實現波動比計算錯誤: {e}")
            return 0.0
    
    def calculate_trend_score(self, r_squared: float, adx: float, direction_consistency: float, 
                            range_vol_ratio: float, slope_t_stat: float) -> float:
        """
        計算趨勢分數 (0-100)
        
        Args:
            r_squared: 線性回歸 R²
            adx: ADX 值
            direction_consistency: 方向一致性
            range_vol_ratio: 移動幅度/實現波動比
            slope_t_stat: 斜率 t 統計量
            
        Returns:
            趨勢分數 (0-100)
        """
        try:
            # 權重設定
            w1, w2, w3, w4 = 35, 25, 20, 20
            
            # 各項分數計算
            score1 = w1 * r_squared  # R² 分數
            
            # ADX 分數 (標準化到 0-1)
            adx_normalized = min(adx, 50) / 50 if adx > 0 else 0
            score2 = w2 * adx_normalized
            
            # 方向一致性分數
            score3 = w3 * direction_consistency
            
            # 移動幅度/實現波動比分數 (限制在 0-1)
            range_vol_normalized = min(range_vol_ratio / 3, 1.0) if range_vol_ratio > 0 else 0
            score4 = w4 * range_vol_normalized
            
            # 總分
            total_score = score1 + score2 + score3 + score4
            
            return min(total_score, 100.0)  # 限制在 0-100
            
        except Exception as e:
            print(f"趨勢分數計算錯誤: {e}")
            return 0.0
    
    def classify_trend(self, trend_score: float, slope_t_stat: float, adx: float, 
                      cumulative_return: float, realized_volatility: float) -> str:
        """
        分類趨勢狀態
        
        Args:
            trend_score: 趨勢分數
            slope_t_stat: 斜率 t 統計量
            adx: ADX 值
            cumulative_return: 累積報酬
            realized_volatility: 實現波動
            
        Returns:
            趨勢分類: 'trend', 'range', 'unclear'
        """
        try:
            # 趨勢條件
            if trend_score >= 60 and abs(slope_t_stat) >= 2:
                return 'trend'
            
            # 盤整條件
            if (trend_score <= 40 and adx <= 18 and 
                abs(cumulative_return) <= 0.8 * realized_volatility):
                return 'range'
            
            # 其餘為不明/過渡
            return 'unclear'
            
        except Exception as e:
            print(f"趨勢分類錯誤: {e}")
            return 'unclear'
    
    def detect_trends(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        檢測多時間框架趨勢
        
        Args:
            df: 包含 OHLCV 資料的 DataFrame
            
        Returns:
            各時間框架的趨勢分析結果
        """
        results = {}
        
        for window in self.windows:
            print(f"分析 {window} 分鐘時間框架...")
            
            # 重採樣到指定時間框架
            df_resampled = self._resample_ohlcv(df, f"{window}T")
            
            # 計算技術指標
            trend_data = self._calculate_trend_indicators(df_resampled, window)
            
            results[f"{window}m"] = trend_data
            
        return results
    
    def _resample_ohlcv(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """重採樣 OHLCV 資料"""
        agg = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        df_resampled = df.resample(rule).agg(agg).dropna()
        return df_resampled
    
    def _calculate_trend_indicators(self, df: pd.DataFrame, window: int) -> pd.DataFrame:
        """計算趨勢指標"""
        results = []
        
        # 計算報酬率
        df['returns'] = df['close'].pct_change()
        
        # 計算 ADX
        df['adx'] = self.calculate_adx(df['high'].values, df['low'].values, df['close'].values)
        
        # 滾動窗格分析
        for i in range(window, len(df)):
            window_data = df.iloc[i-window:i+1]
            
            if len(window_data) < window:
                continue
                
            # 提取資料
            prices = window_data['close'].values
            times = np.arange(len(prices))
            returns = window_data['returns'].dropna().values
            high = window_data['high'].values
            low = window_data['low'].values
            adx = window_data['adx'].iloc[-1] if not pd.isna(window_data['adx'].iloc[-1]) else 0
            
            # 計算指標
            r_squared, slope, slope_t_stat = self.calculate_linear_regression_metrics(prices, times)
            direction_consistency = self.calculate_direction_consistency(returns)
            range_vol_ratio = self.calculate_range_volatility_ratio(high, low, returns)
            
            # 計算趨勢分數
            trend_score = self.calculate_trend_score(r_squared, adx, direction_consistency, 
                                                   range_vol_ratio, slope_t_stat)
            
            # 分類趨勢
            cumulative_return = np.sum(returns) if len(returns) > 0 else 0
            realized_volatility = np.sqrt(np.sum(returns ** 2)) if len(returns) > 0 else 0
            trend_label = self.classify_trend(trend_score, slope_t_stat, adx, 
                                            cumulative_return, realized_volatility)
            
            # 記錄結果
            result = {
                'timestamp': df.index[i],
                'trend_score': trend_score,
                'r_squared': r_squared,
                'slope': slope,
                'slope_t_stat': slope_t_stat,
                'adx': adx,
                'direction_consistency': direction_consistency,
                'range_vol_ratio': range_vol_ratio,
                'trend_label': trend_label,
                'cumulative_return': cumulative_return,
                'realized_volatility': realized_volatility,
                'close': df['close'].iloc[i]
            }
            
            results.append(result)
        
        return pd.DataFrame(results).set_index('timestamp')
