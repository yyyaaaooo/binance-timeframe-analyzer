# Binance 時間框架分析器

一個強大的 Binance 交易對時間框架分析工具，支援所有現貨和永續合約交易對的分析。

## 🚀 主要功能

- **支援所有 Binance 交易對**: 現貨和永續合約
- **正確的 API 端點**: 自動使用對應的現貨或永續合約 API
- **多時間框架分析**: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- **技術指標計算**: ATR, Variance Ratio, 訊號半衰期
- **統計特性分析**: 波動率、偏度、峰度、自相關等技術指標
- **市場效率評估**: 基於方差比的市場效率分析
- **多格式報告**: CSV, TXT, MD 格式
- **智能資料管理**: 自動下載、增量更新、品質檢查

## 📁 檔案結構

```
timeframe selector ethusdt/
├── binance_analyzer_config.py      # 配置類
├── binance_api_utils.py            # API 工具類
├── binance_timeframe_analyzer.py   # 主要分析器
├── example_usage.py                # 使用範例
├── README_binance_analyzer.md      # 說明文件
├── requirements.txt                # 依賴套件
└── data/                          # 資料和報告目錄
    ├── ethusdt_spot_1m.csv        # 原始資料
    ├── ethusdt_spot_timeframe_report_*.csv  # 分析報告
    └── ...
```

## 🛠️ 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 基本使用

```python
from binance_analyzer_config import BinanceConfig
from binance_timeframe_analyzer import BinanceTimeframeAnalyzer

# 創建配置
config = BinanceConfig(
    symbol="ETHUSDT",
    market_type="spot",  # 或 "futures"
    data_days=365
)

# 執行分析
analyzer = BinanceTimeframeAnalyzer(config)
report_df = analyzer.run_analysis()
```

### 3. 快速分析

```python
from binance_timeframe_analyzer import analyze_symbol

# 快速分析 ETHUSDT 現貨
report_df = analyze_symbol("ETHUSDT", "spot", 365)

# 快速分析 BTCUSDT 永續合約
report_df = analyze_symbol("BTCUSDT", "futures", 730)
```

## 📊 分析指標

### 成本/波動比 (C/A)
- **定義**: 來回交易成本 / 平均 ATR
- **標準**: C/A < 0.25 表示成本相對於波動率較低
- **意義**: 評估交易可行性

### 走勢一致性 (Variance Ratio)
- **VR > 1**: 偏趨勢市場，適合趨勢策略
- **VR < 1**: 偏均值回歸市場，適合均值回歸策略
- **意義**: 判斷市場特性

### 訊號半衰期
- **定義**: 基於報酬自相關衰減的近似
- **建議**: bar 週期約為 0.5~1 倍半衰期
- **意義**: 指導時間框架選擇

### 統計指標
- **年化波動率**: 反映市場波動程度
- **報酬偏度**: 正偏度表示右尾較長，負偏度表示左尾較長
- **報酬峰度**: 高峰度表示極端值較多
- **自相關**: 正值表示趨勢性，負值表示均值回歸
- **市場效率比率**: 越接近1表示市場越有效率

## 🔧 配置選項

### 基本設定
```python
config = BinanceConfig(
    symbol="ETHUSDT",           # 交易對
    market_type="spot",         # 市場類型: "spot" 或 "futures"
    data_days=1095,            # 資料天數
    auto_fetch=True,           # 自動抓取資料
    save_csv=True              # 儲存 CSV
)
```

### 成本設定
```python
# 現貨費率
spot_taker_fee=0.001,          # 現貨吃單費率 0.1%
spot_maker_fee=0.001,          # 現貨掛單費率 0.1%

# 永續合約費率
futures_taker_fee=0.0004,      # 永續合約吃單費率 0.04%
futures_maker_fee=0.0002,      # 永續合約掛單費率 0.02%

slippage_bps=2.0,              # 滑點 2 bps
use_taker=True                 # 使用吃單費率
```

### 技術指標參數
```python
# 技術指標參數
atr_period=14,                 # ATR計算週期
vr_q=4,                       # Variance Ratio聚合尺度
half_life_max_lag=100,        # 半衰期計算最大延遲
```

## 📈 使用範例

