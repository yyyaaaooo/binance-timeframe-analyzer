# 趨勢分析系統

這是一個完整的趨勢分析系統，用於檢測加密貨幣市場中的趨勢模式並分析趨勢是否集中在特定時段。

## 系統概述

本系統基於您提供的分析框架，實現了以下核心功能：

### 一、趨勢檢測
- **多時間框架分析**：支援 30分鐘、1小時、4小時等多個滾動窗格
- **綜合趨勢分數**：結合線性回歸擬合度、ADX、方向一致性、移動幅度/實現波動比
- **智能分類**：自動將市場狀態分類為趨勢、盤整、不明

### 二、時段分析
- **時區轉換**：自動轉換為台北時區進行分析
- **多維度彙總**：按小時、星期、月份進行統計
- **趨勢方向分析**：區分多頭和空頭趨勢

### 三、統計檢定
- **卡方檢定**：檢驗趨勢分佈是否均勻
- **ANOVA/Kruskal-Wallis**：檢驗各時段趨勢分數差異
- **多重比較校正**：Benjamini-Hochberg 方法
- **Bootstrap 信賴區間**：提供統計可靠性評估

### 四、視覺化
- **24×7 熱力圖**：顯示星期×小時的趨勢比例
- **趨勢分數箱形圖**：比較各時段的趨勢強度
- **趨勢方向玫瑰圖**：展示多空趨勢分佈
- **ADX vs R² 散點圖**：分析技術指標關係

## 安裝與設定

### 1. 安裝依賴項
```bash
pip install -r requirements.txt
```

### 2. 依賴項說明
- `numpy>=1.21.0`：數值計算
- `pandas>=1.3.0`：數據處理
- `scipy>=1.7.0`：統計檢定
- `matplotlib>=3.5.0`：圖表繪製
- `seaborn>=0.11.0`：統計視覺化
- `pytz>=2021.1`：時區處理
- `requests>=2.25.0`：API 請求

## 使用方法

### 快速開始

#### 方法一：使用範例腳本
```bash
python example_trend_analysis.py
```

#### 方法二：直接使用主腳本
```bash
python trend_analysis_main.py
```

#### 方法三：自定義分析
```python
from trend_analysis_main import TrendAnalysisMain

# 創建分析器
analyzer = TrendAnalysisMain(
    symbol='BTCUSDT',           # 交易對
    market_type='spot',         # 市場類型: 'spot' 或 'futures'
    data_days=1095,            # 資料天數 (3年)
    windows=[30, 60, 240]      # 滾動窗格 (分鐘)
)

# 執行完整分析
results = analyzer.run_complete_analysis(save_results=True)
```

### 進階使用

#### 1. 趨勢檢測
```python
from trend_detector import TrendDetector

detector = TrendDetector(windows=[30, 60, 240])
trend_results = detector.detect_trends(df)
```

#### 2. 時段分析
```python
from time_period_analyzer import TimePeriodAnalyzer

analyzer = TimePeriodAnalyzer(target_timezone='Asia/Taipei')
time_analysis = analyzer.analyze_time_periods(trend_data)
```

#### 3. 統計檢定
```python
from trend_statistics import TrendStatistics

stats = TrendStatistics()
statistical_results = stats.perform_comprehensive_tests(
    trend_data, 'timestamp', 'trend_score', 'hour'
)
```

#### 4. 視覺化
```python
from trend_visualizer import TrendVisualizer

visualizer = TrendVisualizer()
figures = visualizer.create_comprehensive_dashboard(
    trend_data, time_analysis, save_dir='results'
)
```

## 輸出結果

### 1. 分析報告 (TXT 格式)
- 基本統計資訊
- 時段分析結果
- 統計檢定結果
- 結論與建議

### 2. 視覺化圖表 (PNG 格式)
- `heatmap.png`：24×7 趨勢熱力圖
- `trend_score_boxplot.png`：趨勢分數箱形圖
- `trend_direction_rose.png`：趨勢方向玫瑰圖
- `trend_proportion_bar.png`：趨勢比例長條圖
- `adx_r_squared_scatter.png`：ADX vs R² 散點圖

### 3. 數據檔案
- CSV 格式的原始數據
- 處理後的趨勢數據

## 核心算法說明

### 趨勢分數計算
```
TrendScore = 35·R² + 25·min(ADX,50)/50 + 20·方向一致性 + 20·clip((Range/Vol)/3,0,1)
```

### 趨勢分類規則
- **趨勢**：TrendScore ≥ 60 且 |斜率 t| ≥ 2
- **盤整**：TrendScore ≤ 40 且 ADX ≤ 18 且 |累積報酬| ≤ 0.8·實現波動
- **不明**：其餘情況

### 統計檢定
- **卡方檢定**：檢驗趨勢分佈是否均勻
- **ANOVA**：檢驗各時段趨勢分數均值差異
- **Kruskal-Wallis**：非參數版本的多組比較

## 系統架構

```
trend_analysis_main.py          # 主分析腳本
├── trend_detector.py           # 趨勢檢測模組
├── trend_statistics.py         # 統計檢定模組
├── time_period_analyzer.py     # 時段分析模組
├── trend_visualizer.py         # 視覺化模組
└── example_trend_analysis.py   # 使用範例
```

## 注意事項

1. **網路連接**：首次運行需要下載歷史數據，請確保網路連接穩定
2. **計算時間**：長時間範圍的分析可能需要較長計算時間
3. **記憶體使用**：大量數據分析時請注意記憶體使用量
4. **時區設定**：系統預設使用台北時區，可自定義修改

## 故障排除

### 常見問題

1. **依賴項安裝失敗**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **中文字體顯示問題**
   - Windows：確保系統安裝了中文字體
   - macOS：使用 Arial Unicode MS
   - Linux：安裝 SimHei 字體

3. **數據下載失敗**
   - 檢查網路連接
   - 確認交易對符號正確
   - 檢查 Binance API 狀態

4. **記憶體不足**
   - 減少數據天數
   - 減少滾動窗格數量
   - 分批處理數據

## 更新日誌

### v1.0.0 (2024-01-XX)
- 初始版本發布
- 實現完整的趨勢分析功能
- 支援多時間框架分析
- 提供統計檢定和視覺化

## 授權

本專案採用 MIT 授權條款。

## 貢獻

歡迎提交 Issue 和 Pull Request 來改善系統功能。

## 聯絡資訊

如有問題或建議，請透過 GitHub Issues 聯絡。
