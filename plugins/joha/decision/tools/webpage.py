"""
网页抓取工具
支持提取网页内容
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse


class WebpageTool:
    """网页抓取工具类"""
    
    def __init__(self, timeout: int = 10):
        """
        初始化网页工具
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch(self, url: str, max_length: int = 3000) -> str:
        """
        抓取网页内容
        
        Args:
            url: 网页 URL
            max_length: 返回内容的最大长度
            
        Returns:
            网页文本内容
        """
        try:
            # 验证 URL
            if not self._is_valid_url(url):
                return f"无效的 URL: {url}"
            
            # 发送请求
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            # 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            # 提取文本
            text = soup.get_text(separator='\n', strip=True)
            
            # 清理空白行
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            # 截断过长内容
            if len(cleaned_text) > max_length:
                cleaned_text = cleaned_text[:max_length] + "\n\n[内容过长，已截断...]"
            
            return cleaned_text if cleaned_text else "未提取到有效内容"
        
        except requests.exceptions.Timeout:
            return f"请求超时: {url}"
        except requests.exceptions.ConnectionError:
            return f"连接失败: {url}"
        except Exception as e:
            return f"抓取失败: {str(e)}"
    
    def fetch_title(self, url: str) -> str:
        """
        获取网页标题
        
        Args:
            url: 网页 URL
            
        Returns:
            网页标题
        """
        try:
            if not self._is_valid_url(url):
                return f"无效的 URL: {url}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else "无标题"
            
            return title.strip()
        except Exception as e:
            return f"获取标题失败: {str(e)}"
    
    def _is_valid_url(self, url: str) -> bool:
        """验证 URL 是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
