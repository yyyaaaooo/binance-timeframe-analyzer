#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
互動式資料管理工具
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from timeframe_selector_ethusdt import (
    Config, check_existing_data, check_data_quality, 
    smart_data_loader, generate_data_report, save_data_to_csv
)

def print_menu():
    """顯示選單"""
    print("\n" + "="*50)
    print("ETHUSDT 資料管理工具")
    print("="*50)
    print("1. 檢查現有資料狀態")
    print("2. 檢查資料品質")
    print("3. 智能資料載入（推薦）")
    print("4. 強制重新下載")
    print("5. 增量更新資料")
    print("6. 產生詳細資料報告")
    print("7. 修改配置設定")
    print("0. 退出")
    print("="*50)

def check_data_status(cfg: Config):
    """檢查資料狀態"""
    print("\n=== 檢查資料狀態 ===")
    data_exists, df, status = check_existing_data(cfg)
    
    if data_exists:
        print(f"✅ 資料存在")
        print(f"檔案路徑: {cfg.csv_path}")
        print(f"總K線數: {status['total_bars']:,}")
        print(f"時間範圍: {status['start_time']} 到 {status['end_time']}")
        print(f"資料完整度: {status['data_completeness']:.2%}")
        print(f"重複資料: {status['duplicate_bars']} 個")
        print(f"缺失值: {status['null_values']} 個")
    else:
        print(f"❌ 資料不存在或無法讀取")
        print(f"狀態: {status['status']}")

def check_quality(cfg: Config):
    """檢查資料品質"""
    print("\n=== 檢查資料品質 ===")
    data_exists, df, status = check_existing_data(cfg)
    
    if not data_exists:
        print("❌ 沒有資料可以檢查")
        return
    
    quality_report = check_data_quality(df, cfg)
    print(f"品質分數: {quality_report['quality_score']:.2f}")
    
    if quality_report['issues']:
        print("\n發現的問題:")
        for issue in quality_report['issues']:
            print(f"  ❌ {issue}")
    else:
        print("\n✅ 資料品質良好，未發現問題")

def smart_load(cfg: Config):
    """智能載入資料"""
    print("\n=== 智能資料載入 ===")
    try:
        df = smart_data_loader(cfg)
        if cfg.save_csv:
            save_data_to_csv(df, cfg.csv_path)
        print("✅ 資料載入完成")
    except Exception as e:
        print(f"❌ 資料載入失敗: {e}")

def force_redownload(cfg: Config):
    """強制重新下載"""
    print("\n=== 強制重新下載 ===")
    confirm = input("確定要重新下載所有資料嗎？這將覆蓋現有資料 (y/N): ")
    if confirm.lower() == 'y':
        cfg.force_redownload = True
        try:
            df = smart_data_loader(cfg)
            if cfg.save_csv:
                save_data_to_csv(df, cfg.csv_path)
            print("✅ 重新下載完成")
        except Exception as e:
            print(f"❌ 重新下載失敗: {e}")
        finally:
            cfg.force_redownload = False
    else:
        print("取消重新下載")

def incremental_update(cfg: Config):
    """增量更新"""
    print("\n=== 增量更新 ===")
    data_exists, df, status = check_existing_data(cfg)
    
    if not data_exists:
        print("❌ 沒有現有資料，無法進行增量更新")
        return
    
    if status['data_completeness'] >= 0.95:
        print("✅ 資料已完整，無需更新")
        return
    
    print(f"當前資料完整度: {status['data_completeness']:.2%}")
    confirm = input("確定要進行增量更新嗎？ (y/N): ")
    if confirm.lower() == 'y':
        cfg.incremental_update = True
        try:
            df = smart_data_loader(cfg)
            if cfg.save_csv:
                save_data_to_csv(df, cfg.csv_path)
            print("✅ 增量更新完成")
        except Exception as e:
            print(f"❌ 增量更新失敗: {e}")
    else:
        print("取消增量更新")

def generate_report(cfg: Config):
    """產生詳細報告"""
    print("\n=== 產生詳細報告 ===")
    data_exists, df, status = check_existing_data(cfg)
    
    if not data_exists:
        print("❌ 沒有資料可以產生報告")
        return
    
    report = generate_data_report(df, cfg)
    print(report)
    
    # 儲存報告到檔案
    report_file = cfg.csv_path.replace('.csv', '_report.txt')
    # 確保目錄存在
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n報告已儲存至: {report_file}")
    except Exception as e:
        print(f"儲存報告失敗: {e}")

def modify_config(cfg: Config):
    """修改配置"""
    print("\n=== 修改配置 ===")
    print("當前配置:")
    print(f"  交易對: {cfg.symbol}")
    print(f"  資料天數: {cfg.data_days}")
    print(f"  自動抓取: {cfg.auto_fetch}")
    print(f"  儲存CSV: {cfg.save_csv}")
    print(f"  強制重新下載: {cfg.force_redownload}")
    print(f"  增量更新: {cfg.incremental_update}")
    print(f"  資料品質檢查: {cfg.data_quality_check}")
    print(f"  最低品質分數: {cfg.min_data_quality_score}")
    
    print("\n可修改的選項:")
    print("1. 修改資料天數")
    print("2. 修改最低品質分數")
    print("3. 切換自動抓取")
    print("4. 切換資料品質檢查")
    print("0. 返回主選單")
    
    choice = input("\n請選擇 (0-4): ")
    
    if choice == '1':
        try:
            days = int(input(f"請輸入新的資料天數 (當前: {cfg.data_days}): "))
            if days > 0:
                cfg.data_days = days
                print(f"✅ 資料天數已修改為 {days}")
            else:
                print("❌ 天數必須大於0")
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    elif choice == '2':
        try:
            score = float(input(f"請輸入新的最低品質分數 (當前: {cfg.min_data_quality_score}): "))
            if 0 <= score <= 1:
                cfg.min_data_quality_score = score
                print(f"✅ 最低品質分數已修改為 {score}")
            else:
                print("❌ 分數必須在0-1之間")
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    elif choice == '3':
        cfg.auto_fetch = not cfg.auto_fetch
        print(f"✅ 自動抓取已{'啟用' if cfg.auto_fetch else '停用'}")
    
    elif choice == '4':
        cfg.data_quality_check = not cfg.data_quality_check
        print(f"✅ 資料品質檢查已{'啟用' if cfg.data_quality_check else '停用'}")
    
    elif choice == '0':
        return
    
    else:
        print("❌ 無效的選擇")

def main():
    """主函數"""
    cfg = Config()
    
    while True:
        print_menu()
        choice = input("請選擇 (0-7): ")
        
        if choice == '1':
            check_data_status(cfg)
        elif choice == '2':
            check_quality(cfg)
        elif choice == '3':
            smart_load(cfg)
        elif choice == '4':
            force_redownload(cfg)
        elif choice == '5':
            incremental_update(cfg)
        elif choice == '6':
            generate_report(cfg)
        elif choice == '7':
            modify_config(cfg)
        elif choice == '0':
            print("再見！")
            break
        else:
            print("❌ 無效的選擇，請重新輸入")
        
        input("\n按 Enter 繼續...")

if __name__ == "__main__":
    main()
