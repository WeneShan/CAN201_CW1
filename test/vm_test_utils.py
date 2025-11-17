#!/usr/bin/env python3
"""
STEP协议虚拟机测试工具模块
专为VirtualBox Ubuntu虚拟机环境设计
假设服务器已经在另一个虚拟机中运行，测试在客户端虚拟机中执行
"""

import os
import sys
import time
import json
import hashlib
import logging
import subprocess
import socket
from pathlib import Path
from datetime import datetime

class VMTestConfig:
    """虚拟机测试配置类"""
    # 服务器配置（虚拟机网络）
    SERVER_IP = "192.168.100.2"  # 服务器虚拟机IP
    SERVER_PORT = 1379
    STUDENT_ID = "testuser123"
    
    # 测试文件配置
    TEST_FILE_SIZE_10MB = 10 * 1024 * 1024  # 10MB
    TEST_FILE_SIZE_1KB = 1024  # 1KB
    TEST_FILE_SIZE_100KB = 100 * 1024  # 100KB
    TEST_FILE_SIZE_1MB = 1024 * 1024  # 1MB
    TEST_FILE_SIZE_50MB = 50 * 1024 * 1024  # 50MB
    
    # 测试次数
    TEST_RETRY_COUNT = 3
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    
    # 项目路径（在虚拟机中）
    PROJECT_PATH = "/home/stepuser/TCPclient/"

class VMTestLogger:
    """虚拟机测试日志记录器"""
    
    def __init__(self, test_name):
        self.test_name = test_name
        # 在虚拟机中使用绝对路径
        self.log_dir = Path(VMTestConfig.PROJECT_PATH) / "test" / test_name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志记录器
        self.logger = logging.getLogger(test_name)
        self.logger.setLevel(VMTestConfig.LOG_LEVEL)
        
        # 清除已存在的处理器
        self.logger.handlers.clear()
        
        # 文件处理器
        log_file = self.log_dir / "test.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(VMTestConfig.LOG_LEVEL)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(VMTestConfig.LOG_LEVEL)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def info(self, message):
        self.logger.info(message)
        
    def error(self, message):
        self.logger.error(message)
        
    def warning(self, message):
        self.logger.warning(message)
        
    def debug(self, message):
        self.logger.debug(message)

class VMFileManager:
    """虚拟机文件管理工具"""
    
    @staticmethod
    def create_test_file(size, filename):
        """在虚拟机中创建指定大小的测试文件"""
        filepath = Path(VMTestConfig.PROJECT_PATH) / "test" / "test_data" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            # 写入指定大小的随机数据
            chunk_size = 1024 * 1024  # 1MB chunks
            remaining = size
            
            while remaining > 0:
                current_chunk = min(chunk_size, remaining)
                # 创建重复的测试数据模式，便于验证
                pattern = b'A' * 1024 + b'B' * 1024 + b'C' * 1024 + b'D' * 1024
                if len(pattern) > current_chunk:
                    pattern = pattern[:current_chunk]
                elif len(pattern) < current_chunk:
                    pattern = (pattern * (current_chunk // len(pattern) + 1))[:current_chunk]
                
                f.write(pattern)
                remaining -= current_chunk
        
        return filepath
    
    @staticmethod
    def calculate_md5(filepath):
        """计算文件的MD5值"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(1024*1024), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"MD5计算错误: {e}")
            return None
    
    @staticmethod
    def create_empty_file(filename):
        """创建0字节文件"""
        filepath = Path(VMTestConfig.PROJECT_PATH) / "test" / "test_data" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.touch()
        return filepath
    
    @staticmethod
    def create_1byte_file(filename):
        """创建1字节文件"""
        filepath = Path(VMTestConfig.PROJECT_PATH) / "test" / "test_data" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(b'A')
        return filepath

class VMNetworkTester:
    """虚拟机网络测试器"""
    
    @staticmethod
    def check_server_connectivity():
        """检查服务器连接性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((VMTestConfig.SERVER_IP, VMTestConfig.SERVER_PORT))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"服务器连接检查失败: {e}")
            return False
    
    @staticmethod
    def run_client_upload(file_path, custom_key=None, student_id=None):
        """在虚拟机中运行客户端上传"""
        if student_id is None:
            student_id = VMTestConfig.STUDENT_ID
            
        # 构建客户端命令
        client_cmd = [
            "python3", 
            str(Path(VMTestConfig.PROJECT_PATH) / "client.py"),
             # "--ip", VMTestConfig.SERVER_IP,
             # "--port", str(VMTestConfig.SERVER_PORT)
        ]
        
        try:
            # 准备输入数据
            input_data = f"{VMTestConfig.SERVER_IP}\n{student_id}\n{file_path}\n"
            if custom_key:
                input_data += f"{custom_key}\n"
            else:
                input_data += "\n"  # 跳过自定义key
            
            # 执行客户端命令
            start_time = time.time()
            process = subprocess.Popen(
                client_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=input_data, timeout=300)  # 5分钟超时
            print(stdout)
            end_time = time.time()
            
            return {
                'success': process.returncode == 0,
                'return_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'duration': end_time - start_time,
                'file_path': file_path
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': '客户端执行超时',
                'duration': 300,
                'file_path': file_path
            }
        except Exception as e:
            return {
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': 0,
                'file_path': file_path
            }

def save_vm_test_results(test_name, results):
    """保存虚拟机测试结果"""
    results_dir = Path(VMTestConfig.PROJECT_PATH) / "test" / test_name
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / "results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

def verify_file_integrity_vm(local_md5, stdout):
    """在虚拟机环境中验证文件完整性"""
   
    try:
        server_md5 = None
        lines = stdout.splitlines()
        for line in lines:
            # 寻找以"File MD5:"开头的行（忽略前后空格）
            if line.strip().startswith("Server file MD5:"):
                # 分割冒号，取后面的部分并去除首尾空格（处理可能的空格）
                server_md5 = line.split(":", 1)[1].strip()
        print(server_md5)
        if local_md5 and server_md5 and local_md5 == server_md5:
            return True, local_md5, server_md5
        else:
            return False, local_md5, server_md5
            
    except Exception as e:
        print(f"文件完整性验证错误: {e}")
        return False, None, None

if __name__ == "__main__":
    # 测试工具模块
    print("STEP虚拟机测试工具模块加载完成")
    print(f"服务器IP: {VMTestConfig.SERVER_IP}")
    print(f"项目路径: {VMTestConfig.PROJECT_PATH}")