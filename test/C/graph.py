#!/usr/bin/env python3
"""
C1 Test Results Visualization Script - Analysis of Sending Speed vs File Size Relationship
Generate charts showing the relationship between sending speed and file size based on three JSON files
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def load_json_results(file_path):
    """Load JSON result file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load file {file_path}: {e}")
        return None

def extract_speed_size_data(result_data):
    """Extract file size and speed data from result data"""
    if not result_data or 'test_cases' not in result_data:
        return None
    
    file_sizes = []
    speeds_mbps = []
    
    for case in result_data['test_cases']:
        if case.get('upload_success', False):
            file_sizes.append(case['file_size'])
            speeds_mbps.append(case['speed_mbps'])
    
    return {
        'file_sizes': file_sizes,
        'speeds_mbps': speeds_mbps,
        'performance_analysis': result_data.get('performance_analysis', {})
    }

def format_file_size(size_bytes):
    """Format file size display"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def create_speed_vs_size_plots():
    """Create sending speed vs file size relationship charts"""
    
    # Load three result files
    result_files = [
        'result_0.json',
        'result_1.json',
        'result_2.json'
    ]
    
    results = []
    for file_path in result_files:
        data = load_json_results(file_path)
        if data:
            perf_data = extract_speed_size_data(data)
            if perf_data:
                results.append(perf_data)
    
    if not results:
        print("Cannot load valid test result data")
        return
    
    # Create charts
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('C Test - Analysis of Sending Speed vs File Size Relationship', fontsize=18, fontweight='bold')
    
    # # Set system font and style to fix negative sign issue
    # plt.rcParams['font.family'] = ['sans-serif']
    # plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans', 'Bitstream Vera Sans', 'sans-serif']
    # plt.rcParams['axes.unicode_minus'] = False
    # plt.rcParams['font.size'] = 12
    
    # Chart 1: Comparison of sending speed vs file size for three test groups
    ax1.set_title('Sending Speed vs File Size Relationship Comparison', fontsize=14, fontweight='bold')
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    labels = ['Test 1', 'Test 2', 'Test 3']
    markers = ['o', 's', '^']
    
    for i, (result, color, label, marker) in enumerate(zip(results, colors, labels, markers)):
        if result['file_sizes'] and result['speeds_mbps']:
            # Convert file sizes to MB
            file_sizes_mb = [size / (1024*1024) for size in result['file_sizes']]
            ax1.plot(file_sizes_mb, result['speeds_mbps'],
                    marker=marker, color=color, label=label, linewidth=2.5,
                    markersize=10, alpha=0.8)
    
    ax1.set_xlabel('File Size (MB)', fontsize=12)
    ax1.set_ylabel('Sending Speed (Mbps)', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    
    # Set x-axis ticks to file size labels
    x_ticks = [1, 10, 100, 1000]
    ax1.set_xticks(x_ticks)
    ax1.set_xticklabels([f'{x} MB' for x in x_ticks])
    
    # Chart 2: Average sending speed comparison for each test
    ax2.set_title('Average Sending Speed Comparison for Each Test', fontsize=14, fontweight='bold')
    test_names = ['Test 1', 'Test 2', 'Test 3']
    avg_speeds = []
    
    for result in results:
        perf_analysis = result.get('performance_analysis', {})
        avg_speed = perf_analysis.get('average_speed_mbps', 0)
        avg_speeds.append(avg_speed)
    
    bars = ax2.bar(test_names, avg_speeds, color=colors, alpha=0.7, width=0.6)
    ax2.set_ylabel('Average Sending Speed (Mbps)', fontsize=12)
    ax2.set_ylim(0, max(avg_speeds) * 1.2 if avg_speeds else 1)
    
    # Add value labels on bars
    for bar, speed in zip(bars, avg_speeds):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + max(avg_speeds) * 0.02,
                f'{speed:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Chart 3: Trend analysis of sending speed with file size changes
    ax3.set_title('Trend Analysis of Sending Speed with File Size Changes', fontsize=14, fontweight='bold')
    
    # Calculate average speed for each file size
    file_size_to_speeds = {}
    for result in results:
        for size, speed in zip(result['file_sizes'], result['speeds_mbps']):
            if size not in file_size_to_speeds:
                file_size_to_speeds[size] = []
            file_size_to_speeds[size].append(speed)
    
    # Calculate average speed and standard deviation
    avg_sizes = sorted(file_size_to_speeds.keys())
    avg_speeds_all = [np.mean(file_size_to_speeds[size]) for size in avg_sizes]
    std_speeds = [np.std(file_size_to_speeds[size]) for size in avg_sizes]
    
    # Plot average speed curve with error bars
    sizes_mb = [size / (1024*1024) for size in avg_sizes]
    ax3.errorbar(sizes_mb, avg_speeds_all, yerr=std_speeds,
                fmt='o-', color='red', linewidth=2.5, markersize=8,
                capsize=5, capthick=2, label='Average Speed ± Standard Deviation')
    
    ax3.set_xlabel('File Size (MB)', fontsize=12)
    ax3.set_ylabel('Average Sending Speed (Mbps)', fontsize=12)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3, linestyle='--')
    ax3.set_xscale('log')
    ax3.set_yscale('log')
    
    # Set x-axis ticks
    ax3.set_xticks([1, 10, 100, 1000])
    ax3.set_xticklabels([f'{x} MB' for x in x_ticks])
    
    # Chart 4: Performance statistics summary table
    ax4.axis('off')
    ax4.set_title('Performance Statistics Summary', fontsize=14, fontweight='bold')
    
    # Create statistics table
    table_data = []
    headers = ['Test', 'Avg Speed\n(Mbps)', 'Max Speed\n(Mbps)', 'Min Speed\n(Mbps)', 'Success Rate\n(%)', 'Std Dev\n(Mbps)']
    
    for i, (result, label) in enumerate(zip(results, labels)):
        perf_analysis = result.get('performance_analysis', {})
        total_files = perf_analysis.get('total_files_tested', 0)
        successful = perf_analysis.get('successful_uploads', 0)
        success_rate = (successful / total_files * 100) if total_files > 0 else 0
        
        table_data.append([
            label,
            f"{perf_analysis.get('average_speed_mbps', 0):.2f}",
            f"{perf_analysis.get('max_speed_mbps', 0):.2f}",
            f"{perf_analysis.get('min_speed_mbps', 0):.2f}",
            f"{success_rate:.1f}",
            f"{perf_analysis.get('speed_std_dev', 0):.2f}"
        ])
    
    # Add overall statistics row
    all_avg_speeds = [r.get('performance_analysis', {}).get('average_speed_mbps', 0) for r in results]
    all_max_speeds = [r.get('performance_analysis', {}).get('max_speed_mbps', 0) for r in results]
    all_min_speeds = [r.get('performance_analysis', {}).get('min_speed_mbps', 0) for r in results]
    all_std_devs = [r.get('performance_analysis', {}).get('speed_std_dev', 0) for r in results]
    
    table_data.append([
        'Overall Average',
        f"{np.mean(all_avg_speeds):.2f}",
        f"{max(all_max_speeds):.2f}",
        f"{min(all_min_speeds):.2f}",
        f"{np.mean([r['performance_analysis'].get('successful_uploads', 0)/r['performance_analysis'].get('total_files_tested', 1)*100 for r in results]):.1f}",
        f"{np.mean(all_std_devs):.2f}"
    ])
    
    # Create table
    table = ax4.table(cellText=table_data, colLabels=headers,
                     cellLoc='center', loc='center', colColours=['lightgray']*len(headers))
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)
    
    # Set table style
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart
    output_path = 'Sending_Speed_vs_File_Size_Analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    
    # Display chart
    plt.show()
    
    return output_path

if __name__ == "__main__":
    print("Starting to generate sending speed vs file size relationship analysis chart...")
    plot_path = create_speed_vs_size_plots()
    if plot_path:
        print(f"Chart generation completed: {plot_path}")
    else:
        print("Chart generation failed")