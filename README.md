# Binance 時間框架分析器 🚀

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-brightgreen.svg)](https://github.com/yyyaaaooo/binance-timeframe-analyzer)

一個強大的 Binance 交易對時間框架分析工具，支援所有現貨和永續合約交易對的分析，幫助您找到最適合的交易時間框架。

## ✨ 主要特色

- 🔥 **支援所有 Binance 交易對**: 現貨和永續合約
- 📊 **多時間框架分析**: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- 📈 **技術指標計算**: ATR, Variance Ratio, 訊號半衰期
- 🎯 **策略回測**: MA 趨勢策略和 RSI 均值回歸策略
- 🔬 **Walk-forward 評估**: 樣本外測試確保策略穩定性
- 📋 **多格式報告**: CSV, TXT, MD 格式
- 🧠 **智能資料管理**: 自動下載、增量更新、品質檢查

## 🚀 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from binance_timeframe_analyzer import analyze_symbol

# 分析 ETHUSDT 現貨
report_df = analyze_symbol("ETHUSDT", "spot", 365)
print(report_df)
```

### 分析結果示例

| 時間框架 | C/A 比率 | Variance Ratio | 樣本外夏普比率 | 建議策略 |
|---------|---------|----------------|---------------|----------|
| 5m      | 0.15    | 1.2            | 0.85          | MA 趨勢  |
| 15m     | 0.12    | 1.1            | 1.02          | MA 趨勢  |
| 1h      | 0.08    | 0.9            | 1.15          | RSI 均值回歸 |
| 4h      | 0.06    | 0.8            | 1.25          | RSI 均值回歸 |

## 📁 項目結構

```
binance-timeframe-analyzer/
├── binance_analyzer_config.py      # 配置類
├── binance_api_utils.py            # API 工具類
├── binance_timeframe_analyzer.py   # 主要分析器
├── data_manager.py                 # 資料管理
├── example_usage.py                # 使用範例
├── timeframe_selector_ethusdt.py   # ETHUSDT 專用分析器
├── test_expanded_features.py       # 功能測試
├── requirements.txt                # 依賴套件
├── README.md                       # 主說明文件
├── README_binance_analyzer.md      # 詳細說明文件
└── data/                          # 資料和報告目錄
    ├── *.csv                      # 分析報告
    ├── *.txt                      # 文字報告
    └── *.md                       # Markdown 報告
```

## 🔧 核心功能

### 1. 成本/波動比分析 (C/A)
- 評估交易成本相對於市場波動率的合理性
- C/A < 0.25 表示成本相對於波動率較低，適合交易

### 2. 市場特性分析 (Variance Ratio)
- VR > 1: 偏趨勢市場，適合趨勢策略
- VR < 1: 偏均值回歸市場，適合均值回歸策略

### 3. 策略回測
- **MA 趨勢策略**: 適合趨勢市場
- **RSI 均值回歸策略**: 適合均值回歸市場
- **Walk-forward 評估**: 確保策略穩定性

### 4. 智能資料管理
- 自動下載歷史資料
- 增量更新機制
- 資料品質檢查
- 多格式報告輸出

## 📊 使用範例

### 分析單一交易對

```python
from binance_timeframe_analyzer import analyze_symbol

# 分析 ETHUSDT 現貨
report_df = analyze_symbol("ETHUSDT", "spot", 365)

# 分析 BTCUSDT 永續合約
report_df = analyze_symbol("BTCUSDT", "futures", 730)
```

### 批量分析多個交易對

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

### 獲取可用交易對

```python
from binance_timeframe_analyzer import get_available_symbols, get_popular_symbols

# 獲取所有現貨交易對
spot_symbols = get_available_symbols("spot")
print(f"現貨交易對數量: {len(spot_symbols)}")

# 獲取熱門永續合約交易對
popular_futures = get_popular_symbols("futures", 20)
print("熱門永續合約:", popular_futures)
```

## 📈 分析指標說明

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

### 策略表現指標
- **樣本外夏普比率**: 越高越好，表示策略穩定性
- **樣本外最大回撤**: 越低越好，表示風險控制
- **勝率**: 獲利交易比例
- **獲利因子**: 總獲利 / 總虧損

## ⚙️ 配置選項

```python
from binance_analyzer_config import BinanceConfig

config = BinanceConfig(
    symbol="ETHUSDT",           # 交易對
    market_type="spot",         # 市場類型: "spot" 或 "futures"
    data_days=1095,            # 資料天數
    auto_fetch=True,           # 自動抓取資料
    save_csv=True,             # 儲存 CSV
    spot_taker_fee=0.001,      # 現貨吃單費率 0.1%
    futures_taker_fee=0.0004,  # 永續合約吃單費率 0.04%
    slippage_bps=2.0,          # 滑點 2 bps
    use_taker=True             # 使用吃單費率
)
```

## 🚨 注意事項

1. **API 限制**: Binance API 有請求頻率限制，程式已內建延遲機制
2. **資料品質**: 建議啟用資料品質檢查，確保分析結果可靠性
3. **網路連線**: 需要穩定的網路連線來下載歷史資料
4. **記憶體使用**: 長時間資料分析可能消耗較多記憶體
5. **交易成本**: 不同市場類型的費率結構不同，請根據實際情況調整

## 📚 詳細文檔

- [詳細使用說明](README_binance_analyzer.md)
- [動態最小 bar 數說明](README_dynamic_min_bars.md)
- [時間框架選擇器說明](README_timeframe_selector.md)
- [策略移除更新日誌](CHANGELOG_strategy_removal.md)

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## ⚠️ 免責聲明

本專案僅供學習和研究使用，不構成投資建議。請遵守 Binance 的 API 使用條款，並自行承擔投資風險。

---

⭐ 如果這個項目對您有幫助，請給我們一個星標！
