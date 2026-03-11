"""
网页数据自动提取和导出工作流
支持：登录 → 筛选 → 数据提取 → Excel/CSV 导出
"""

import os
import sys
import json
import time
from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WebDataExtractionWorkflow:
    """网页数据自动提取和导出工作流"""
    
    def __init__(self, config_file="config.json"):
        """初始化工作流"""
        self.config = self.load_config(config_file)
        self.driver = None
        self.setup_output_dir()
        
        # 从环境变量覆盖配置（如果设置了）
        if os.getenv('TARGET_USERNAME'):
            self.config['username'] = os.getenv('TARGET_USERNAME')
        if os.getenv('TARGET_PASSWORD'):
            self.config['password'] = os.getenv('TARGET_PASSWORD')
        if os.getenv('TARGET_URL'):
            self.config['target_url'] = os.getenv('TARGET_URL')
    
    def load_config(self, config_file):
        """加载配置文件"""
        if not os.path.exists(config_file):
            print(f"⚠ 配置文件 {config_file} 不存在")
            print("创建默认配置文件...")
            self.create_default_config(config_file)
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✓ 配置文件加载成功")
        return config
    
    @staticmethod
    def create_default_config(config_file):
        """创建默认配置文件"""
        default_config = {
            "target_url": "https://example.com/login",
            "username": "your_username",
            "password": "your_password",
            "headless": True,
            "output_dir": "./downloads",
            "export_format": "excel",
            "selectors": {
                "username_field": "username",
                "password_field": "password",
                "login_button": "login-btn"
            },
            "filters": []
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 默认配置文件已创建: {config_file}")
    
    def setup_output_dir(self):
        """创建输出目录"""
        output_dir = self.config.get('output_dir', './downloads')
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
    
    def setup_driver(self):
        """设置 Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        
        # 在 GitHub Actions 中必须使用 headless 模式
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--single-process')
        
        # 禁用某些功能加快速度
        prefs = {
            'profile.default_content_settings.popups': 0,
            'profile.managed_default_content_settings.images': 2
        }
        options.add_experimental_option('prefs', prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print("✓ 浏览器启动成功")
            return True
        except Exception as e:
            print(f"✗ 浏览器启动失败: {e}")
            return False
    
    def login_with_captcha_wait(self):
        """
        登录流程：自动输入用户名密码，等待用户完成验证码
        在 GitHub Actions 中会失败（无法手动输入），需要特殊处理
        """
        target_url = self.config['target_url']
        username = self.config['username']
        password = self.config['password']
        
        self.driver.get(target_url)
        print(f"✓ 已打开网页: {target_url}")
        
        try:
            # 等待用户名字段加载
            username_selector = self.config['selectors']['username_field']
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, username_selector))
            )
            
            # 自动输入用户名
            username_field.clear()
            username_field.send_keys(username)
            print("✓ 已输入用户名")
            
            # 自动输入密码
            password_selector = self.config['selectors']['password_field']
            password_field = self.driver.find_element(By.ID, password_selector)
            password_field.clear()
            password_field.send_keys(password)
            print("✓ 已输入密码")
            
            print("\n⚠️  需要手动完成登录:")
            print("   1. 在本地运行此脚本")
            print("   2. 在浏览器中手动输入验证码")
            print("   3. 点击登录按钮")
            print("   脚本将在登录完成后继续执行\n")
            
            # 检测登录是否完成
            # 等待特定的登录成功标志（需要根据实际网站调整）
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.CLASS_NAME, "main-content"))
            )
            
            time.sleep(2)
            print("✓ 登录成功！\n")
            return True
            
        except Exception as e:
            print(f"✗ 登录失败: {e}")
            return False
    
    def apply_filters(self):
        """应用筛选条件"""
        filters = self.config.get('filters', [])
        
        if not filters:
            print("ℹ  未设置筛选条件\n")
            return True
        
        print("开始应用筛选条件...\n")
        
        try:
            for filter_item in filters:
                filter_type = filter_item.get('type')
                selector = filter_item.get('selector')
                value = filter_item.get('value')
                name = filter_item.get('name', selector)
                
                print(f"  🔍 筛选 [{name}]: ", end="", flush=True)
                
                if filter_type == 'text':
                    # 文本输入框
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    element.clear()
                    element.send_keys(value)
                    print(f"输入 '{value}' ✓")
                
                elif filter_type == 'select':
                    # 下拉菜单
                    select_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    select_element.click()
                    
                    option = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//option[@value='{value}']")
                        )
                    )
                    option.click()
                    print(f"选择 '{value}' ✓")
                
                elif filter_type == 'date':
                    # 日期选择器
                    date_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    date_field.clear()
                    date_field.send_keys(value)
                    print(f"设置 '{value}' ✓")
                
                elif filter_type == 'click':
                    # 点击按钮
                    button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    button.click()
                    print(f"点击 ✓")
                    time.sleep(2)
                
                time.sleep(1)
            
            print("\n✓ 筛选完成\n")
            return True
            
        except Exception as e:
            print(f"\n✗ 筛选失败: {e}")
            return False
    
    def extract_data(self):
        """提取表格数据"""
        try:
            print("开始提取数据...\n")
            
            # 等待表格加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
            
            all_data = []
            headers = None
            
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"  发现 {len(tables)} 个表格")
            
            for table_idx, table in enumerate(tables):
                print(f"\n  📊 表格 {table_idx + 1}:")
                
                # 提取表头
                header_cells = table.find_elements(
                    By.XPATH, 
                    ".//thead//th | .//tr[1]//th"
                )
                if header_cells:
                    headers = [cell.text.strip() for cell in header_cells]
                    print(f"     表头: {headers}")
                
                # 提取数据
                rows = table.find_elements(
                    By.XPATH, 
                    ".//tbody//tr | .//tr[position()>1]"
                )
                print(f"     数据行数: {len(rows)}")
                
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if cols:
                        row_data = [col.text.strip() for col in cols]
                        all_data.append(row_data)
            
            print(f"\n✓ 成功提取 {len(all_data)} 行数据\n")
            return all_data, headers
            
        except Exception as e:
            print(f"✗ 数据提取失败: {e}")
            return None, None
    
    def export_data(self, data, headers=None):
        """导出数据"""
        if not data:
            print("✗ 没有数据可导出")
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_format = self.config.get('export_format', 'excel')
            
            if export_format == 'excel':
                filename = os.path.join(self.output_dir, f"data_{timestamp}.xlsx")
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(filename, index=False, engine='openpyxl')
                
            elif export_format == 'csv':
                filename = os.path.join(self.output_dir, f"data_{timestamp}.csv")
                df = pd.DataFrame(data, columns=headers)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            file_size = os.path.getsize(filename) / 1024  # KB
            print(f"✓ 数据已导出")
            print(f"📁 文件: {filename}")
            print(f"📊 大小: {file_size:.2f} KB")
            return True
            
        except Exception as e:
            print(f"✗ 导出失败: {e}")
            return False
    
    def run(self):
        """运行完整工作流"""
        print("\n" + "="*70)
        print("🚀 开始执行自动化工作流")
        print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        try:
            # 第一步：启动浏览器
            if not self.setup_driver():
                return False
            
            # 第二步：登录
            if not self.login_with_captcha_wait():
                return False
            
            # 第三步：应用筛选
            if not self.apply_filters():
                return False
            
            # 第四步：提取数据
            data, headers = self.extract_data()
            if data is None:
                return False
            
            # 第五步：导出数据
            if not self.export_data(data, headers):
                return False
            
            print("\n" + "="*70)
            print("✓ 工作流执行成功！")
            print("="*70 + "\n")
            return True
            
        except Exception as e:
            print(f"\n✗ 工作流执行失败: {e}\n")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
                print("浏览器已关闭")

if __name__ == "__main__":
    workflow = WebDataExtractionWorkflow(config_file="config.json")
    success = workflow.run()
    sys.exit(0 if success else 1)
