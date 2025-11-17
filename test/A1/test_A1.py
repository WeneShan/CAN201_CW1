#!/usr/bin/env python3
"""
A1 - 基线：单客户端标准文件上传（基本功能）
验证STEP协议的基础流程：Token、申请上传、分块、完成、MD5校验
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
    print("=== A1 测试：基线单客户端标准文件上传 ===")
    
    # 初始化测试
    test_name = "A1"
    logger = VMTestLogger(test_name)
    results = {
        'test_name': test_name,
        'test_description': '基线：单客户端标准文件上传（基本功能）',
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
        
        # 创建10MB测试文件
        logger.info("创建10MB测试文件...")
        test_file = VMFileManager.create_test_file(
            VMTestConfig.TEST_FILE_SIZE_10MB, 
            "test_10mb.bin"
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
            'name': 'A1_Baseline_Upload',
            'file_size': test_file.stat().st_size,
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
            local_md5 == server_md5_calc == client_md5_calc):
            logger.info("✅ A1 测试通过：文件上传成功且MD5校验一致")
            results['status'] = 'PASSED'
            results['final_result'] = 'MD5校验一致，上传成功'
        else:
            logger.error("❌ A1 测试失败")
            results['status'] = 'FAILED'
            results['final_result'] = 'MD5校验失败或上传失败'
            
            if not test_result['success']:
                logger.error(f"上传失败，返回码: {test_result['return_code']}")
                logger.error(f"错误输出: {test_result['stderr']}")
            if not is_valid:
                logger.error("文件完整性验证失败")
        
    except Exception as e:
        logger.error(f"A1测试异常: {e}")
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
        
        print(f"=== A1 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)