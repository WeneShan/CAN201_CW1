#!/usr/bin/env python3
"""
C1 - 文件大小性能测试（不同大小文件）
测试不同大小文件的上传性能，分析传输效率
专为VirtualBox Ubuntu虚拟机环境设计
假设服务器已经在另一个虚拟机中运行
"""

import sys
import os
import time
import json
import statistics
from pathlib import Path
from datetime import datetime

# 添加项目路径到系统路径
project_path = Path("/home/stepuser/TCPclient/")
sys.path.insert(0, str(project_path))

from test.vm_test_utils import VMTestConfig, VMTestLogger, VMFileManager, VMNetworkTester, save_vm_test_results

def main():
    print("=== C1 测试：文件大小性能测试（不同大小文件） ===")

    # 初始化测试
    test_name = "C1"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '文件大小性能测试（不同大小文件）',
        'start_time': datetime.now().isoformat(),
        'test_cases': []
    }

    try:
        # 检查服务器连接性
        logger.info("检查服务器连接性...")
        if not VMNetworkTester.check_server_connectivity():
            logger.error("服务器连接失败，请确保服务器虚拟机正在运行")
            results['status'] = 'FAILED'
            results['error'] = '服务器连接失败'
            save_vm_test_results(test_name, results)
            return False
            
        logger.info("服务器连接正常")

        # 测试不同大小的文件
        file_sizes = [
            (VMTestConfig.TEST_FILE_SIZE_1KB, "test_1kb.bin"),
            (VMTestConfig.TEST_FILE_SIZE_100KB, "test_100kb.bin"),
            (VMTestConfig.TEST_FILE_SIZE_1MB, "test_1mb.bin"),
            (VMTestConfig.TEST_FILE_SIZE_10MB, "test_10mb.bin"),
            (VMTestConfig.TEST_FILE_SIZE_50MB, "test_50mb.bin")
        ]

        for size, filename in file_sizes:
            logger.info(f"测试文件大小: {size} 字节, 文件名: {filename}")

            # 创建测试文件
            test_file = VMFileManager.create_test_file(size, filename)

            if not test_file.exists():
                logger.error(f"测试文件创建失败: {filename}")
                continue

            # 计算本地文件MD5
            local_md5 = VMFileManager.calculate_md5(test_file)
            logger.info(f"本地文件MD5: {local_md5}")

            # 运行上传测试
            logger.info(f"开始文件上传: {filename}")
            test_result = VMNetworkTester.run_client_upload(str(test_file))

            if not test_result['success']:
                logger.error(f"上传测试执行失败: {filename}")
                test_case = {
                    'name': f'C1_Upload_{size}_bytes',
                    'file_size': size,
                    'upload_success': False,
                    'upload_error': '测试执行失败'
                }
                results['test_cases'].append(test_case)
                continue

            # 计算性能指标
            duration = test_result['duration']
            speed = size / duration if duration > 0 else 0  # 字节/秒
            speed_mbps = (speed * 8) / (1024 * 1024)  # Mbps

            # 记录测试用例结果
            test_case = {
                'name': f'C1_Upload_{size}_bytes',
                'file_size': size,
                'duration': duration,
                'speed_bytes_per_sec': speed,
                'speed_mbps': speed_mbps,
                'local_md5': local_md5,
                'upload_success': test_result['success'],
                'return_code': test_result['return_code']
            }

            results['test_cases'].append(test_case)
            logger.info(f"文件 {filename} 上传完成: {duration:.2f}s, {speed_mbps:.2f} Mbps")

            # 清理测试文件
            try:
                test_file.unlink()
            except:
                pass

        # 分析性能结果
        successful_cases = [case for case in results['test_cases'] if case['upload_success']]
        if successful_cases:
            speeds = [case['speed_mbps'] for case in successful_cases]
            avg_speed = statistics.mean(speeds)
            max_speed = max(speeds)
            min_speed = min(speeds)

            results['performance_analysis'] = {
                'total_files_tested': len(file_sizes),
                'successful_uploads': len(successful_cases),
                'average_speed_mbps': avg_speed,
                'max_speed_mbps': max_speed,
                'min_speed_mbps': min_speed,
                'speed_std_dev': statistics.stdev(speeds) if len(speeds) > 1 else 0
            }

            logger.info(f"性能分析: 平均速度 {avg_speed:.2f} Mbps, 最大 {max_speed:.2f} Mbps, 最小 {min_speed:.2f} Mbps")

        # 判断测试结果
        if len(successful_cases) >= 3:  # 至少3个文件上传成功
            logger.info("✅ C1 测试通过：多个文件大小上传成功，性能数据收集完成")
            results['status'] = 'PASSED'
            results['final_result'] = '多文件大小上传成功，性能数据可用'
        else:
            logger.error("❌ C1 测试失败：成功上传的文件数量不足")
            results['status'] = 'FAILED'
            results['final_result'] = '成功上传的文件数量不足'

    except Exception as e:
        logger.error(f"C1测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)

    finally:
        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_vm_test_results(test_name, results)

        print(f"=== C1 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)