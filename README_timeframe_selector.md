
# ETHUSDT 時間框架特性分析工具

## 功能特色

這個工具可以自動分析ETHUSDT在不同時間框架下的市場特性，幫助選擇最適合的交易時間框架。

### 主要功能

1. **自動資料抓取**：從Binance API自動抓取ETHUSDT歷史資料
2. **多時間框架分析**：支援1m/5m/15m/1h/4h/1d/1w時間框架
3. **技術指標計算**：
   - 成本/波動比 (C/A)
   - 走勢一致性 (Variance Ratio)
   - 訊號半衰期
   - 年化波動率
   - 報酬偏度與峰度
   - 自相關分析
   - 市場效率比率
4. **時間框架特性評估**：基於客觀技術指標評估各時間框架的市場特性

## 安裝需求

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 智能資料管理（推薦）

程式會自動檢查現有資料，智能決定是否需要下載或更新：

```python
# 在 Config 類別中設定
auto_fetch: bool = True                    # 啟用自動抓取
incremental_update: bool = True            # 增量更新（只下載缺失的資料）
force_redownload: bool = False             # 強制重新下載（覆蓋現有資料）
data_quality_check: bool = True            # 啟用資料品質檢查
min_data_quality_score: float = 0.8        # 最低資料品質分數（0-1）
```

### 2. 互動式資料管理工具

使用專門的資料管理工具：

```bash
python data_manager.py
```

功能包括：
- 檢查現有資料狀態
- 檢查資料品質
- 智能資料載入
- 強制重新下載
- 增量更新資料
- 產生詳細資料報告
- 修改配置設定

### 3. 本地CSV模式

如果已有CSV檔案：

```python
auto_fetch: bool = False                   # 關閉自動抓取
csv_path: str = "/path/to/your/data.csv"   # CSV檔案路徑
```

## 配置說明

### 資料抓取設定

```python
@dataclass
class Config:
    # 資料抓取設定
    symbol: str = "ETHUSDT"                    # 交易對
    exchange: str = "binance"                  # 交易所
    data_days: int = 365                       # 要抓取的天數
    auto_fetch: bool = True                    # 是否自動抓取資料
    save_csv: bool = True                      # 是否儲存CSV檔案
    
    # 資料管理設定
    force_redownload: bool = False             # 強制重新下載（覆蓋現有資料）
    incremental_update: bool = True            # 增量更新（只下載缺失的資料）
    data_quality_check: bool = True            # 啟用資料品質檢查
    min_data_quality_score: float = 0.8        # 最低資料品質分數（0-1）
    
    # 報告格式設定
    generate_csv_report: bool = True           # 生成CSV報告
    generate_txt_report: bool = True           # 生成TXT報告
    generate_md_report: bool = True            # 生成MD報告
```

### 報告格式設定

```python
# 報告格式設定
generate_csv_report: bool = True           # 生成CSV報告
generate_txt_report: bool = True           # 生成TXT報告
generate_md_report: bool = True            # 生成MD報告
```

### 交易成本設定

```python
# 成本假設（單邊，一次成交）
taker_fee: float = 0.0004     # 0.04% 吃單費率
maker_fee: float = 0.0002     # 0.02% 掛單費率
slippage_bps: float = 2.0     # 2 bps = 0.02% 滑點
use_taker: bool = True        # True: 用吃單費率；False: 用掛單費率
```

### 技術指標參數

```python
# 技術指標參數
atr_period: int = 14          # ATR計算週期
vr_q: int = 4                 # Variance Ratio聚合尺度
half_life_max_lag: int = 100  # 半衰期計算最大延遲
```

## 執行方式

### 主程式
```bash
python timeframe_selector_ethusdt.py
```

### 資料管理工具
```bash
python data_manager.py
```

### 測試資料抓取
```bash
python test_data_fetch.py
```

### 報告格式配置範例

您可以通過修改Config類別來控制報告格式的生成：

```python
# 只生成CSV報告
cfg = Config(
    generate_csv_report=True,
    generate_txt_report=False,
    generate_md_report=False
)

# 只生成TXT和MD報告
cfg = Config(
    generate_csv_report=False,
    generate_txt_report=True,
    generate_md_report=True
)

# 生成所有格式的報告（預設）
cfg = Config(
    generate_csv_report=True,
    generate_txt_report=True,
    generate_md_report=True
)
```

## 輸出結果

程式會產生以下檔案：

