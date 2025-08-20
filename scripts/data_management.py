# -*- coding: utf-8 -*-
"""
資料管理工具
用於檢查、清理和恢復 Binance 分析資料
"""

import os
import glob
import time
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

# 添加專案路徑
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_timeframe_analyzer import analyze_symbol


class DataManager:
    """資料管理工具類"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.required_files = [
            "ethusdt_spot_1m.csv",
            "btcusdt_spot_1m.csv", 
            "ethusdt_futures_1m.csv",
            "btcusdt_futures_1m.csv"
        ]
    
    def check_data_integrity(self) -> Dict[str, bool]:
        """檢查資料完整性"""
        print("=== 檢查資料完整性 ===")
        
        results = {}
        missing_files = []
        
        for file in self.required_files:
            file_path = os.path.join(self.data_dir, file)
            exists = os.path.exists(file_path)
            results[file] = exists
            
            if exists:
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                print(f"✅ {file} - {file_size:.1f} MB")
            else:
                missing_files.append(file)
                print(f"❌ {file} - 缺失")
        
        # 檢查分析報告檔案
        report_files = glob.glob(os.path.join(self.data_dir, "*_timeframe_report_*.md"))
        print(f"\n📊 分析報告檔案: {len(report_files)} 個")
        
        if missing_files:
            print(f"\n⚠️  缺少 {len(missing_files)} 個檔案:")
            for file in missing_files:
                print(f"  - {file}")
            print("\n💡 建議執行資料恢復")
        else:
            print("\n✅ 所有資料檔案完整")
        
        return results
    
    def get_file_info(self) -> Dict[str, Dict]:
        """獲取檔案詳細資訊"""
        print("=== 檔案詳細資訊 ===")
        
        file_info = {}
        
        # 原始資料檔案
        raw_files = glob.glob(os.path.join(self.data_dir, "*_1m.csv"))
        total_size = 0
        
        for file in raw_files:
            filename = os.path.basename(file)
            size_mb = os.path.getsize(file) / (1024 * 1024)
            modified_time = datetime.fromtimestamp(os.path.getmtime(file))
            
            file_info[filename] = {
                "size_mb": size_mb,
                "modified": modified_time,
                "type": "raw_data"
            }
            
            total_size += size_mb
            print(f"📁 {filename}")
            print(f"   大小: {size_mb:.1f} MB")
            print(f"   修改時間: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 分析報告檔案
        report_files = glob.glob(os.path.join(self.data_dir, "*_timeframe_report_*"))
        report_size = 0
        
        for file in report_files:
            filename = os.path.basename(file)
            size_kb = os.path.getsize(file) / 1024
            modified_time = datetime.fromtimestamp(os.path.getmtime(file))
            
            file_info[filename] = {
                "size_kb": size_kb,
                "modified": modified_time,
                "type": "report"
            }
            
            report_size += size_kb
        
        print(f"\n📊 統計資訊:")
        print(f"   原始資料檔案: {len(raw_files)} 個, 總大小: {total_size:.1f} MB")
        print(f"   分析報告檔案: {len(report_files)} 個, 總大小: {report_size:.1f} KB")
        
        return file_info
    
    def cleanup_old_data(self, days_to_keep: int = 30, dry_run: bool = True) -> List[str]:
        """清理舊資料"""
        print(f"=== 清理舊資料 (保留 {days_to_keep} 天) ===")
        
        if dry_run:
            print("🔍 乾跑模式 - 不會實際刪除檔案")
        
        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 24 * 3600)
        
        files_to_delete = []
        
        # 檢查原始資料檔案
        raw_files = glob.glob(os.path.join(self.data_dir, "*_1m.csv"))
        
        for file in raw_files:
            file_time = os.path.getmtime(file)
            if file_time < cutoff_time:
                files_to_delete.append(file)
                file_age = (current_time - file_time) / (24 * 3600)
                print(f"🗑️  標記刪除: {os.path.basename(file)} (已存在 {file_age:.1f} 天)")
        
        if not files_to_delete:
            print("✅ 沒有需要清理的舊檔案")
            return []
        
        if not dry_run:
            print(f"\n⚠️  即將刪除 {len(files_to_delete)} 個檔案...")
            confirm = input("確認刪除? (y/N): ")
            
            if confirm.lower() == 'y':
                for file in files_to_delete:
                    os.remove(file)
                    print(f"✅ 已刪除: {os.path.basename(file)}")
            else:
                print("❌ 取消刪除")
                return []
        
        return files_to_delete
    
    def backup_reports(self, backup_dir: str = "data/backup") -> str:
        """備份分析報告"""
        print("=== 備份分析報告 ===")
        
        # 創建備份目錄
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"reports_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)
        
        # 複製報告檔案
        report_files = glob.glob(os.path.join(self.data_dir, "*_timeframe_report_*"))
        
        for file in report_files:
            filename = os.path.basename(file)
            dest_file = os.path.join(backup_path, filename)
            shutil.copy2(file, dest_file)
            print(f"📋 備份: {filename}")
        
        print(f"✅ 報告已備份到: {backup_path}")
        return backup_path
    
    def restore_data(self, symbols: List[str] = None, market_types: List[str] = None) -> bool:
        """恢復資料"""
        print("=== 恢復資料 ===")
        
        if symbols is None:
            symbols = ["ETHUSDT", "BTCUSDT"]
        
        if market_types is None:
            market_types = ["spot", "futures"]
        
        success_count = 0
        total_count = len(symbols) * len(market_types)
        
        for symbol in symbols:
            for market_type in market_types:
                try:
                    print(f"📥 下載 {symbol} {market_type} 資料...")
                    analyze_symbol(symbol, market_type, 1095)  # 3年資料
                    success_count += 1
                    print(f"✅ {symbol} {market_type} 下載完成")
                except Exception as e:
                    print(f"❌ {symbol} {market_type} 下載失敗: {e}")
        
        print(f"\n📊 恢復結果: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    def create_data_sample(self, symbol: str, market_type: str, days: int = 7) -> str:
        """創建資料樣本"""
        print(f"=== 創建 {symbol} {market_type} 資料樣本 ===")
        
        source_file = os.path.join(self.data_dir, f"{symbol.lower()}_{market_type}_1m.csv")
        sample_dir = os.path.join(self.data_dir, "samples")
        os.makedirs(sample_dir, exist_ok=True)
        
        sample_file = os.path.join(sample_dir, f"{symbol.lower()}_{market_type}_sample.csv")
        
        if not os.path.exists(source_file):
            print(f"❌ 原始檔案不存在: {source_file}")
            return None
        
        try:
            df = pd.read_csv(source_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 取最近N天的資料
            end_date = df['timestamp'].max()
            start_date = end_date - timedelta(days=days)
            
            sample_df = df[df['timestamp'] >= start_date]
            sample_df.to_csv(sample_file, index=False)
            
            sample_size = len(sample_df)
            print(f"✅ 已創建樣本檔案: {sample_file}")
            print(f"   包含 {sample_size} 根K線 ({days} 天資料)")
            
            return sample_file
            
        except Exception as e:
            print(f"❌ 創建樣本失敗: {e}")
            return None


def main():
    """主函數"""
    manager = DataManager()
    
    print("🔧 Binance 資料管理工具")
    print("=" * 50)
    
    while True:
        print("\n請選擇操作:")
        print("1. 檢查資料完整性")
        print("2. 查看檔案詳細資訊")
        print("3. 清理舊資料 (乾跑)")
        print("4. 清理舊資料 (實際執行)")
        print("5. 備份分析報告")
        print("6. 恢復所有資料")
        print("7. 創建資料樣本")
        print("0. 退出")
        
        choice = input("\n請輸入選項 (0-7): ").strip()
        
        if choice == "1":
            manager.check_data_integrity()
        
        elif choice == "2":
            manager.get_file_info()
        
        elif choice == "3":
            days = input("保留天數 (預設30): ").strip()
            days = int(days) if days.isdigit() else 30
            manager.cleanup_old_data(days, dry_run=True)
        
        elif choice == "4":
            days = input("保留天數 (預設30): ").strip()
            days = int(days) if days.isdigit() else 30
            manager.cleanup_old_data(days, dry_run=False)
        
        elif choice == "5":
            manager.backup_reports()
        
        elif choice == "6":
            confirm = input("確認恢復所有資料? 這可能需要很長時間 (y/N): ")
            if confirm.lower() == 'y':
                manager.restore_data()
        
        elif choice == "7":
            symbol = input("交易對 (預設 ETHUSDT): ").strip() or "ETHUSDT"
            market_type = input("市場類型 (spot/futures, 預設 spot): ").strip() or "spot"
            days = input("樣本天數 (預設7): ").strip()
            days = int(days) if days.isdigit() else 7
            manager.create_data_sample(symbol, market_type, days)
        
        elif choice == "0":
            print("👋 再見!")
            break
        
        else:
            print("❌ 無效選項，請重新選擇")


if __name__ == "__main__":
    main()
