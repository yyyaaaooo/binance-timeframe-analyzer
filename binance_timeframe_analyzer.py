# -*- coding: utf-8 -*-
"""
Binance 時間框架分析器
支援所有現貨和永續合約交易對的分析
專注於時間框架特性分析，不包含策略回測功能
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
    
    def compute_atr(self, ohlc: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算 ATR (Average True Range)"""
        high = ohlc['high']
        low = ohlc['low']
        close = ohlc['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def variance_ratio(self, log_returns: pd.Series, q: int) -> float:
        """計算 Variance Ratio (Lo-MacKinlay)"""
        if len(log_returns) < q * 2:
            return np.nan
        
        # 移除 NaN
        log_returns = log_returns.dropna()
        if len(log_returns) < q * 2:
            return np.nan
        
        # 計算不同時間間隔的方差
        var_1 = log_returns.var()
        var_q = log_returns.rolling(q).sum().var()
        
        if var_1 == 0:
            return np.nan
        
        vr = var_q / (q * var_1)
        return float(vr)
    
    def estimate_half_life_by_autocorr(self, log_returns: pd.Series, max_lag: int = 100) -> float:
        """基於自相關估計半衰期"""
        if len(log_returns) < max_lag * 2:
            return np.nan
        
        log_returns = log_returns.dropna()
        if len(log_returns) < max_lag * 2:
            return np.nan
        
        # 計算自相關
        autocorr = []
        for lag in range(1, min(max_lag + 1, len(log_returns) // 2)):
            corr = log_returns.autocorr(lag=lag)
            if not pd.isna(corr):
                autocorr.append((lag, corr))
        
        if len(autocorr) < 3:
            return np.nan
        
        # 找到第一個負自相關
        for lag, corr in autocorr:
            if corr < 0:
                return float(lag)
        
        # 如果沒有負自相關，返回最大延遲
        return float(autocorr[-1][0]) if autocorr else np.nan
    
    def get_min_bars_for_timeframe(self, timeframe: str) -> int:
        """獲取時間框架的最小 bar 數要求"""
        if not self.config.use_dynamic_min_bars:
            return self.config.n_min_bars_for_backtest
        
        # 動態計算最小 bar 數
        min_days = self.config.min_days_per_timeframe.get(timeframe, 365)
        
        # 根據時間框架計算對應的 bar 數
        timeframe_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080
        }
        
        minutes_per_bar = timeframe_minutes.get(timeframe, 1440)
        min_bars = int(min_days * 24 * 60 / minutes_per_bar)
        
        return max(min_bars, 100)  # 至少需要 100 根 bar
    
    def annualization_factor(self, timeframe: str) -> float:
        """計算年化因子"""
        timeframe_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080
        }
        
        minutes_per_bar = timeframe_minutes.get(timeframe, 1440)
        minutes_per_year = 365 * 24 * 60
        
        return minutes_per_year / minutes_per_bar
    
    def calculate_volatility(self, returns: pd.Series, ann_factor: float) -> float:
        """計算年化波動率"""
        if len(returns) < 2:
            return np.nan
        return float(returns.std() * np.sqrt(ann_factor))
    
    def calculate_skewness(self, returns: pd.Series) -> float:
        """計算報酬偏度"""
        if len(returns) < 3:
            return np.nan
        return float(returns.skew())
    
    def calculate_kurtosis(self, returns: pd.Series) -> float:
        """計算報酬峰度"""
        if len(returns) < 4:
            return np.nan
        return float(returns.kurtosis())
    
    def calculate_autocorrelation(self, returns: pd.Series, lag: int = 1) -> float:
        """計算報酬自相關"""
        if len(returns) < lag + 1:
            return np.nan
        return float(returns.autocorr(lag=lag))
    
    def calculate_market_efficiency_ratio(self, log_returns: pd.Series, q: int = 4) -> float:
        """計算市場效率比率（基於方差比）"""
        vr = self.variance_ratio(log_returns, q)
        if pd.isna(vr):
            return np.nan
        # 市場效率比率 = 1 / VR，越接近1表示越有效率
        return float(1.0 / vr) if vr > 0 else np.nan
    
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
            
            # 新增技術指標
            log_returns = np.log1p(ret).dropna()
            volatility_ann = self.calculate_volatility(ret.dropna(), ann_factor)
            skewness = self.calculate_skewness(ret.dropna())
            kurtosis = self.calculate_kurtosis(ret.dropna())
            autocorr_lag1 = self.calculate_autocorrelation(ret.dropna(), 1)
            market_efficiency = self.calculate_market_efficiency_ratio(log_returns, self.config.vr_q)
            
            row = {
                "Timeframe": tf_label,
                "Bars": len(ohlc),
                "Avg_ATR_pct": avg_atr_pct,
                "Cost_RoundTrip_pct": cost_roundtrip,
                "C_over_A": c_over_a,
                "VR_q": self.config.vr_q,
                "VarianceRatio": vr,
                "HalfLife_bars": hl,
                "Volatility_Ann": volatility_ann,
                "Skewness": skewness,
                "Kurtosis": kurtosis,
                "Autocorr_Lag1": autocorr_lag1,
                "Market_Efficiency": market_efficiency
            }
            
            row["Pass_CA_0.25"] = (c_over_a < 0.25) if not (pd.isna(c_over_a)) else False
            
            report_rows.append(row)
        
        if not report_rows:
            print("沒有可用的時間框架結果。請確認資料量或調整最小資料量設定。")
            return pd.DataFrame()
        
        report = pd.DataFrame(report_rows).sort_values(
            by=["Pass_CA_0.25", "C_over_A"],
            ascending=[False, True]
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
        
        # 生成MD報告
        if self.config.generate_md_report:
            md_report = self.generate_md_report(report_df)
            out_md = f"./data/{filename_prefix}.md"
            with open(out_md, 'w', encoding='utf-8') as f:
                f.write(md_report)
            print(f"✅ 已輸出MD報表：{out_md}")
        
        print("\n📋 報告解讀指南：")
        print("1) 先看 C_over_A 是否 < 0.25（越低越好）。")
        print("2) 再看 VarianceRatio 判斷市場特性（>1偏趨勢，<1偏均值回歸）。")
        print("3) 半衰期提示 bar 粗細，建議bar週期約為0.5~1倍半衰期。")
        print("4) 技術指標幫助了解市場統計特性。")
    
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
        
        # 分析設定
        report.append("⚙️ 分析設定")
        report.append("-" * 40)
        report.append(f"ATR計算週期: {self.config.atr_period}")
        report.append(f"Variance Ratio聚合尺度: {self.config.vr_q}")
        report.append(f"半衰期計算最大延遲: {self.config.half_life_max_lag}")
        report.append(f"動態最小資料量: {'啟用' if self.config.use_dynamic_min_bars else '停用'}")
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
        report.append("• 市場效率比率: 越接近1表示市場越有效率")
        
        # 添加詳細指標解釋
        report.append("")
        report.append("📊 詳細指標解釋")
        report.append("-" * 40)
        report.append("")
        
        report.append("🔍 成本/波動比 (C/A Ratio)")
        report.append("意義: 衡量交易成本相對於市場波動的比率")
        report.append("解讀: ")
        report.append("• C/A < 0.25: 成本相對較低，適合頻繁交易")
        report.append("• C/A 0.25-0.5: 成本適中，需要謹慎選擇入場點")
        report.append("• C/A > 0.5: 成本過高，不適合短線交易")
        report.append("")
        
        report.append("🔍 走勢一致性 (Variance Ratio, VR)")
        report.append("意義: 衡量價格變動的趨勢性強度")
        report.append("解讀:")
        report.append("• VR > 1: 價格變動具有趨勢性，適合趨勢跟隨策略")
        report.append("• VR < 1: 價格變動偏向隨機遊走，適合均值回歸策略")
        report.append("• VR ≈ 1: 價格變動接近隨機遊走")
        report.append("")
        
        report.append("🔍 訊號半衰期 (Signal Half-Life)")
        report.append("意義: 衡量價格訊號的持續時間")
        report.append("解讀:")
        report.append("• 半衰期越長，訊號越持久，適合較長期的策略")
        report.append("• 半衰期越短，訊號變化越快，需要更頻繁的調整")
        report.append("")
        
        report.append("🔍 年化波動率 (Annualized Volatility)")
        report.append("意義: 衡量價格變動的劇烈程度")
        report.append("解讀:")
        report.append("• 波動率越高，價格變動越劇烈，風險越大")
        report.append("• 波動率越低，價格變動越平穩，風險較小")
        report.append("")
        
        report.append("🔍 報酬偏度 (Return Skewness)")
        report.append("意義: 衡量報酬分布的對稱性")
        report.append("解讀:")
        report.append("• 正偏度: 右尾較長，大幅上漲機率較高")
        report.append("• 負偏度: 左尾較長，大幅下跌機率較高")
        report.append("")
        
        report.append("🔍 報酬峰度 (Return Kurtosis)")
        report.append("意義: 衡量報酬分布的尖銳程度")
        report.append("解讀:")
        report.append("• 高峰度: 極端值出現機率較高，風險較大")
        report.append("• 低峰度: 分布較平坦，極端值較少")
        report.append("")
        
        report.append("🔍 自相關 (Autocorrelation)")
        report.append("意義: 衡量當前價格與過去價格的相關性")
        report.append("解讀:")
        report.append("• 正值: 價格具有趨勢性，過去走勢對未來有影響")
        report.append("• 負值: 價格具有均值回歸特性")
        report.append("")
        
        report.append("🔍 市場效率比率 (Market Efficiency Ratio)")
        report.append("意義: 衡量市場的資訊效率")
        report.append("解讀:")
        report.append("• 接近1: 市場效率較高，價格充分反映資訊")
        report.append("• 遠離1: 市場效率較低，可能存在套利機會")
        report.append("")
        
        # 添加市場分析結論
        report.append("📈 市場分析結論")
        report.append("-" * 40)
        report.append("")
        
        # 分析整體市場特性
        avg_volatility = report_df['Volatility_Ann'].mean() if 'Volatility_Ann' in report_df.columns else None
        avg_vr = report_df['VarianceRatio'].mean() if 'VarianceRatio' in report_df.columns else None
        avg_autocorr = report_df['Autocorr_Lag1'].mean() if 'Autocorr_Lag1' in report_df.columns else None
        avg_me = report_df['Market_Efficiency'].mean() if 'Market_Efficiency' in report_df.columns else None
        
        report.append("🎯 整體市場特性:")
        if avg_volatility and not pd.isna(avg_volatility):
            volatility_level = "高" if avg_volatility > 0.5 else "中" if avg_volatility > 0.3 else "低"
            report.append(f"1. 波動性: {self.config.symbol} {self.config.market_type}年化波動率約{avg_volatility:.1%}，屬於{volatility_level}波動資產")
        
        if avg_me and not pd.isna(avg_me):
            efficiency_level = "高" if abs(avg_me - 1) < 0.1 else "中" if abs(avg_me - 1) < 0.2 else "低"
            report.append(f"2. 市場效率: 各時間框架的市場效率比率都接近1，顯示市場資訊效率較{efficiency_level}")
        
        if avg_autocorr and not pd.isna(avg_autocorr):
            if avg_autocorr < -0.01:
                report.append("3. 均值回歸: 大部分時間框架顯示負自相關，表示價格具有均值回歸特性")
            elif avg_autocorr > 0.01:
                report.append("3. 趨勢性: 大部分時間框架顯示正自相關，表示價格具有趨勢性")
            else:
                report.append("3. 隨機性: 大部分時間框架顯示接近零的自相關，表示價格變動接近隨機")
        
        # 分析偏度特性
        long_term_timeframes = ['1d', '1w']
        long_term_skewness = []
        for tf in long_term_timeframes:
            if tf in report_df['Timeframe'].values:
                row = report_df[report_df['Timeframe'] == tf].iloc[0]
                if 'Skewness' in row and not pd.isna(row['Skewness']):
                    long_term_skewness.append(row['Skewness'])
        
        if long_term_skewness:
            avg_long_skew = sum(long_term_skewness) / len(long_term_skewness)
            if avg_long_skew > 0.1:
                report.append("4. 長期正偏度: 較長時間框架顯示正偏度，長期來看上漲機率較高")
            elif avg_long_skew < -0.1:
                report.append("4. 長期負偏度: 較長時間框架顯示負偏度，長期來看下跌機率較高")
            else:
                report.append("4. 長期對稱性: 較長時間框架顯示接近對稱的分布")
        
        report.append("")
        report.append("🎯 交易策略建議:")
        
        # 分析通過C/A測試的時間框架
        passed_timeframes = report_df[report_df['Pass_CA_0.25'] == True]['Timeframe'].tolist()
        short_timeframes = [tf for tf in passed_timeframes if tf in ['1m', '5m', '15m']]
        medium_timeframes = [tf for tf in passed_timeframes if tf in ['1h', '4h']]
        long_timeframes = [tf for tf in passed_timeframes if tf in ['1d', '1w']]
        
        if short_timeframes:
            report.append(f"1. 短線交易({', '.join(short_timeframes)}): 適合，成本效率較好")
        else:
            report.append("1. 短線交易(1m-15m): 不建議，因為交易成本相對波動率過高(C/A > 0.25)")
        
        if medium_timeframes:
            report.append(f"2. 中線交易({', '.join(medium_timeframes)}): 適合，成本效率較好")
        
        if long_timeframes:
            report.append(f"3. 長線交易({', '.join(long_timeframes)}): 最適合，成本效率最佳，適合趨勢跟隨策略")
        
        report.append("")
        report.append("🎯 風險管理建議:")
        report.append("1. 由於高波動性，建議使用較小的倉位規模")
        report.append("2. 設置適當的止損位，避免極端價格變動造成的損失")
        report.append("3. 考慮使用期權等衍生品進行風險對沖")
        report.append("4. 關注市場情緒指標，避免在極端市場條件下交易")
        
        report.append("")
        report.append("🎯 最佳時間框架選擇:")
        
        # 找出最佳時間框架
        if best_ca is not None and not pd.isna(best_ca['C_over_A']):
            if best_ca['Timeframe'] in ['1h', '4h']:
                report.append(f"• 日內交易: {best_ca['Timeframe']}時間框架 (C/A: {best_ca['C_over_A']:.4f})")
            elif best_ca['Timeframe'] in ['1d', '1w']:
                report.append(f"• 長期投資: {best_ca['Timeframe']}時間框架 (C/A: {best_ca['C_over_A']:.4f}，成本效率最佳)")
        
        if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
            if best_vr['VarianceRatio'] > 1.05:
                report.append(f"• 波段交易: {best_vr['Timeframe']}時間框架 (VR: {best_vr['VarianceRatio']:.4f}，趨勢性最強)")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def generate_md_report(self, report_df: pd.DataFrame) -> str:
        """生成Markdown格式的詳細報告"""
        report = []
        report.append(f"# {self.config.symbol} 時間框架選擇分析報告")
        report.append("")
        report.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本資訊
        report.append("## 📊 基本資訊")
        report.append("")
        report.append("| 項目 | 數值 |")
        report.append("|------|------|")
        report.append(f"| 交易對 | {self.config.symbol} |")
        report.append(f"| 市場類型 | {self.config.market_type.upper()} |")
        report.append(f"| 交易所 | {self.config.exchange.upper()} |")
        report.append(f"| 測試開始時間 | {self.df_1m.index.min().strftime('%Y-%m-%d %H:%M:%S')} |")
        report.append(f"| 測試結束時間 | {self.df_1m.index.max().strftime('%Y-%m-%d %H:%M:%S')} |")
        report.append(f"| 總測試天數 | {(self.df_1m.index.max() - self.df_1m.index.min()).days} 天 |")
        report.append(f"| 原始資料K線數 | {len(self.df_1m):,} |")
        report.append("")
        
        # 成本設定
        cost_one_way = (self.config.taker_fee if self.config.use_taker else self.config.maker_fee) + self.config.slippage_bps / 10000.0
        report.append("## 💰 成本設定")
        report.append("")
        report.append("| 項目 | 數值 |")
        report.append("|------|------|")
        report.append(f"| 費率類型 | {'吃單費率' if self.config.use_taker else '掛單費率'} |")
        report.append(f"| 單邊成本 | {cost_one_way:.6f} ({cost_one_way*100:.4f}%) |")
        report.append(f"| 來回成本 | {cost_one_way*2:.6f} ({cost_one_way*2*100:.4f}%) |")
        report.append("")
        
        # 分析設定
        report.append("## ⚙️ 分析設定")
        report.append("")
        report.append("| 項目 | 數值 |")
        report.append("|------|------|")
        report.append(f"| ATR計算週期 | {self.config.atr_period} |")
        report.append(f"| Variance Ratio聚合尺度 | {self.config.vr_q} |")
        report.append(f"| 半衰期計算最大延遲 | {self.config.half_life_max_lag} |")
        report.append(f"| 動態最小資料量 | {'啟用' if self.config.use_dynamic_min_bars else '停用'} |")
        report.append("")
        
        # 時間框架分析結果
        report.append("## 📈 時間框架分析結果")
        report.append("")
        
        # 創建表格標題
        table_headers = ["時間框架", "K線數", "C/A", "VR", "半衰期", "波動率", "偏度", "峰度", "自相關", "市場效率", "通過C/A測試", "狀態"]
        report.append("| " + " | ".join(table_headers) + " |")
        report.append("|" + "|".join(["---"] * len(table_headers)) + "|")
        
        tested_timeframes = set(report_df['Timeframe'].tolist())
        
        for tf_label, rule in self.config.timeframes.items():
            if tf_label in tested_timeframes:
                row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
                
                # 格式化數值
                bars = f"{row['Bars']:,}"
                ca = f"{row['C_over_A']:.4f}" if not pd.isna(row['C_over_A']) else "N/A"
                vr = f"{row['VarianceRatio']:.4f}" if not pd.isna(row['VarianceRatio']) else "N/A"
                hl = f"{row['HalfLife_bars']:.1f}" if not pd.isna(row['HalfLife_bars']) else "N/A"
                vol = f"{row['Volatility_Ann']:.4f}" if not pd.isna(row['Volatility_Ann']) else "N/A"
                skew = f"{row['Skewness']:.4f}" if not pd.isna(row['Skewness']) else "N/A"
                kurt = f"{row['Kurtosis']:.4f}" if not pd.isna(row['Kurtosis']) else "N/A"
                autocorr = f"{row['Autocorr_Lag1']:.4f}" if not pd.isna(row['Autocorr_Lag1']) else "N/A"
                me = f"{row['Market_Efficiency']:.4f}" if not pd.isna(row['Market_Efficiency']) else "N/A"
                pass_ca = "✅" if row['Pass_CA_0.25'] else "❌"
                status = "✅ 已測試"
                
                report.append(f"| {tf_label} | {bars} | {ca} | {vr} | {hl} | {vol} | {skew} | {kurt} | {autocorr} | {me} | {pass_ca} | {status} |")
            else:
                report.append(f"| {tf_label} | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ❌ 未測試 |")
        
        report.append("")
        
        # 詳細分析
        report.append("### 🔍 詳細分析")
        report.append("")
        
        for tf_label, rule in self.config.timeframes.items():
            if tf_label in tested_timeframes:
                row = report_df[report_df['Timeframe'] == tf_label].iloc[0]
                report.append(f"#### 🕐 {row['Timeframe']} 時間框架")
                report.append("")
                report.append("**基本統計:**")
                report.append(f"- K線數量: {row['Bars']:,}")
                report.append(f"- 平均ATR: {row['Avg_ATR_pct']:.4f} ({row['Avg_ATR_pct']*100:.2f}%)")
                report.append(f"- 成本/波動比 (C/A): {row['C_over_A']:.4f}")
                report.append(f"- 走勢一致性 (VR): {row['VarianceRatio']:.4f}")
                report.append(f"- 訊號半衰期: {row['HalfLife_bars']:.1f} bars")
                report.append("")
                
                if not pd.isna(row['Volatility_Ann']):
                    report.append("**技術指標:**")
                    report.append(f"- 年化波動率: {row['Volatility_Ann']:.4f}")
                    report.append(f"- 報酬偏度: {row['Skewness']:.4f}")
                    report.append(f"- 報酬峰度: {row['Kurtosis']:.4f}")
                    report.append(f"- 自相關(Lag1): {row['Autocorr_Lag1']:.4f}")
                    report.append(f"- 市場效率比率: {row['Market_Efficiency']:.4f}")
                    report.append("")
                
                if row['Pass_CA_0.25']:
                    report.append("✅ **通過C/A < 0.25測試**")
                else:
                    report.append("❌ **未通過C/A < 0.25測試**")
                report.append("")
        
        # 綜合建議
        report.append("## 💡 綜合建議")
        report.append("")
        
        best_ca = report_df.loc[report_df['C_over_A'].idxmin()] if 'C_over_A' in report_df.columns else None
        best_vr = report_df.loc[report_df['VarianceRatio'].idxmax()] if 'VarianceRatio' in report_df.columns else None
        
        if best_ca is not None and not pd.isna(best_ca['C_over_A']):
            report.append(f"**最佳成本效率時間框架**: {best_ca['Timeframe']} (C/A: {best_ca['C_over_A']:.4f})")
        
        if best_vr is not None and not pd.isna(best_vr['VarianceRatio']):
            report.append(f"**最高趨勢性時間框架**: {best_vr['Timeframe']} (VR: {best_vr['VarianceRatio']:.4f})")
        
        report.append("")
        report.append("### 📋 指標解讀指南")
        report.append("")
        report.append("- **C/A < 0.25**: 成本相對於波動率較低，適合交易")
        report.append("- **VR > 1**: 偏趨勢市場，適合趨勢策略")
        report.append("- **VR < 1**: 偏均值回歸市場，適合均值回歸策略")
        report.append("- **半衰期**: 建議bar週期約為0.5~1倍半衰期")
        report.append("- **波動率**: 反映市場波動程度")
        report.append("- **偏度**: 正偏度表示右尾較長，負偏度表示左尾較長")
        report.append("- **峰度**: 高峰度表示極端值較多")
        report.append("- **自相關**: 正值表示趨勢性，負值表示均值回歸")
        report.append("- **市場效率比率**: 越接近1表示市場越有效率")
        
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
