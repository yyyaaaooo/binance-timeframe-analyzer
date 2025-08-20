# -*- coding: utf-8 -*-
"""
趨勢視覺化模組
實現各種圖表生成功能
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import warnings

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

warnings.filterwarnings("ignore")


class TrendVisualizer:
    """趨勢視覺化器"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        """
        初始化視覺化器
        
        Args:
            figsize: 圖表大小
        """
        self.figsize = figsize
        self.colors = {
            'trend': '#2E8B57',  # 深綠色
            'range': '#CD5C5C',  # 印度紅
            'unclear': '#D3D3D3',  # 淺灰色
            'long': '#228B22',  # 森林綠
            'short': '#DC143C'   # 深紅色
        }
    
    def create_24x7_heatmap(self, heatmap_data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """
        創建 24x7 熱力圖
        
        Args:
            heatmap_data: 熱力圖數據
            save_path: 儲存路徑（可選）
            
        Returns:
            matplotlib Figure 物件
        """
        try:
            fig, ax = plt.subplots(figsize=(16, 8))
            
            # 創建熱力圖
            sns.heatmap(
                heatmap_data,
                annot=True,
                fmt='.3f',
                cmap='RdYlGn',
                center=0.5,
                cbar_kws={'label': '趨勢比例'},
                ax=ax
            )
            
            # 設定標題和標籤
            ax.set_title('24x7 趨勢熱力圖 (星期 x 小時)', fontsize=16, fontweight='bold')
            ax.set_xlabel('小時 (0-23)', fontsize=12)
            ax.set_ylabel('星期', fontsize=12)
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"熱力圖已儲存至: {save_path}")
            
            return fig
            
        except Exception as e:
            print(f"熱力圖創建錯誤: {e}")
            return None
    
    def create_trend_score_boxplot(self, trend_data: pd.DataFrame, group_column: str = 'hour', 
                                 save_path: Optional[str] = None) -> plt.Figure:
        """
        創建趨勢分數箱形圖
        
        Args:
            trend_data: 趨勢數據
            group_column: 分組列名
            save_path: 儲存路徑（可選）
            
        Returns:
            matplotlib Figure 物件
        """
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # 創建箱形圖
            sns.boxplot(
                data=trend_data,
                x=group_column,
                y='trend_score',
                ax=ax,
                palette='Set3'
            )
            
            # 設定標題和標籤
            title_map = {
                'hour': '各小時趨勢分數分佈',
                'weekday': '各星期趨勢分數分佈',
                'month': '各月份趨勢分數分佈'
            }
            ax.set_title(title_map.get(group_column, f'各{group_column}趨勢分數分佈'), 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel(group_column, fontsize=12)
            ax.set_ylabel('趨勢分數', fontsize=12)
            
            # 旋轉 x 軸標籤
            plt.xticks(rotation=45)
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"箱形圖已儲存至: {save_path}")
            
            return fig
            
        except Exception as e:
            print(f"箱形圖創建錯誤: {e}")
            return None
    
    def create_trend_direction_rose_chart(self, direction_stats: Dict, save_path: Optional[str] = None) -> plt.Figure:
        """
        創建趨勢方向玫瑰圖
        
        Args:
            direction_stats: 趨勢方向統計
            save_path: 儲存路徑（可選）
            
        Returns:
            matplotlib Figure 物件
        """
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 整體趨勢方向
            labels = ['多頭趨勢', '空頭趨勢']
            sizes = [direction_stats['long_trends'], direction_stats['short_trends']]
            colors = [self.colors['long'], self.colors['short']]
            
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('整體趨勢方向分佈', fontsize=14, fontweight='bold')
            
            # 按小時的趨勢方向
            hours = list(range(24))
            long_proportions = []
            short_proportions = []
            
            for hour in hours:
                if hour in direction_stats['direction_by_hour']:
                    long_prop = direction_stats['direction_by_hour'][hour]['long_proportion']
                    short_prop = direction_stats['direction_by_hour'][hour]['short_proportion']
                else:
                    long_prop = short_prop = 0
                
                long_proportions.append(long_prop)
                short_proportions.append(short_prop)
            
            x = np.arange(len(hours))
            width = 0.35
            
            ax2.bar(x - width/2, long_proportions, width, label='多頭趨勢', color=self.colors['long'])
            ax2.bar(x + width/2, short_proportions, width, label='空頭趨勢', color=self.colors['short'])
            
            ax2.set_xlabel('小時')
            ax2.set_ylabel('比例')
            ax2.set_title('各小時趨勢方向分佈')
            ax2.set_xticks(x)
            ax2.set_xticklabels(hours)
            ax2.legend()
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"玫瑰圖已儲存至: {save_path}")
            
            return fig
            
        except Exception as e:
            print(f"玫瑰圖創建錯誤: {e}")
            return None
    
    def create_trend_proportion_bar_chart(self, aggregation_data: Dict, period_type: str = 'hour',
                                        save_path: Optional[str] = None) -> plt.Figure:
        """
        創建趨勢比例長條圖
        
        Args:
            aggregation_data: 彙總數據
            period_type: 時段類型
            save_path: 儲存路徑（可選）
            
        Returns:
            matplotlib Figure 物件
        """
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # 準備數據
            periods = list(aggregation_data.keys())
            trend_proportions = [aggregation_data[p]['trend_proportion'] for p in periods]
            range_proportions = [aggregation_data[p]['range_proportion'] for p in periods]
            unclear_proportions = [aggregation_data[p]['unclear_proportion'] for p in periods]
            
            x = np.arange(len(periods))
            width = 0.25
            
            # 創建堆疊長條圖
            ax.bar(x, trend_proportions, width, label='趨勢', color=self.colors['trend'])
            ax.bar(x, range_proportions, width, bottom=trend_proportions, 
                  label='盤整', color=self.colors['range'])
            ax.bar(x, unclear_proportions, width, 
                  bottom=[t + r for t, r in zip(trend_proportions, range_proportions)],
                  label='不明', color=self.colors['unclear'])
            
            # 設定標題和標籤
            title_map = {
                'hour': '各小時趨勢狀態分佈',
                'weekday': '各星期趨勢狀態分佈',
                'month': '各月份趨勢狀態分佈'
            }
            ax.set_title(title_map.get(period_type, f'各{period_type}趨勢狀態分佈'), 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel(period_type, fontsize=12)
            ax.set_ylabel('比例', fontsize=12)
            ax.set_xticks(x)
            ax.set_xticklabels(periods)
            ax.legend()
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"長條圖已儲存至: {save_path}")
            
            return fig
            
        except Exception as e:
            print(f"長條圖創建錯誤: {e}")
            return None
    
    def create_adx_r_squared_scatter(self, trend_data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """
        創建 ADX vs R² 散點圖
        
        Args:
            trend_data: 趨勢數據
            save_path: 儲存路徑（可選）
            
        Returns:
            matplotlib Figure 物件
        """
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # 按趨勢標籤分組
            trend_points = trend_data[trend_data['trend_label'] == 'trend']
            range_points = trend_data[trend_data['trend_label'] == 'range']
            unclear_points = trend_data[trend_data['trend_label'] == 'unclear']
            
            # 創建散點圖
            ax.scatter(trend_points['adx'], trend_points['r_squared'], 
                      c=self.colors['trend'], label='趨勢', alpha=0.7, s=30)
            ax.scatter(range_points['adx'], range_points['r_squared'], 
                      c=self.colors['range'], label='盤整', alpha=0.7, s=30)
            ax.scatter(unclear_points['adx'], unclear_points['r_squared'], 
                      c=self.colors['unclear'], label='不明', alpha=0.7, s=30)
            
            # 設定標題和標籤
            ax.set_title('ADX vs R² 散點圖', fontsize=14, fontweight='bold')
            ax.set_xlabel('ADX', fontsize=12)
            ax.set_ylabel('R²', fontsize=12)
            ax.legend()
            
            # 添加網格
            ax.grid(True, alpha=0.3)
            
            # 調整佈局
            plt.tight_layout()
            
            # 儲存圖片
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"散點圖已儲存至: {save_path}")
            
            return fig
            
        except Exception as e:
            print(f"散點圖創建錯誤: {e}")
            return None
    
    def create_comprehensive_dashboard(self, trend_data: pd.DataFrame, time_analysis: Dict,
                                     save_dir: Optional[str] = None) -> List[plt.Figure]:
        """
        創建綜合儀表板
        
        Args:
            trend_data: 趨勢數據
            time_analysis: 時段分析結果
            save_dir: 儲存目錄（可選）
            
        Returns:
            圖表列表
        """
        try:
            figures = []
            
            # 創建儲存目錄
            if save_dir:
                import os
                os.makedirs(save_dir, exist_ok=True)
            
            # 1. 24x7 熱力圖
            if 'heatmap_data' in time_analysis and not time_analysis['heatmap_data'].empty:
                heatmap_fig = self.create_24x7_heatmap(
                    time_analysis['heatmap_data'],
                    save_path=f"{save_dir}/heatmap.png" if save_dir else None
                )
                if heatmap_fig:
                    figures.append(heatmap_fig)
            
            # 2. 趨勢分數箱形圖（按小時）
            if 'hour_aggregation' in time_analysis:
                boxplot_fig = self.create_trend_score_boxplot(
                    time_analysis['processed_data'],
                    'hour',
                    save_path=f"{save_dir}/trend_score_boxplot.png" if save_dir else None
                )
                if boxplot_fig:
                    figures.append(boxplot_fig)
            
            # 3. 趨勢方向玫瑰圖
            if 'direction_stats' in time_analysis:
                rose_fig = self.create_trend_direction_rose_chart(
                    time_analysis['direction_stats'],
                    save_path=f"{save_dir}/trend_direction_rose.png" if save_dir else None
                )
                if rose_fig:
                    figures.append(rose_fig)
            
            # 4. 趨勢比例長條圖（按小時）
            if 'hour_aggregation' in time_analysis:
                bar_fig = self.create_trend_proportion_bar_chart(
                    time_analysis['hour_aggregation'],
                    'hour',
                    save_path=f"{save_dir}/trend_proportion_bar.png" if save_dir else None
                )
                if bar_fig:
                    figures.append(bar_fig)
            
            # 5. ADX vs R² 散點圖
            scatter_fig = self.create_adx_r_squared_scatter(
                trend_data,
                save_path=f"{save_dir}/adx_r_squared_scatter.png" if save_dir else None
            )
            if scatter_fig:
                figures.append(scatter_fig)
            
            return figures
            
        except Exception as e:
            print(f"綜合儀表板創建錯誤: {e}")
            return []
    
    def save_all_figures(self, figures: List[plt.Figure], save_dir: str, prefix: str = "trend_analysis"):
        """
        儲存所有圖表
        
        Args:
            figures: 圖表列表
            save_dir: 儲存目錄
            prefix: 檔案前綴
        """
        try:
            import os
            os.makedirs(save_dir, exist_ok=True)
            
            for i, fig in enumerate(figures):
                if fig is not None:
                    filename = f"{prefix}_{i+1}.png"
                    filepath = os.path.join(save_dir, filename)
                    fig.savefig(filepath, dpi=300, bbox_inches='tight')
                    print(f"圖表已儲存至: {filepath}")
            
        except Exception as e:
            print(f"圖表儲存錯誤: {e}")
