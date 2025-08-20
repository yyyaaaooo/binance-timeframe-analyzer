# 📁 資料目錄說明

## 🎯 版本控制策略

### ✅ 納入版本控制的資料
- **分析報告檔案** (小檔案，有價值)
  - `*_timeframe_report_*.md` - Markdown 格式分析報告
  - `*_timeframe_report_*.txt` - 文字格式分析報告  
  - `*_timeframe_report_*.csv` - CSV 格式分析報告

### ❌ 不納入版本控制的資料
- **大型原始資料檔案**
  - `*_1m.csv` - 1分鐘K線資料 (每個檔案約180-200MB)
  - `*_5m.csv` - 5分鐘K線資料
  - `*_15m.csv` - 15分鐘K線資料
  - `*_1h.csv` - 1小時K線資料
  - `*_4h.csv` - 4小時K線資料
  - `*_1d.csv` - 日線K線資料
  - `*_1w.csv` - 週線K線資料

- **動態生成的資料**
  - 可以重新下載的資料

## 📊 檔案命名規則

### 分析報告檔案
```
{symbol}_{market_type}_timeframe_report_{start_date}-{end_date}.{format}
```

範例：
- `ethusdt_spot_timeframe_report_20220820-20250819.md`
- `btcusdt_futures_timeframe_report_20220820-20250819.txt`
- `ethusdt_spot_timeframe_report_20220820-20250819.csv`

### 原始資料檔案
```
{symbol}_{market_type}_{timeframe}.csv
```

範例：
- `ethusdt_spot_1m.csv`
- `btcusdt_futures_1m.csv`

## 🔄 資料恢復機制

### 重新下載原始資料
如果原始資料檔案遺失，可以使用以下方式重新下載：

```python
from binance_timeframe_analyzer import analyze_symbol

# 重新下載 ETHUSDT 現貨 3年資料
analyze_symbol("ETHUSDT", "spot", 1095)

# 重新下載 BTCUSDT 期貨 3年資料  
analyze_symbol("BTCUSDT", "futures", 1095)
```

### 批量重新下載
```python
from analyze_btc_eth_3years import analyze_all_symbols

# 重新下載所有交易對的資料
analyze_all_symbols()
```

## 📈 分析報告內容

### 包含的分析指標
- **成本/波動比 (C/A)**: 評估交易成本相對於市場波動的合理性
- **走勢一致性 (VR)**: 判斷市場是趨勢型還是均值回歸型
- **訊號半衰期**: 技術指標的有效期
- **年化波動率**: 市場波動程度
- **報酬偏度/峰度**: 報酬分布的統計特性
- **自相關**: 價格變動的相關性
- **市場效率比率**: 市場效率評估

### 時間框架分析
- 1m, 5m, 15m, 1h, 4h, 1d, 1w 時間框架
- 每個時間框架的詳細統計分析
- 策略回測結果 (MA趨勢策略、RSI均值回歸策略)

## 🛠️ 資料管理工具

### 檢查資料完整性
```python
import os

def check_data_integrity():
    """檢查資料完整性"""
    required_files = [
        "data/ethusdt_spot_1m.csv",
        "data/btcusdt_spot_1m.csv",
        "data/ethusdt_futures_1m.csv", 
        "data/btcusdt_futures_1m.csv"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("缺少以下資料檔案:")
        for file in missing_files:
            print(f"  - {file}")
        print("\n請執行資料下載腳本重新獲取資料")
    else:
        print("所有資料檔案完整")
```

### 清理舊資料
```python
import os
import glob

def cleanup_old_data(days_to_keep=30):
    """清理超過指定天數的舊資料"""
    import time
    current_time = time.time()
    
    # 清理舊的原始資料檔案
    csv_files = glob.glob("data/*_1m.csv")
    for file in csv_files:
        file_time = os.path.getmtime(file)
        if (current_time - file_time) > (days_to_keep * 24 * 3600):
            os.remove(file)
            print(f"已刪除舊檔案: {file}")
```

## 📋 注意事項

1. **檔案大小**: 原始資料檔案較大，建議定期清理
2. **API限制**: Binance API 有請求頻率限制，下載大量資料時需要時間
3. **網路連線**: 確保網路連線穩定，避免下載中斷
4. **磁碟空間**: 確保有足夠的磁碟空間存儲資料
5. **備份策略**: 重要的分析報告建議定期備份

## 🔗 相關檔案

- `binance_timeframe_analyzer.py` - 主要分析器
- `analyze_btc_eth_3years.py` - 批量分析腳本
- `binance_api_utils.py` - API 工具類
- `binance_analyzer_config.py` - 配置類別
