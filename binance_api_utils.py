# -*- coding: utf-8 -*-
"""
Binance API 工具類
支援現貨和永續合約的正確 API 端點
"""

import requests
import time
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

class BinanceAPI:
    """Binance API 工具類"""
    
    @staticmethod
    def get_klines_url(market_type: str) -> str:
        """根據市場類型返回對應的 K線 API URL"""
        if market_type == "futures":
            return "https://fapi.binance.com/fapi/v1/klines"
        else:  # spot
            return "https://api.binance.com/api/v3/klines"
    
    @staticmethod
    def get_exchange_info_url(market_type: str) -> str:
        """根據市場類型返回對應的交易所資訊 API URL"""
        if market_type == "futures":
            return "https://fapi.binance.com/fapi/v1/exchangeInfo"
        else:  # spot
            return "https://api.binance.com/api/v3/exchangeInfo"
    
    @staticmethod
    def get_ticker_url(market_type: str) -> str:
        """根據市場類型返回對應的價格 API URL"""
        if market_type == "futures":
            return "https://fapi.binance.com/fapi/v1/ticker/24hr"
        else:  # spot
            return "https://api.binance.com/api/v3/ticker/24hr"
    
    @staticmethod
    def fetch_klines(symbol: str, market_type: str, interval: str, 
                    start_time: int, end_time: int) -> List[List]:
        """從 Binance API 抓取 K線資料"""
        url = BinanceAPI.get_klines_url(market_type)
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"抓取資料時發生錯誤: {e}")
            return []
    
    @staticmethod
    def get_available_symbols(market_type: str) -> List[str]:
        """獲取可用的交易對列表"""
        url = BinanceAPI.get_exchange_info_url(market_type)
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            symbols = []
            for symbol_info in data['symbols']:
                if symbol_info['status'] == 'TRADING':
                    symbols.append(symbol_info['symbol'])
            
            return symbols
        except Exception as e:
            print(f"獲取交易對列表失敗: {e}")
            return []
    
    @staticmethod
    def get_symbol_info(symbol: str, market_type: str) -> Dict:
        """獲取特定交易對的詳細資訊"""
        url = BinanceAPI.get_exchange_info_url(market_type)
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for symbol_info in data['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            
            return {}
        except Exception as e:
            print(f"獲取交易對資訊失敗: {e}")
            return {}
    
    @staticmethod
    def get_24hr_ticker(symbol: str, market_type: str) -> Dict:
        """獲取24小時價格統計"""
        url = BinanceAPI.get_ticker_url(market_type)
        params = {"symbol": symbol}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"獲取24小時價格統計失敗: {e}")
            return {}
    
    @staticmethod
    def fetch_historical_data(symbol: str, market_type: str, days: int, 
                            interval: str = "1m") -> pd.DataFrame:
        """抓取指定天數的歷史資料"""
        print(f"開始從 Binance {market_type} 抓取 {symbol} {interval} 資料，共 {days} 天...")
        
        # 計算時間範圍
        end_time = int(time.time() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            current_end = min(current_start + (1000 * 60 * 1000), end_time)
            
            print(f"抓取 {datetime.fromtimestamp(current_start/1000)} 到 {datetime.fromtimestamp(current_end/1000)} 的資料...")
            
            klines = BinanceAPI.fetch_klines(symbol, market_type, interval, current_start, current_end)
            
            if not klines:
                print("警告：此時間範圍沒有資料，跳過...")
                current_start = current_end
                continue
            
            all_data.extend(klines)
            current_start = current_end
            time.sleep(0.1)  # 避免請求過於頻繁
        
        if not all_data:
            raise ValueError("沒有抓取到任何資料")
        
        # 轉換為 DataFrame
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # 轉換資料類型
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # 設定時區
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        
        # 排序並去重
        df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        df = df.set_index('timestamp')
        
        print(f"成功抓取 {len(df)} 根K線資料")
        print(f"資料時間範圍: {df.index.min()} 到 {df.index.max()}")
        
        return df
    
    @staticmethod
    def validate_symbol(symbol: str, market_type: str) -> bool:
        """驗證交易對是否存在且可交易"""
        try:
            symbol_info = BinanceAPI.get_symbol_info(symbol, market_type)
            return symbol_info.get('status') == 'TRADING'
        except:
            return False
    
    @staticmethod
    def get_popular_symbols(market_type: str = "spot", limit: int = 50) -> List[str]:
        """獲取熱門交易對列表"""
        try:
            url = BinanceAPI.get_ticker_url(market_type)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 按24小時成交量排序
            sorted_data = sorted(data, key=lambda x: float(x.get('volume', 0)), reverse=True)
            
            # 提取交易對名稱
            symbols = [item['symbol'] for item in sorted_data[:limit]]
            return symbols
        except Exception as e:
            print(f"獲取熱門交易對失敗: {e}")
            return []
