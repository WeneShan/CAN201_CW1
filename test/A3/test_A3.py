#!/usr/bin/env python3
"""
A3 - 尾部块处理（非整数倍块大小）
验证文件大小不是块大小的整数倍时，尾部块的正确处理
专为VirtualBox Ubuntu虚拟机环境设计
假设服务器已经在另一个虚拟机中运行
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径到系统路径
project_path = Path("/home/stepuser/TCPclient/")
sys.path.insert(0, str(project_path))

from test.vm_test_utils import VMTestConfig, VMTestLogger, VMFileManager, VMNetworkTester, save_vm_test_results, verify_file_integrity_vm

def main():
    print("=== A3 测试：尾部块处理（非整数倍块大小） ===")

    # 初始化测试
    test_name = "A3"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '尾部块处理测试（非整数倍块大小）',
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

        # 创建测试文件 - 1KB + 1字节，确保不是块大小的整数倍
        # 块大小通常为20480字节，我们创建20481字节的文件
        tail_block_size = 20481  # 20480 + 1
        logger.info(f"创建 {tail_block_size} 字节测试文件（非整数倍块大小）...")
        test_file = VMFileManager.create_test_file(
            tail_block_size, 
            "test_tail_block.bin"
        )

        if not test_file.exists():
            logger.error("测试文件创建失败")
            results['status'] = 'FAILED'
            results['error'] = '测试文件创建失败'
            save_vm_test_results(test_name, results)
            return False

        # 计算本地文件MD5
        local_md5 = VMFileManager.calculate_md5(test_file)
        logger.info(f"本地文件MD5: {local_md5}")

        # 运行上传测试
        logger.info("开始文件上传...")
        test_result = VMNetworkTester.run_client_upload(str(test_file))

        if not test_result['success']:
            logger.error("上传测试执行失败")
            results['status'] = 'FAILED'
            results['error'] = '上传测试执行失败'
            save_vm_test_results(test_name, results)
            return False

        # 验证文件完整性
        logger.info("验证文件完整性...")
        is_valid, server_md5_calc, client_md5_calc = verify_file_integrity_vm(local_md5, test_result['stdout'])

        # 记录测试用例结果
        test_case = {
            'name': 'A3_Tail_Block_Upload',
            'file_size': test_file.stat().st_size,
            'expected_size': tail_block_size,
            'duration': test_result['duration'],
            'local_md5': local_md5,
            'server_md5': server_md5_calc,
            'client_md5': client_md5_calc,
            'file_integrity': is_valid,
            'upload_success': test_result['success'],
            'return_code': test_result['return_code'],
            'stdout_excerpt': test_result['stdout'][-500:] if len(test_result['stdout']) > 500 else test_result['stdout']
        }

        results['test_cases'].append(test_case)

        # 判断测试结果
        if (test_result['success'] and is_valid and 
            local_md5 == server_md5_calc == client_md5_calc and
            test_file.stat().st_size == tail_block_size):
            logger.info("✅ A3 测试通过：尾部块处理正确，MD5校验一致")
            results['status'] = 'PASSED'
            results['final_result'] = '尾部块处理正确，MD5校验一致'
        else:
            logger.error("❌ A3 测试失败")
            results['status'] = 'FAILED'
            results['final_result'] = '尾部块处理失败或MD5校验失败'

            if not test_result['success']:
                logger.error(f"上传失败，返回码: {test_result['return_code']}")
                logger.error(f"错误输出: {test_result['stderr']}")
            if not is_valid:
                logger.error("文件完整性验证失败")
            if test_file.stat().st_size != tail_block_size:
                logger.error(f"文件大小不匹配: 期望 {tail_block_size}, 实际 {test_file.stat().st_size}")

    except Exception as e:
        logger.error(f"A3测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)

    finally:
        # 清理测试文件
        if 'test_file' in locals() and test_file.exists():
            try:
                test_file.unlink()
                logger.info("清理测试文件完成")
            except:
                pass

        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_vm_test_results(test_name, results)

        print(f"=== A3 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)