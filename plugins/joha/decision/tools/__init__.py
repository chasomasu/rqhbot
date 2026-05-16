"""
工具模块 - 搜索、网页抓取、链接预览和知识库搜索
"""
from .search import SearchTool
from .webpage import WebpageTool
from .link_preview import LinkPreviewTool
from .knowledge_search import KnowledgeBaseSearchTool, get_kb_search_tool

# 全局工具实例
search_tool = SearchTool()
webpage_tool = WebpageTool()
link_preview_tool = LinkPreviewTool()
kb_search_tool = get_kb_search_tool()

__all__ = [
    'SearchTool', 'WebpageTool', 'LinkPreviewTool',
    'KnowledgeBaseSearchTool', 'get_kb_search_tool',
    'search_tool', 'webpage_tool', 'link_preview_tool', 'kb_search_tool',
]
