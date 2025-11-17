#!/usr/bin/env python3
"""
A2 - 0 字节 / 1 字节 文件上传（极小文件）
验证极小文件的处理（0B 应失败/1B 应成功）
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
    print("=== A2 测试：0字节应失败/1字节应成功 ===")
    
    # 初始化测试
    test_name = "A2"
    logger = VMTestLogger(test_name)
    # client_tester = VMClientTester(test_name)
    results = {
        'test_name': test_name,
        'test_description': '极小文件上传测试（0字节应失败/1字节应成功）',
        'start_time': datetime.now().isoformat(),
        'test_cases': []
    }
    
    try:

        # 测试案例
        test_cases = [
            {'file': 'empty_file.bin', 'type': '0字节', 'size': 0, 'expected_success': False},
            {'file': 'one_byte_file.bin', 'type': '1字节', 'size': 1, 'expected_success': True}
        ]
        
        for case in test_cases:
            logger.info(f"测试 {case['type']} 文件: {case['file']}")
            
            # 创建测试文件
            if case['size'] == 0:
                test_file = VMFileManager.create_empty_file(case['file'])
            else:  # 1字节
                test_file = VMFileManager.create_1byte_file(case['file'])
            
            if not test_file.exists():
                logger.error(f"测试文件创建失败: {case['file']}")
                continue
            
            # 计算本地文件MD5
            local_md5 = VMFileManager.calculate_md5(test_file)
            logger.info(f"本地文件MD5: {local_md5}")
            
            # 运行上传测试
            logger.info(f"开始上传 {case['type']} 文件...")
            test_result = VMNetworkTester.run_client_upload(str(test_file))
            
            if not test_result:
                logger.error(f"上传测试执行失败: {case['file']}")
                test_case = {
                    'name': f'A2_{case["type"]}_Upload',
                    'file_size': test_file.stat().st_size,
                    'upload_success': False,
                    'upload_error': '测试执行失败'
                }
                results['test_cases'].append(test_case)
                continue
            
            # 验证文件完整性
            logger.info(f"验证 {case['type']} 文件完整性...")
            is_valid, client_md5, server_md5 = verify_file_integrity_vm(local_md5, test_result['stdout'])
            
            # 记录测试用例结果
            test_case = {
                'name': f'A2_{case["type"]}_Upload',
                'file_type': case['type'],
                'file_size': test_file.stat().st_size,
                'duration': test_result['duration'],
                'local_md5': local_md5,
                'server_md5': server_md5,
                'file_integrity': is_valid,
                'upload_success': test_result['success'],
                'return_code': test_result['return_code'],
                'stdout_excerpt': test_result['stdout'][-300:] if len(test_result['stdout']) > 300 else test_result['stdout'],
                'expected_success': case['expected_success']
            }
            
            results['test_cases'].append(test_case)
            
            # 清理测试文件
            try:
                test_file.unlink()
            except:
                pass
        
        # 分析结果
        all_passed = True
        for test_case in results['test_cases']:
            expected_success = test_case.get('expected_success', True)
            actual_success = test_case['upload_success'] and test_case.get('file_integrity', False)
            
            if actual_success == expected_success:
                logger.info(f"✅ {test_case['name']} 通过")
            else:
                logger.error(f"❌ {test_case['name']} 失败")
                all_passed = False
        
        if all_passed and len(results['test_cases']) > 0:
            results['status'] = 'PASSED'
            results['final_result'] = '极小文件上传测试结果符合预期'
        else:
            results['status'] = 'FAILED' 
            results['final_result'] = '存在不符合预期的测试结果'
            
    except Exception as e:
        logger.error(f"A2测试异常: {e}")
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
    finally:

        
        # 记录结束时间
        results['end_time'] = datetime.now().isoformat()
        save_vm_test_results(test_name, results)
        
        print(f"=== A2 测试完成，结果: {results['status']} ===")
        return results['status'] == 'PASSED'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)