1. **ethusdt_1m.csv**：抓取的1分鐘原始資料（如果啟用save_csv）
2. **ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.csv**：時間框架分析報告（CSV格式）
3. **ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.txt**：詳細的時間框架分析報告（TXT格式）
4. **ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.md**：詳細的時間框架分析報告（Markdown格式）
5. **ethusdt_1m_report.txt**：詳細的資料品質報告

**注意**：報告檔名中的日期格式為 YYYYMMDD-YYYYMMDD，例如 `ethusdt_timeframe_report_20230101-20231231.csv`

### 檔名格式說明

報告檔名會自動包含測試的日期區間，格式如下：
- **CSV報告**: `ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.csv`
- **TXT報告**: `ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.txt`
- **MD報告**: `ethusdt_timeframe_report_YYYYMMDD-YYYYMMDD.md`

其中：
- `YYYYMMDD` 為測試開始日期（8位數字格式）
- `-` 為分隔符號
- `YYYYMMDD` 為測試結束日期（8位數字格式）

**範例**：
- `ethusdt_timeframe_report_20230101-20231231.csv` 表示測試期間為2023年1月1日到2023年12月31日
- `ethusdt_timeframe_report_20240101-20240630.csv` 表示測試期間為2024年1月1日到2024年6月30日

**檔名優勢**：
- 自動識別測試期間，無需手動記錄
- 便於管理多個不同時期的分析報告
- 避免檔案覆蓋，保留歷史分析結果
- 支援檔案排序，按時間順序組織報告

### 報告格式說明

#### CSV報告 (ethusdt_timeframe_report.csv)
- 結構化數據，適合進一步分析
- 包含所有時間框架的技術指標
- 可用Excel或其他工具開啟

#### TXT報告 (ethusdt_timeframe_report.txt)
- 純文字格式，易於閱讀
- 包含完整的測試資訊，包括：
  - 測試日期範圍
  - 成本設定詳情
  - 技術指標參數配置
  - 各時間框架詳細分析
  - 綜合建議和指標解讀

#### Markdown報告 (ethusdt_timeframe_report.md)
- 結構化格式，支援表格和標題
- 適合在GitHub、文檔系統中顯示
- 包含與TXT報告相同的完整資訊
- 支援表格格式的結果展示

### 資料品質檢查項目

程式會自動檢查以下項目：
- **基本結構**：必要欄位是否存在
- **時間序列完整性**：時間間隔是否正確（1分鐘）
- **重複資料**：是否有重複的時間戳記
- **缺失值**：是否有空值或NaN
- **價格邏輯**：OHLC價格關係是否正確
- **異常值**：是否有零值或負值
- **成交量**：是否有負成交量
- **時間範圍**：是否包含未來時間

品質分數範圍：0.0-1.0，建議保持0.8以上

### 報告解讀

#### 基本資訊
- **測試日期範圍**：報告會顯示完整的測試時間範圍，包括開始和結束時間
- **總測試天數**：顯示測試涵蓋的總天數
- **原始資料K線數**：顯示使用的1分鐘K線總數

#### 技術指標
1. **C_over_A < 0.25**：成本/波動比，越低越好
2. **VarianceRatio**：
   - > 1：偏趨勢市場
   - < 1：偏均值回歸市場
3. **HalfLife_bars**：訊號半衰期，建議bar週期約為0.5~1倍半衰期
4. **Volatility_Ann**：年化波動率，反映市場波動程度
5. **Skewness**：報酬偏度，正偏度表示右尾較長，負偏度表示左尾較長
6. **Kurtosis**：報酬峰度，高峰度表示極端值較多
7. **Autocorr_Lag1**：一階自相關，正值表示趨勢性，負值表示均值回歸
8. **Market_Efficiency**：市場效率比率，基於方差比

#### 時間框架特性評估
- **成本效率**：基於C/A指標評估交易成本相對波動的合理性
- **市場特性**：基於VR指標判斷市場是趨勢性還是均值回歸
- **統計特性**：透過偏度、峰度、自相關等指標了解市場分佈特性

## 注意事項

1. **網路連線**：自動抓取模式需要穩定的網路連線
2. **API限制**：Binance API有請求頻率限制，程式已內建延遲機制
3. **資料品質**：Binance是全球最大加密貨幣交易所，資料品質有保障
4. **時區設定**：預設使用UTC時區，可根據需要調整

## 技術細節

- **資料來源**：Binance REST API v3
- **資料格式**：1分鐘OHLCV K線資料
- **分析方法**：基於技術指標的客觀分析
- **評估指標**：成本效率、市場特性、統計分佈

## 支援的交易對

目前支援所有Binance現貨交易對，預設為ETHUSDT。可修改Config中的symbol參數來分析其他交易對。