### 範例 1: 分析 ETHUSDT 現貨
```python
from binance_timeframe_analyzer import analyze_symbol

# 分析 ETHUSDT 現貨，使用 1 年資料
report_df = analyze_symbol("ETHUSDT", "spot", 365)
print(report_df)
```

### 範例 2: 分析 BTCUSDT 永續合約
```python
# 分析 BTCUSDT 永續合約，使用 2 年資料
report_df = analyze_symbol("BTCUSDT", "futures", 730)
print(report_df)
```

### 範例 3: 獲取可用交易對
```python
from binance_timeframe_analyzer import get_available_symbols, get_popular_symbols

# 獲取所有現貨交易對
spot_symbols = get_available_symbols("spot")
print(f"現貨交易對數量: {len(spot_symbols)}")

# 獲取熱門永續合約交易對
popular_futures = get_popular_symbols("futures", 20)
print("熱門永續合約:", popular_futures)
```

### 範例 4: 批量分析
```python
symbols_to_analyze = [
    ("ETHUSDT", "spot"),
    ("BTCUSDT", "futures"),
    ("ADAUSDT", "spot")
]

results = {}
for symbol, market_type in symbols_to_analyze:
    try:
        report_df = analyze_symbol(symbol, market_type, 90)
        results[f"{symbol}_{market_type}"] = report_df
        print(f"✅ {symbol} {market_type} 分析完成")
    except Exception as e:
        print(f"❌ {symbol} {market_type} 分析失敗: {e}")
```

## 📋 報告解讀

### 1. 優先順序
1. **C/A < 0.25**: 成本相對於波動率較低，適合交易
2. **Variance Ratio**: 判斷市場特性（趨勢 vs 均值回歸）
3. **技術指標**: 了解市場統計特性

### 2. 市場特性判斷
- **VR > 1**: 偏趨勢市場，適合趨勢策略
- **VR < 1**: 偏均值回歸市場，適合均值回歸策略

### 3. 時間框架選擇
- **半衰期**: 建議 bar 週期約為 0.5~1 倍半衰期
- **交易頻率**: 考慮交易成本和滑點影響

## 🔍 API 端點差異

### 現貨 API
- **K線資料**: `https://api.binance.com/api/v3/klines`
- **交易所資訊**: `https://api.binance.com/api/v3/exchangeInfo`
- **24小時統計**: `https://api.binance.com/api/v3/ticker/24hr`

### 永續合約 API
- **K線資料**: `https://fapi.binance.com/fapi/v1/klines`
- **交易所資訊**: `https://fapi.binance.com/fapi/v1/exchangeInfo`
- **24小時統計**: `https://fapi.binance.com/fapi/v1/ticker/24hr`

## ⚠️ 注意事項

1. **API 限制**: Binance API 有請求頻率限制，程式已內建延遲機制
2. **資料品質**: 建議啟用資料品質檢查，確保分析結果可靠性
3. **網路連線**: 需要穩定的網路連線來下載歷史資料
4. **記憶體使用**: 長時間資料分析可能消耗較多記憶體
5. **交易成本**: 不同市場類型的費率結構不同，請根據實際情況調整

## 🚀 進階功能

### 自定義時間框架
```python
config = BinanceConfig(
    symbol="ETHUSDT",
    market_type="spot",
    timeframes={
        "5m": "5T",
        "15m": "15T", 
        "1h": "1H",
        "4h": "4H",
        "1d": "1D"
    }
)
```

### 自定義策略參數
```python
config = BinanceConfig(
    symbol="ETHUSDT",
    market_type="spot",
    ma_fast_grid=[3, 5, 8],
    ma_slow_grid=[15, 25, 40],
    rsi_window_grid=[10, 14, 20],
    rsi_band_grid=[(25, 75), (20, 80)]
)
```

### 資料管理
```python
config = BinanceConfig(
    symbol="ETHUSDT",
    market_type="spot",
    force_redownload=False,      # 強制重新下載
    incremental_update=True,     # 增量更新
    data_quality_check=True,     # 資料品質檢查
    min_data_quality_score=0.8   # 最低品質分數
)
```

## 📞 支援

如有問題或建議，請檢查：
1. 網路連線是否正常
2. 交易對是否存在且可交易
3. 資料天數是否合理
4. API 限制是否超額

## 📄 授權

本專案僅供學習和研究使用，請遵守 Binance 的 API 使用條款。
