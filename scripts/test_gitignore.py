# -*- coding: utf-8 -*-
"""
測試 .gitignore 設定
驗證哪些檔案會被 Git 追蹤，哪些會被忽略
"""

import os
import subprocess
from pathlib import Path


def test_gitignore():
    """測試 .gitignore 設定"""
    print("🔍 測試 .gitignore 設定")
    print("=" * 50)
    
    # 檢查大型原始資料檔案是否被忽略
    large_files = [
        "data/ethusdt_spot_1m.csv",
        "data/btcusdt_spot_1m.csv", 
        "data/ethusdt_futures_1m.csv",
        "data/btcusdt_futures_1m.csv"
    ]
    
    print("📁 檢查大型原始資料檔案:")
    for file in large_files:
        if os.path.exists(file):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print(f"  {file} - {size_mb:.1f} MB")
        else:
            print(f"  {file} - 不存在")
    
    # 檢查分析報告檔案是否會被追蹤
    report_files = [
        "data/ethusdt_spot_timeframe_report_20220820-20250819.md",
        "data/btcusdt_spot_timeframe_report_20220820-20250819.txt",
        "data/ethusdt_futures_timeframe_report_20220820-20250819.csv"
    ]
    
    print("\n📊 檢查分析報告檔案:")
    for file in report_files:
        if os.path.exists(file):
            size_kb = os.path.getsize(file) / 1024
            print(f"  {file} - {size_kb:.1f} KB")
        else:
            print(f"  {file} - 不存在")
    
    # 使用 git check-ignore 測試
    print("\n🔍 使用 git check-ignore 測試:")
    
    test_files = [
        "data/ethusdt_spot_1m.csv",  # 應該被忽略
        "data/btcusdt_futures_1m.csv",  # 應該被忽略
        "data/ethusdt_spot_timeframe_report_20220820-20250819.md",  # 不應該被忽略
        "data/btcusdt_spot_timeframe_report_20220820-20250819.txt",  # 不應該被忽略
        "data/ethusdt_futures_timeframe_report_20220820-20250819.csv"  # 不應該被忽略
    ]
    
    for file in test_files:
        try:
            result = subprocess.run(
                ["git", "check-ignore", file], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ❌ {file} - 被忽略")
            else:
                print(f"  ✅ {file} - 不被忽略")
                
        except FileNotFoundError:
            print(f"  ⚠️  {file} - Git 命令不可用")
    
    print("\n📋 總結:")
    print("✅ 大型原始資料檔案 (*_1m.csv) 應該被忽略")
    print("✅ 分析報告檔案 (*_timeframe_report_*) 應該被追蹤")
    print("✅ 資料目錄 README 應該被追蹤")


def check_file_sizes():
    """檢查檔案大小分布"""
    print("\n📊 檔案大小分布:")
    print("=" * 30)
    
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ data 目錄不存在")
        return
    
    # 分類檔案
    raw_files = []
    report_files = []
    other_files = []
    
    for file in data_dir.rglob("*"):
        if file.is_file():
            size_mb = file.stat().st_size / (1024 * 1024)
            
            if "_1m.csv" in file.name:
                raw_files.append((file.name, size_mb))
            elif "timeframe_report" in file.name:
                report_files.append((file.name, size_mb))
            else:
                other_files.append((file.name, size_mb))
    
    # 顯示結果
    print("📁 原始資料檔案:")
    total_raw_size = 0
    for name, size in raw_files:
        print(f"  {name} - {size:.1f} MB")
        total_raw_size += size
    print(f"  總計: {total_raw_size:.1f} MB")
    
    print("\n📊 分析報告檔案:")
    total_report_size = 0
    for name, size in report_files:
        size_kb = size * 1024
        print(f"  {name} - {size_kb:.1f} KB")
        total_report_size += size
    print(f"  總計: {total_report_size:.1f} MB")
    
    print("\n📄 其他檔案:")
    for name, size in other_files:
        if size > 1:
            print(f"  {name} - {size:.1f} MB")
        else:
            size_kb = size * 1024
            print(f"  {name} - {size_kb:.1f} KB")


if __name__ == "__main__":
    test_gitignore()
    check_file_sizes()
