# -*- coding: utf-8 -*-
"""
Binance 時間框架分析器
支援所有現貨和永續合約交易對的分析
"""

import math
import warnings
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

from binance_analyzer_config import BinanceAnalyzerConfig
from binance_api_utils import BinanceAPI

warnings.filterwarnings("ignore")


class BinanceTimeframeAnalyzer:
    """Binance 時間框架分析器"""
    
    def __init__(self, config: BinanceAnalyzerConfig):
        self.config = config
        self.df_1m = None
    
    def load_or_fetch_data(self) -> pd.DataFrame:
        """載入或抓取資料"""
        if self.config.auto_fetch:
            print("=== 自動抓取模式 ===")
            try:
                # 驗證交易對
                if not BinanceAPI.validate_symbol(self.config.symbol, self.config.market_type):
                    raise ValueError(f"交易對 {self.config.symbol} 在 {self.config.market_type} 市場不存在或不可交易")
                
                self.df_1m = BinanceAPI.fetch_historical_data(
                    self.config.symbol, 
                    self.config.market_type, 
                    self.config.data_days
                )
                
                if self.config.save_csv:
                    self.save_data_to_csv()
                
                return self.df_1m
                
            except Exception as e:
                print(f"自動抓取失敗: {e}")
                print("嘗試使用本地CSV檔案...")
                return self.load_1m_csv()
        else:
            print("=== 本地CSV模式 ===")
            return self.load_1m_csv()
    
    def save_data_to_csv(self) -> None:
        """將資料儲存為 CSV 檔案"""
        try:
            os.makedirs(os.path.dirname(self.config.csv_path), exist_ok=True)
            self.df_1m.to_csv(self.config.csv_path, encoding='utf-8-sig')
            print(f"資料已儲存至: {self.config.csv_path}")
        except Exception as e:
            print(f"儲存CSV時發生錯誤: {e}")
    
    def load_1m_csv(self) -> pd.DataFrame:
        """讀取 1m CSV 檔案"""
        try:
            df = pd.read_csv(self.config.csv_path)
            
            # 轉換時間戳記
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            if df['timestamp'].isna().mean() > 0.5:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
            # 設定時區
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            # 轉換資料類型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df = df.set_index('timestamp').sort_index()
            return df
            
        except Exception as e:
            raise ValueError(f"讀取CSV檔案失敗: {e}")
    
    def resample_ohlcv(self, df_1m: pd.DataFrame, rule: str) -> pd.DataFrame:
        """以 OHLCV 規則重採樣"""
        agg = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        return df_1m.resample(rule, label='right', closed='right').agg(agg).dropna(subset=['open', 'high', 'low', 'close'])
    
    def compute_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """計算 ATR"""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        return atr
    
    def variance_ratio(self, returns: pd.Series, q: int) -> float:
        """計算 Variance Ratio"""
        r = returns.dropna()
        if len(r) < q + 2:
            return np.nan
        var_1 = np.var(r, ddof=1)
        r_q = r.rolling(q).sum()
        var_q = np.var(r_q.dropna(), ddof=1)
        if var_1 == 0:
            return np.nan
        return float(var_q / (q * var_1))
    
    def estimate_half_life_by_autocorr(self, returns: pd.Series, max_lag: int) -> Optional[float]:
        """估算訊號半衰期"""
        r = returns.dropna()
        if len(r) < max_lag + 5:
            return None
        
        r = r - r.mean()
        var = (r ** 2).sum()
        if var == 0:
            return None
        
        def autocorr(lag: int) -> float:
            return float((r[lag:] * r.shift(lag)[lag:]).sum() / var)
        
        rho1 = autocorr(1)
        if np.isnan(rho1) or abs(rho1) < 1e-6:
            return None
        
        target = 0.5 * abs(rho1)
        for k in range(2, max_lag + 1):
            rhok = autocorr(k)
            if np.isnan(rhok):
                continue
            if abs(rhok) <= target:
                return float(k)
        return None
    
    def bar_minutes(self, label: str) -> float:
        """將時間框架標籤轉換為分鐘數"""
        mapping = {
            "1m": 1, "5m": 5, "15m": 15,
            "1h": 60, "4h": 240,
            "1d": 1440, "1w": 10080
        }
        return float(mapping.get(label, 1.0))
    
    def get_min_bars_for_timeframe(self, tf_label: str) -> int:
        """根據時間框架動態計算最小資料量要求"""
        if not self.config.use_dynamic_min_bars:
            return self.config.n_min_bars_for_backtest
        
        min_days = self.config.min_days_per_timeframe.get(tf_label, 365)
        minutes_per_bar = self.bar_minutes(tf_label)
        min_bars = int((min_days * 24 * 60) / minutes_per_bar)
        min_bars = max(min_bars, 100)
        
        return min_bars
    
    def annualization_factor(self, tf_label: str) -> float:
        """計算年化倍數"""
        bars_per_year = (365.0 * 24.0 * 60.0) / self.bar_minutes(tf_label)
        return bars_per_year
    
    def apply_costs(self, returns: pd.Series, position: pd.Series, cost_one_way: float) -> pd.Series:
        """根據部位變化計算交易成本"""
        pos = position.fillna(0.0)
        pos_prev = pos.shift(1).fillna(0.0)
        turnover = (pos - pos_prev).abs()
        
        cost = turnover * cost_one_way
        net_ret = pos_prev * returns - cost
        return net_ret
    
    def sharpe_ratio(self, returns: pd.Series, ann_factor: float) -> float:
        """計算夏普比率"""
        r = returns.dropna()
        if len(r) < 2:
            return np.nan
        mean = r.mean() * ann_factor
        std = r.std(ddof=1) * math.sqrt(ann_factor)
        return float(mean / std) if std > 0 else np.nan
    
    def max_drawdown(self, equity_curve: pd.Series) -> float:
        """計算最大回撤"""
        peak = equity_curve.cummax()
        dd = equity_curve / peak - 1.0
        return float(dd.min()) if len(dd) else np.nan
    
    def profit_factor(self, returns: pd.Series) -> float:
        """計算獲利因子"""
        gains = returns[returns > 0].sum()
        losses = -returns[returns < 0].sum()
        if losses == 0:
            return np.inf if gains > 0 else np.nan
        return float(gains / losses)
    
    def hit_rate(self, returns: pd.Series) -> float:
        """計算勝率"""
        r = returns.dropna()
        if len(r) == 0:
            return np.nan
        return float((r > 0).mean())
    
    def ma_trend_positions(self, close: pd.Series, fast: int, slow: int) -> pd.Series:
        """MA 趨勢策略"""
        if slow <= fast:
            return pd.Series(index=close.index, dtype=float)
        f = close.rolling(fast).mean()
        s = close.rolling(slow).mean()
        pos = np.where(f > s, 1.0, np.where(f < s, -1.0, 0.0))
        return pd.Series(pos, index=close.index, dtype=float)
    
    def rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """計算 RSI 指標"""
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        roll_up = up.rolling(window).mean()
        roll_down = down.rolling(window).mean()
        rs = roll_up / (roll_down + 1e-12)
        return 100.0 - (100.0 / (1.0 + rs))
    
    def rsi_mr_positions(self, close: pd.Series, window: int, lower: int, upper: int) -> pd.Series:
        """RSI 均值回歸策略"""
        r = self.rsi(close, window)
        pos = np.where(r < lower, 1.0, np.where(r > upper, -1.0, 0.0))
        return pd.Series(pos, index=close.index, dtype=float)
    
    def backtest_positions(self, ohlc: pd.DataFrame, position: pd.Series, cost_one_way: float, ann_factor: float) -> Dict[str, float]:
        """回測策略表現"""
        px = ohlc['close']
        ret = px.pct_change().fillna(0.0)
        net = self.apply_costs(ret, position, cost_one_way)
        eq = (1.0 + net).cumprod()
        
        metrics = {
            "AnnRet": float((eq.iloc[-1] ** (ann_factor / max(len(eq), 1)) - 1.0)) if len(eq) > 0 else np.nan,
            "Sharpe": self.sharpe_ratio(net, ann_factor),
            "MDD": self.max_drawdown(eq),
            "PF": self.profit_factor(net),
            "HitRate": self.hit_rate(net),
            "TradesPerYear": float((position.diff().abs().fillna(0.0).sum() / 2.0) * (ann_factor / max(len(position), 1))),
            "AvgTurnover": float(position.diff().abs().fillna(0.0).mean())
        }
        return metrics
    
    def param_search_ma(self, ohlc: pd.DataFrame, cost_one_way: float, ann_factor: float) -> Tuple[Tuple[int, int], Dict[str, float]]:
        """MA 策略參數搜尋"""
        best_param = None
        best_metric = -np.inf
        best_stats = {}
        close = ohlc['close']
        
        for f in self.config.ma_fast_grid:
            for s in self.config.ma_slow_grid:
                if s <= f:
                    continue
                pos = self.ma_trend_positions(close, f, s)
                stats = self.backtest_positions(ohlc, pos, cost_one_way, ann_factor)
                score = stats["Sharpe"]
                if not np.isnan(score) and score > best_metric:
                    best_metric = score
                    best_param = (f, s)
                    best_stats = stats
        return best_param, best_stats
    
    def param_search_rsi(self, ohlc: pd.DataFrame, cost_one_way: float, ann_factor: float) -> Tuple[Tuple[int, int, int], Dict[str, float]]:
        """RSI 策略參數搜尋"""
        best_param = None
        best_metric = -np.inf
        best_stats = {}
        close = ohlc['close']
        
        for w in self.config.rsi_window_grid:
            for (lo, up) in self.config.rsi_band_grid:
                pos = self.rsi_mr_positions(close, w, lo, up)
                stats = self.backtest_positions(ohlc, pos, cost_one_way, ann_factor)
                score = stats["Sharpe"]
                if not np.isnan(score) and score > best_metric:
                    best_metric = score
                    best_param = (w, lo, up)
                    best_stats = stats
        return best_param, best_stats
    
    def walk_forward_oos(self, ohlc: pd.DataFrame, strategy: str, cost_one_way: float, ann_factor: float) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Walk-forward 樣本外評估"""
        n = len(ohlc)
        train_len = int(n * self.config.wf_train_ratio)
        test_len = int(n * self.config.wf_test_ratio)
        if train_len < 200 or test_len < 100:
            return {}, {}
        
        oos_metrics = []
        chosen_params = []
        
        start = 0
        while start + train_len + test_len <= n:
            train = ohlc.iloc[start:start + train_len]
            test = ohlc.iloc[start + train_len:start + train_len + test_len]
            
            if strategy == "MA":
                param, _ = self.param_search_ma(train, cost_one_way, ann_factor)
                if param is None:
                    start += test_len
                    continue
                f, s = param
                pos = self.ma_trend_positions(test['close'], f, s)
            elif strategy == "RSI":
                param, _ = self.param_search_rsi(train, cost_one_way, ann_factor)
                if param is None:
                    start += test_len
                    continue
                w, lo, up = param
                pos = self.rsi_mr_positions(test['close'], w, lo, up)
            else:
                raise ValueError("未知策略")
            
            stats = self.backtest_positions(test, pos, cost_one_way, ann_factor)
            oos_metrics.append(stats)
            chosen_params.append(param)
            start += test_len
        
        if not oos_metrics:
            return {}, {}
        
        # 聚合 OOS 指標
        oos_df = pd.DataFrame(oos_metrics)
        oos_summary = {
            "OOS_AnnRet": float(oos_df["AnnRet"].mean()),
            "OOS_Sharpe": float(oos_df["Sharpe"].mean()),
            "OOS_MDD": float(oos_df["MDD"].mean()),
            "OOS_PF": float(oos_df["PF"].mean()),
            "OOS_HitRate": float(oos_df["HitRate"].mean()),
            "OOS_TradesPerYear": float(oos_df["TradesPerYear"].mean())
        }
        
        last_param = chosen_params[-1] if chosen_params else None
        chosen_param_dict = {"BestTrainParam_LastFold": str(last_param)}
        return oos_summary, chosen_param_dict
    
    def analyze_timeframes(self) -> pd.DataFrame:
        """分析所有時間框架"""
        print("=== 開始時間框架分析 ===")
        
        # 載入資料
        self.df_1m = self.load_or_fetch_data()
        
        report_rows = []
        
        # 成本（單邊）
        cost_one_way = (self.config.taker_fee if self.config.use_taker else self.config.maker_fee) + self.config.slippage_bps / 10000.0
        print(f"採用 {'吃單' if self.config.use_taker else '掛單'} 費率；單邊成本 = {cost_one_way:.6f} ({cost_one_way*100:.4f}%)")
        
        for tf_label, rule in self.config.timeframes.items():
            print(f"\n--- 時間框架：{tf_label} ({rule}) ---")
            ohlc = self.resample_ohlcv(self.df_1m, rule)
            
            min_bars_required = self.get_min_bars_for_timeframe(tf_label)
            
            if len(ohlc) < min_bars_required:
                min_days_required = self.config.min_days_per_timeframe.get(tf_label, 365) if self.config.use_dynamic_min_bars else "N/A"
                print(f"資料量不足（{len(ohlc)} < {min_bars_required} bars），略過。")
                if self.config.use_dynamic_min_bars:
                    print(f"  該時間框架需要至少 {min_days_required} 天的資料")
                continue
            
            ann_factor = self.annualization_factor(tf_label)
            
            # C/A
            atr = self.compute_atr(ohlc, self.config.atr_period)
            atr_pct = (atr / ohlc['close']).dropna()
            avg_atr_pct = float(atr_pct.mean()) if len(atr_pct) else np.nan
            cost_roundtrip = 2.0 * cost_one_way
            c_over_a = float(cost_roundtrip / avg_atr_pct) if avg_atr_pct and avg_atr_pct > 0 else np.nan
            
            # VR
            ret = ohlc['close'].pct_change()
            vr = self.variance_ratio(np.log1p(ret), self.config.vr_q)
            
            # 半衰期
            hl = self.estimate_half_life_by_autocorr(np.log1p(ret), self.config.half_life_max_lag)
            
            # Walk-forward
            ma_oos, ma_param = self.walk_forward_oos(ohlc, "MA", cost_one_way, ann_factor)
            rsi_oos, rsi_param = self.walk_forward_oos(ohlc, "RSI", cost_one_way, ann_factor)
            
            row = {
                "Timeframe": tf_label,
                "Bars": len(ohlc),
                "Avg_ATR_pct": avg_atr_pct,
                "Cost_RoundTrip_pct": cost_roundtrip,
                "C_over_A": c_over_a,
                "VR_q": self.config.vr_q,
                "VarianceRatio": vr,
                "HalfLife_bars": hl,
            }
            
            if ma_oos:
                row.update({f"MA_{k}": v for k, v in ma_oos.items()})
            if rsi_oos:
                row.update({f"RSI_{k}": v for k, v in rsi_oos.items()})
            
            row.update({f"MA_{k}": v for k, v in ma_param.items()} if ma_param else {})
            row.update({f"RSI_{k}": v for k, v in rsi_param.items()} if rsi_param else {})
            
            row["Pass_CA_0.25"] = (c_over_a < 0.25) if not (pd.isna(c_over_a)) else False
            
            report_rows.append(row)
        
        if not report_rows:
            print("沒有可用的時間框架結果。請確認資料量或調整最小資料量設定。")
            return pd.DataFrame()
        
        report = pd.DataFrame(report_rows).sort_values(
            by=["Pass_CA_0.25", "MA_OOS_Sharpe", "RSI_OOS_Sharpe"],
            ascending=[False, False, False]
        )
        
        return report
    
    def generate_reports(self, report_df: pd.DataFrame) -> None:
        """生成報告檔案"""
        if report_df.empty:
            print("沒有資料可生成報告")
            return
        
        # 確保輸出目錄存在
        os.makedirs("./data", exist_ok=True)
        
        # 生成包含日期區間和交易對資訊的檔名
        start_date = self.df_1m.index.min().strftime('%Y%m%d')
        end_date = self.df_1m.index.max().strftime('%Y%m%d')
        date_range = f"{start_date}-{end_date}"
        filename_prefix = f"{self.config.symbol.lower()}_{self.config.market_type}_timeframe_report_{date_range}"
        
        # 生成CSV報告
        if self.config.generate_csv_report:
            out_csv = f"./data/{filename_prefix}.csv"
            report_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"\n✅ 已輸出CSV報表：{out_csv}")
        
        # 生成TXT報告
        if self.config.generate_txt_report:
            txt_report = self.generate_txt_report(report_df)
            out_txt = f"./data/{filename_prefix}.txt"
            with open(out_txt, 'w', encoding='utf-8') as f:
                f.write(txt_report)
            print(f"✅ 已輸出TXT報表：{out_txt}")
        
        print("\n📋 報告解讀指南：")
        print("1) 先看 C_over_A 是否 < 0.25（越低越好）。")
        print("2) 再看策略 OOS_Sharpe（跨折平均）與 OOS_MDD。")
        print("3) VR>1 偏趨勢；VR<1 偏均值回歸；HalfLife 提示 bar 粗細。")
        print("4) 詳細報告包含測試日期範圍、成本設定、策略參數等完整資訊。")
    
    def generate_txt_report(self, report_df: pd.DataFrame) -> str:
        """生成TXT格式的詳細報告"""
        report = []
        report.append("=" * 80)
        report.append(f"{self.config.symbol} {self.config.market_type.upper()} 時間框架選擇分析報告")
        report.append("=" * 80)
        report.append("")
        
        # 基本資訊
        report.append("📊 基本資訊")
        report.append("-" * 40)
        report.append(f"交易對: {self.config.symbol}")
        report.append(f"市場類型: {self.config.market_type.upper()}")
        report.append(f"交易所: {self.config.exchange.upper()}")
        report.append(f"測試日期範圍: {self.df_1m.index.min().strftime('%Y-%m-%d %H:%M:%S')} 到 {self.df_1m.index.max().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"總測試天數: {(self.df_1m.index.max() - self.df_1m.index.min()).days} 天")
        report.append(f"原始資料K線數: {len(self.df_1m):,}")
        report.append(f"報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 成本設定
        cost_one_way = (self.config.taker_fee if self.config.use_taker else self.config.maker_fee) + self.config.slippage_bps / 10000.0
        report.append("💰 成本設定")
        report.append("-" * 40)
        report.append(f"費率類型: {'吃單費率' if self.config.use_taker else '掛單費率'}")
        report.append(f"單邊成本: {cost_one_way:.6f} ({cost_one_way*100:.4f}%)")
        report.append(f"來回成本: {cost_one_way*2:.6f} ({cost_one_way*2*100:.4f}%)")
        report.append("")
        
        # 時間框架分析結果
        report.append("📈 時間框架分析結果")
        report.append("-" * 40)
        report.append("")
        
        tested_timeframes = set(report_df['Timeframe'].tolist())
        
        for tf_label, rule in self.config.timeframes.items():
            if tf_label in tested_timeframes:
                row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
                report.append(f"🕐 {row['Timeframe']} 時間框架")
                report.append(f"    K線數量: {row['Bars']:,}")
                report.append(f"    平均ATR: {row['Avg_ATR_pct']:.4f} ({row['Avg_ATR_pct']*100:.2f}%)")
                report.append(f"    成本/波動比 (C/A): {row['C_over_A']:.4f}")
                report.append(f"    走勢一致性 (VR): {row['VarianceRatio']:.4f}")
                report.append(f"    訊號半衰期: {row['HalfLife_bars']:.1f} bars")
                
                if 'Volatility_Ann' in row and not pd.isna(row['Volatility_Ann']):
                    report.append(f"    年化波動率: {row['Volatility_Ann']:.4f}")
                if 'Skewness' in row and not pd.isna(row['Skewness']):
                    report.append(f"    報酬偏度: {row['Skewness']:.4f}")
                if 'Kurtosis' in row and not pd.isna(row['Kurtosis']):
                    report.append(f"    報酬峰度: {row['Kurtosis']:.4f}")
                if 'Autocorr_Lag1' in row and not pd.isna(row['Autocorr_Lag1']):
                    report.append(f"    自相關(Lag1): {row['Autocorr_Lag1']:.4f}")
                if 'Market_Efficiency' in row and not pd.isna(row['Market_Efficiency']):
                    report.append(f"    市場效率比率: {row['Market_Efficiency']:.4f}")
                
                if row['Pass_CA_0.25']:
                    report.append(f"    ✅ 通過C/A < 0.25測試")
                else:
                    report.append(f"    ❌ 未通過C/A < 0.25測試")
            else:
                report.append(f"🕐 {tf_label} 時間框架")
                report.append(f"    ❌ 未進行測試")
                min_bars_required = self.get_min_bars_for_timeframe(tf_label)
                min_days_required = self.config.min_days_per_timeframe.get(tf_label, 365) if self.config.use_dynamic_min_bars else "N/A"
                report.append(f"    原因: 資料量不足（需要至少 {min_bars_required} 根K線）")
                if self.config.use_dynamic_min_bars:
                    report.append(f"    要求: 至少 {min_days_required} 天的資料")
                report.append(f"    建議: 增加資料天數或調整最小資料量設定")
            
            report.append("")
        
        # 綜合建議
        report.append("💡 綜合建議")
        report.append("-" * 40)
        
        best_ca = report_df.loc[report_df['C_over_A'].idxmin()] if 'C_over_A' in report_df.columns else None
        best_vr = report_df.loc[report_df['VarianceRatio'].idxmax()] if 'VarianceRatio' in report_df.columns else None
        
        if best_ca is not None and not pd.isna(best_ca['C_over_A']):
            report.append(f"最佳成本效率時間框架: {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
        
        if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
            report.append(f"最高趨勢性時間框架: {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
        
        report.append("")
        report.append("📋 指標解讀指南:")
        report.append("• C/A < 0.25: 成本相對於波動率較低，適合交易")
        report.append("• VR > 1: 偏趨勢市場，適合趨勢策略")
        report.append("• VR < 1: 偏均值回歸市場，適合均值回歸策略")
        report.append("• 半衰期: 建議bar週期約為0.5~1倍半衰期")
        report.append("• 波動率: 反映市場波動程度")
        report.append("• 偏度: 正偏度表示右尾較長，負偏度表示左尾較長")
        report.append("• 峰度: 高峰度表示極端值較多")
        report.append("• 自相關: 正值表示趨勢性，負值表示均值回歸")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def analyze(self) -> pd.DataFrame:
        """執行完整分析"""
        print("=== Binance 時間框架分析器 ===")
        print(f"分析交易對: {self.config.symbol}")
        print(f"市場類型: {self.config.market_type.upper()}")
        
        # 分析時間框架
        report_df = self.analyze_timeframes()
        
        # 生成報告
        self.generate_reports(report_df)
        
        return report_df


# 便捷函數
def analyze_symbol(symbol: str, market_type: str = "spot", data_days: int = 365) -> pd.DataFrame:
    """分析指定交易對的便捷函數"""
    config = BinanceAnalyzerConfig(
        symbol=symbol,
        market_type=market_type,
        data_days=data_days
    )
    analyzer = BinanceTimeframeAnalyzer(config)
    return analyzer.analyze()


def get_available_symbols(market_type: str = "spot") -> List[str]:
    """獲取可用的交易對列表"""
    return BinanceAPI.get_available_symbols(market_type)


def get_popular_symbols(market_type: str = "spot", limit: int = 50) -> List[str]:
    """獲取熱門交易對列表"""
    return BinanceAPI.get_popular_symbols(market_type, limit)


if __name__ == "__main__":
    # 預設配置 - 可以修改這裡來分析不同的交易對
    config = BinanceAnalyzerConfig(
        symbol="ETHUSDT",
        market_type="spot",  # 或 "futures"
        data_days=365
    )
    
    analyzer = BinanceTimeframeAnalyzer(config)
    analyzer.analyze()
