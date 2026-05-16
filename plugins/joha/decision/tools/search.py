"""
搜索引擎工具
支持多种搜索引擎 API
"""
import requests
from typing import List, Dict, Optional


class SearchTool:
    """搜索引擎工具类"""
    
    def __init__(self, api_key: str = "", engine: str = "duckduckgo"):
        """
        初始化搜索工具
        
        Args:
            api_key: 搜索 API 密钥（可选）
            engine: 搜索引擎类型 (duckduckgo, google, bing)
        """
        self.api_key = api_key
        self.engine = engine
    
    def search(self, query: str, num_results: int = 5) -> str:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
            
        Returns:
            格式化的搜索结果
        """
        try:
            if self.engine == "duckduckgo":
                return self._duckduckgo_search(query, num_results)
            elif self.engine == "google":
                return self._google_search(query, num_results)
            elif self.engine == "bing":
                return self._bing_search(query, num_results)
            else:
                return f"不支持的搜索引擎: {self.engine}"
        except Exception as e:
            return f"搜索失败: {str(e)}"
    
    def _duckduckgo_search(self, query: str, num_results: int = 5) -> str:
        """使用 DDGS (原 duckduckgo_search) 进行搜索"""
        try:
            from ddgs import DDGS
            
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })
            
            return self._format_results(results)
        except ImportError:
            return "请安装 ddgs: pip install ddgs"
        except Exception as e:
            return f"DuckDuckGo 搜索失败: {str(e)}"
    
    def _google_search(self, query: str, num_results: int = 5) -> str:
        """使用 Google Custom Search API"""
        if not self.api_key:
            return "Google 搜索需要 API Key"
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': 'YOUR_CUSTOM_SEARCH_ENGINE_ID',  # 需要配置
                'q': query,
                'num': num_results
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            return self._format_results(results)
        except Exception as e:
            return f"Google 搜索失败: {str(e)}"
    
    def _bing_search(self, query: str, num_results: int = 5) -> str:
        """使用 Bing Search API"""
        if not self.api_key:
            return "Bing 搜索需要 API Key"
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {'q': query, 'count': num_results}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('webPages', {}).get('value', []):
                results.append({
                    'title': item.get('name', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('snippet', '')
                })
            
            return self._format_results(results)
        except Exception as e:
            return f"Bing 搜索失败: {str(e)}"
    
    def _format_results(self, results: List[Dict]) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到相关结果"
        
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result['title']}\n"
                f"   链接: {result['url']}\n"
                f"   摘要: {result['snippet'][:200]}"
            )
        
        return "\n\n".join(formatted)
