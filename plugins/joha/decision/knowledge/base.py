"""
知识库模块 v3.0 - 分片式存储架构
将 storage/txt 目录下的 JSON 分片文件转换为可查询的知识库

改进特性：
- 结构化 JSON 存储（替代旧版 txt）
- 分片式管理（每片100条，自动扩展）
- jieba 中文分词增强关键词提取
- BM25 算法提升搜索相关性
- 结果去重与日期过滤
- 动态文档管理（增删改）
- 增量热重载
- 文档统计与重复检测
"""

import os
import re
import math
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 尝试导入 jieba，未安装则降级为简单正则分词
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba 未安装，使用正则分词作为降级方案。建议运行: pip install jieba")


class Document:
    """知识库文档模型"""
    
    def __init__(self, doc_id: str, filename: str, title: str, timestamp: Optional[datetime],
                 user_question: str, ai_response: str, full_content: str, keywords: List[str],
                 file_path: Path = None, file_mtime: float = 0):
        self.id = doc_id
        self.filename = filename
        self.title = title
        self.timestamp = timestamp
        self.user_question = user_question
        self.ai_response = ai_response
        self.full_content = full_content
        self.keywords = keywords
        self.file_path = file_path
        self.file_mtime = file_mtime
        self.word_count = len(full_content)
        self.token_count = 0  # 由分词器填充
        
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'filename': self.filename,
            'title': self.title,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_question': self.user_question,
            'ai_response': self.ai_response,
            'full_content': self.full_content,
            'keywords': self.keywords,
            'word_count': self.word_count,
            'token_count': self.token_count,
        }
    
    def get_searchable_text(self) -> str:
        """获取用于搜索的完整文本"""
        return f"{self.user_question}\n{self.ai_response}\n{self.title}"


class BM25Index:
    """BM25 索引实现"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Document] = []
        self.doc_freqs: Dict[str, int] = {}  # 词项的文档频率
        self.doc_lengths: List[int] = []      # 每个文档的长度
        self.avg_doc_length: float = 0.0      # 平均文档长度
        self.total_docs: int = 0
        self.term_indices: List[Dict[str, int]] = []  # 每个文档的词频
        self._built = False
        
    def build(self, documents: List[Document], tokenizer: Callable[[str], List[str]]):
        """构建 BM25 索引"""
        self.documents = documents
        self.total_docs = len(documents)
        self.doc_lengths = []
        self.term_indices = []
        self.doc_freqs = {}
        
        total_length = 0
        
        for doc in documents:
            text = doc.get_searchable_text()
            tokens = tokenizer(text)
            doc.token_count = len(tokens)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)
            
            # 统计词频
            term_freq: Dict[str, int] = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
            
            self.term_indices.append(term_freq)
            
            # 更新文档频率
            for term in set(term_freq.keys()):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        
        self.avg_doc_length = total_length / max(self.total_docs, 1)
        self._built = True
        
    def search(self, query: str, tokenizer: Callable[[str], List[str]], top_k: int = 10) -> List[Tuple[Document, float]]:
        """使用 BM25 搜索文档"""
        if not self._built or self.total_docs == 0:
            return []
        
        query_tokens = tokenizer(query)
        if not query_tokens:
            return []
        
        scores = [0.0] * self.total_docs
        
        for token in query_tokens:
            # 计算 IDF
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue
            
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            # 计算每个文档的得分
            for i, term_freq in enumerate(self.term_indices):
                freq = term_freq.get(token, 0)
                if freq == 0:
                    continue
                
                doc_len = self.doc_lengths[i]
                denom = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                scores[i] += idf * (freq * (self.k1 + 1)) / denom
        
        # 排序并返回 top_k
        doc_scores = list(zip(self.documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [(doc, score) for doc, score in doc_scores if score > 0][:top_k]


class KnowledgeBase:
    """知识库类，用于管理和查询 txt 目录中的知识文件"""
    
    # 停用词列表
    STOP_WORDS: Set[str] = set([
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '个', '之', '与', '及', '等', '或', '但', '而', '如果', '因为', '所以', '可以', '让', '给', '把', '被', '将', '对', '能', '还', '过', '做', '来', '它', '们', '为', '以', '可', '于', '则', '却', '下', '地', '得', '着', '过', '但', '又', '很', '都', '只', '最', '和', '或', '既', '即', '虽', '而', '因', '此', '若', '当', '向', '从', '由', '自', '至', '往', '在', '跟', '同', '给', '把', '比', '被', '叫', '让', '关于', '对于', '由于', '根据', '按照', '通过', '经过', '随着', '除了', '除去', '除开', '有关', '涉及', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this', 'that', 'these', 'those',
    ])
    
    def __init__(self, txt_dir: str = None):
        """
        初始化知识库
        
        Args:
            txt_dir: 文本文件目录路径，默认 joha/storage/txt
        """
        if txt_dir is None:
            current_file_dir = Path(__file__).parent.parent.parent
            self.txt_dir = current_file_dir / "storage" / "txt"
        else:
            self.txt_dir = Path(txt_dir)
        
        self.documents: List[Document] = []
        self.bm25_index = BM25Index()
        self.indexed = False
        self._file_mtimes: Dict[Path, float] = {}
        
        # 尝试加载 jieba 用户词典（如果存在）
        self._load_jieba_dict()
        
        self.load_documents()
    
    def _load_jieba_dict(self):
        """加载自定义词典"""
        if not JIEBA_AVAILABLE:
            return
        dict_path = self.txt_dir.parent / "user_dict.txt"
        if dict_path.exists():
            try:
                jieba.load_userdict(str(dict_path))
                logger.info(f"已加载自定义词典: {dict_path}")
            except Exception as e:
                logger.warning(f"加载自定义词典失败: {e}")
    
    def _tokenize(self, text: str) -> List[str]:
        """分词，优先使用 jieba，降级为正则"""
        if not text:
            return []
        
        if JIEBA_AVAILABLE:
            # 使用 jieba 分词，过滤停用词和单字
            tokens = []
            for word, flag in pseg.cut(text.lower()):
                word = word.strip()
                if len(word) <= 1 or word in self.STOP_WORDS:
                    continue
                # 保留名词、动词、形容词、英文等技术相关词性
                if flag.startswith(('n', 'v', 'a', 'eng', 'x')) or word.isalnum():
                    tokens.append(word)
            return tokens
        else:
            # 降级方案：正则提取中文词语和英文单词
            chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text.lower())
            english_words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
            all_words = chinese_words + english_words
            return [w for w in all_words if w not in self.STOP_WORDS]
    
    def load_documents(self):
        """加载分片式 JSON 知识库文件"""
        if not self.txt_dir.exists():
            logger.warning(f"知识库目录不存在: {self.txt_dir}")
            return
        
        # 查找所有分片文件 (knowledge_*.json)
        shard_files = sorted(self.txt_dir.glob("knowledge_*.json"))
        
        if not shard_files:
            logger.warning(f"未找到分片文件，尝试加载独立 JSON 文件")
            self._load_individual_json_files()
            return
        
        new_docs = []
        total_docs = 0
        
        for shard_file in shard_files:
            try:
                with open(shard_file, 'r', encoding='utf-8') as f:
                    shard_data = json.load(f)
                    
                    # 检查是否为分片格式
                    if 'documents' not in shard_data:
                        logger.warning(f"跳过非分片文件: {shard_file}")
                        continue
                    
                    documents_in_shard = shard_data['documents']
                    
                    for doc_data in documents_in_shard:
                        doc = self._create_document_from_json(doc_data, shard_file.name)
                        if doc:
                            new_docs.append(doc)
                            total_docs += 1
                            
            except Exception as e:
                logger.error(f"加载分片失败 {shard_file}: {e}")
        
        if new_docs:
            self.documents = new_docs
            logger.info(f"已加载 {total_docs} 个知识文档（{len(shard_files)} 个分片）")
        else:
            logger.warning("未加载到任何文档")
        
        self.indexed = False  # 标记需要重建索引
    
    def _load_individual_json_files(self):
        """加载独立的 JSON 文件（兼容旧格式）"""
        json_files = list(self.txt_dir.glob("*.json"))
        # 排除分片文件和报告文件
        json_files = [f for f in json_files if not f.name.startswith('knowledge_') and not f.name.endswith('_report.json')]
        
        new_docs = []
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                    doc = self._create_document_from_json(doc_data, json_file.name)
                    if doc:
                        new_docs.append(doc)
            except Exception as e:
                logger.error(f"加载 JSON 文件失败 {json_file}: {e}")
        
        if new_docs:
            self.documents = new_docs
            logger.info(f"已加载 {len(new_docs)} 个独立 JSON 文档")
        
        self.indexed = False
    
    def _create_document_from_json(self, doc_data: dict, source_file: str) -> Optional[Document]:
        """
        从 JSON 数据创建 Document 对象
        
        Args:
            doc_data: JSON 格式的文档数据
            source_file: 源文件名
            
        Returns:
            Document 对象或 None
        """
        try:
            # 提取字段（支持新旧两种格式）
            doc_id = doc_data.get('id', f"doc_{hash(source_file)}")
            filename = doc_data.get('filename', source_file)
            title = doc_data.get('title', filename.replace('.json', '').replace('_', ' '))
            
            # 处理时间戳
            timestamp_str = doc_data.get('timestamp', '')
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    pass
            
            user_question = doc_data.get('question', doc_data.get('user_question', ''))
            ai_response = doc_data.get('response', doc_data.get('ai_response', ''))
            full_content = doc_data.get('full_text', doc_data.get('full_content', ''))
            
            # 如果没有结构化字段，尝试从 full_content 解析
            if not user_question and not ai_response and full_content:
                parsed = self._parse_document(full_content, filename)
                if parsed:
                    return parsed
            
            # 提取关键词
            searchable_text = f"{user_question}\n{ai_response}\n{title}"
            keywords = self._extract_keywords(searchable_text)
            
            return Document(
                doc_id=doc_id,
                filename=filename,
                title=title[:100],
                timestamp=timestamp,
                user_question=user_question[:500] if user_question else '',
                ai_response=ai_response[:1000] if ai_response else '',
                full_content=full_content,
                keywords=keywords,
                file_path=None,
                file_mtime=0,
            )
        except Exception as e:
            logger.error(f"创建文档对象失败: {e}")
            return None
    
    def _parse_document(self, content: str, filename: str, file_path: Path = None,
                        file_mtime: float = 0) -> Optional[Document]:
        """解析单个文档内容"""
        lines = content.split('\n')
        
        # 提取时间信息
        timestamp = None
        title = filename.replace('.txt', '').replace('_', ' ')
        
        if lines and lines[0].startswith('时间:'):
            try:
                time_str = lines[0].replace('时间:', '').strip()
                timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        # 查找用户问题和AI回复部分
        user_question = ""
        ai_response = ""
        
        current_section = None
        for line in lines:
            if '【用户问题】' in line or line.strip() == '【用户问题】':
                current_section = 'question'
            elif '【AI 回复】' in line or line.strip() == '【AI 回复】':
                current_section = 'response'
            elif current_section == 'question' and not line.strip().startswith('【'):
                user_question += line + '\n'
            elif current_section == 'response' and not line.strip().startswith('【'):
                ai_response += line + '\n'
        
        user_question = user_question.strip()
        ai_response = ai_response.strip()
        
        # 如果无法解析结构化内容，尝试其他格式
        if not user_question and not ai_response:
            # 尝试 "问题：" / "回答：" 格式
            q_match = re.search(r'问题[：:]\s*(.+?)(?=\n\n|\n回答[：:]|$)', content, re.DOTALL)
            a_match = re.search(r'回答[：:]\s*(.+)$', content, re.DOTALL)
            if q_match:
                user_question = q_match.group(1).strip()
            if a_match:
                ai_response = a_match.group(1).strip()
        
        # 如果仍无法解析，将整个内容作为响应
        if not user_question and not ai_response:
            parts = filename.split('-', 1)
            if len(parts) > 1:
                title = parts[1].replace('.txt', '')
            ai_response = content
        
        full_text = f"{user_question} {ai_response}"
        keywords = self._extract_keywords(full_text)
        
        return Document(
            doc_id=str(hash(str(file_path) if file_path else filename)),
            filename=filename,
            title=title,
            timestamp=timestamp,
            user_question=user_question,
            ai_response=ai_response,
            full_content=content,
            keywords=keywords,
            file_path=file_path,
            file_mtime=file_mtime,
        )
    
    def _extract_keywords(self, text: str, top_k: int = 30) -> List[str]:
        """从文本中提取关键词"""
        tokens = self._tokenize(text)
        
        # 统计词频
        freq: Dict[str, int] = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        
        # 按频率排序，返回高频词
        sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        return [word for word, count in sorted_words[:top_k]]
    
    def _build_index(self):
        """构建 BM25 索引"""
        if not self.documents:
            return
        
        self.bm25_index.build(self.documents, self._tokenize)
        self.indexed = True
        logger.debug(f"BM25 索引构建完成，文档数: {len(self.documents)}")
    
    def _ensure_index(self):
        """确保索引已构建"""
        if not self.indexed:
            self._build_index()
    
    def search(self, query: str, top_k: int = 5, min_score: float = 0.01,
               date_from: Optional[datetime] = None,
               date_to: Optional[datetime] = None,
               dedup: bool = True,
               dedup_threshold: float = 0.85) -> List[Dict]:
        """
        搜索相关文档
        
        Args:
            query: 查询字符串
            top_k: 返回最相关的前k个文档
            min_score: 最低相似度阈值
            date_from: 起始日期过滤
            date_to: 结束日期过滤
            dedup: 是否对结果去重
            dedup_threshold: 去重相似度阈值
            
        Returns:
            相关文档列表，按相关性排序，包含 score 字段
        """
        self._ensure_index()
        
        if not self.documents:
            return []
        
        # BM25 搜索
        bm25_results = self.bm25_index.search(query, self._tokenize, top_k=top_k * 3)
        
        # 计算混合得分（BM25 + 关键词 + 短语匹配）
        results = []
        query_lower = query.lower()
        query_tokens = set(self._tokenize(query))
        
        for doc, bm25_score in bm25_results:
            # 日期过滤
            if date_from and doc.timestamp and doc.timestamp < date_from:
                continue
            if date_to and doc.timestamp and doc.timestamp > date_to:
                continue
            
            # 关键词匹配得分
            keyword_matches = sum(1 for kw in doc.keywords if kw.lower() in query_lower)
            keyword_score = keyword_matches / max(len(doc.keywords), 1)
            
            # 短语匹配得分
            doc_text = doc.get_searchable_text().lower()
            phrase_score = 0.0
            if query_lower in doc_text:
                phrase_score = 1.0
            elif any(qt in doc_text for qt in query_tokens):
                phrase_score = 0.5
            
            # 标题匹配加权
            title_score = 0.0
            if query_lower in doc.title.lower():
                title_score = 1.0
            elif any(qt in doc.title.lower() for qt in query_tokens):
                title_score = 0.3
            
            # 综合得分（BM25 为主，其他为辅）
            # 对 BM25 得分做归一化压缩
            normalized_bm25 = min(bm25_score / 10.0, 1.0) if bm25_score > 0 else 0
            final_score = (normalized_bm25 * 0.5 +
                          keyword_score * 0.15 +
                          phrase_score * 0.15 +
                          title_score * 0.2)
            
            if final_score >= min_score:
                results.append((doc, final_score))
        
        # 按得分排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 去重
        if dedup:
            results = self._deduplicate_results(results, dedup_threshold)
        
        # 格式化为字典
        formatted = []
        for doc, score in results[:top_k]:
            item = doc.to_dict()
            item['score'] = round(score, 4)
            formatted.append(item)
        
        return formatted
    
    def _deduplicate_results(self, results: List[Tuple[Document, float]],
                             threshold: float) -> List[Tuple[Document, float]]:
        """对搜索结果去重"""
        if not results:
            return results
        
        deduped = [results[0]]
        
        for doc, score in results[1:]:
            is_duplicate = False
            for kept_doc, _ in deduped:
                sim = self._text_similarity(doc.get_searchable_text(), kept_doc.get_searchable_text())
                if sim >= threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                deduped.append((doc, score))
        
        return deduped
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度（Jaccard 系数）"""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        return len(intersection) / len(union)
    
    def search_by_date(self, query: str, days: int = 7, top_k: int = 5) -> List[Dict]:
        """
        搜索最近 N 天内的文档
        
        Args:
            query: 查询字符串
            days: 最近多少天
            top_k: 返回结果数
        """
        date_from = datetime.now() - timedelta(days=days)
        return self.search(query, top_k=top_k, date_from=date_from)
    
    def add_document(self, content: str = "", title: str = "", filename: str = None,
                     question: str = "", response: str = "") -> Optional[str]:
        """
        动态添加文档到知识库（分片式存储）
        
        Args:
            content: 文档内容（兼容旧版）
            title: 文档标题
            filename: 文件名（自动生成如果不提供）
            question: 用户问题（新版结构化字段）
            response: AI回复（新版结构化字段）
            
        Returns:
            文档 ID 或 None
        """
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            
            if filename is None:
                safe_title = title[:20].replace("/", "_").replace("\\", "_").replace(":", "_") if title else "manual"
                filename = f"{timestamp}-{safe_title}.json"
            
            # 构建结构化文档数据
            doc_data = {
                'id': f"doc_{timestamp}_{filename}",
                'filename': filename,
                'title': title[:100] if title else '',
                'source': 'auto_save',
                'full_text': content if content else f"{question}\n{response}",
                'question': question[:500] if question else '',
                'response': response[:1000] if response else '',
                'timestamp': now.isoformat(),
                'word_count': len(content.split()) if content else 0,
                'char_count': len(content) if content else 0,
            }
            
            # 追加到最后一个分片，或创建新分片
            self._append_to_shard(doc_data)
            
            # 解析并添加到内存
            doc = self._create_document_from_json(doc_data, filename)
            if doc:
                self.documents.append(doc)
                self.indexed = False
                logger.info(f"已添加文档到分片: {filename}")
                return doc.id
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
        return None
    
    def _append_to_shard(self, doc_data: dict, shard_size: int = 100):
        """
        将文档追加到分片文件
        
        Args:
            doc_data: 文档数据
            shard_size: 每个分片的最大文档数
        """
        # 查找所有分片文件
        shard_files = sorted(self.txt_dir.glob("knowledge_*.json"))
        
        if shard_files:
            # 使用最后一个分片
            last_shard = shard_files[-1]
            with open(last_shard, 'r', encoding='utf-8') as f:
                shard_data = json.load(f)
            
            documents = shard_data.get('documents', [])
            
            # 如果当前分片已满，创建新分片
            if len(documents) >= shard_size:
                shard_num = len(shard_files) + 1
                self._create_new_shard(shard_num, [doc_data])
            else:
                # 追加到当前分片
                documents.append(doc_data)
                shard_data['documents'] = documents
                shard_data['metadata']['document_count'] = len(documents)
                shard_data['metadata']['updated_at'] = datetime.now().isoformat()
                
                with open(last_shard, 'w', encoding='utf-8') as f:
                    json.dump(shard_data, f, ensure_ascii=False, indent=2)
        else:
            # 没有分片，创建第一个
            self._create_new_shard(1, [doc_data])
    
    def _create_new_shard(self, shard_num: int, documents: list):
        """
        创建新的分片文件
        
        Args:
            shard_num: 分片编号
            documents: 文档列表
        """
        shard_filename = f"knowledge_{shard_num:04d}.json"
        shard_path = self.txt_dir / shard_filename
        
        shard_data = {
            'metadata': {
                'shard_number': shard_num,
                'total_shards': shard_num,
                'document_count': len(documents),
                'created_at': datetime.now().isoformat(),
                'version': '1.8.0',
            },
            'documents': documents,
        }
        
        with open(shard_path, 'w', encoding='utf-8') as f:
            json.dump(shard_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已创建新分片: {shard_filename} ({len(documents)} 条)")
    
    def remove_document(self, doc_id: str) -> bool:
        """
        从知识库中删除文档
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            是否成功删除
        """
        for doc in self.documents:
            if doc.id == doc_id:
                self.documents.remove(doc)
                # 同时删除文件
                if doc.file_path and doc.file_path.exists():
                    try:
                        doc.file_path.unlink()
                        self._file_mtimes.pop(doc.file_path, None)
                    except Exception as e:
                        logger.warning(f"删除文件失败: {e}")
                self.indexed = False
                logger.info(f"已删除文档: {doc.filename}")
                return True
        return False
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """根据ID获取特定文档"""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc.to_dict()
        return None
    
    def get_all_documents(self) -> List[Dict]:
        """获取所有文档"""
        return [doc.to_dict() for doc in self.documents]
    
    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        if not self.documents:
            return {
                'total_documents': 0,
                'total_words': 0,
                'avg_words_per_doc': 0,
                'date_range': None,
                'top_keywords': [],
                'file_count_by_dir': {},
            }
        
        total_words = sum(d.word_count for d in self.documents)
        timestamps = [d.timestamp for d in self.documents if d.timestamp]
        
        # 统计目录分布
        dir_counts: Dict[str, int] = {}
        for d in self.documents:
            if d.file_path:
                rel = d.file_path.relative_to(self.txt_dir)
                parent = str(rel.parent) if rel.parent != Path('.') else '(根目录)'
                dir_counts[parent] = dir_counts.get(parent, 0) + 1
        
        # 全局关键词统计
        all_keywords: Dict[str, int] = {}
        for d in self.documents:
            for kw in d.keywords:
                all_keywords[kw] = all_keywords.get(kw, 0) + 1
        top_keywords = sorted(all_keywords.items(), key=lambda x: -x[1])[:20]
        
        return {
            'total_documents': len(self.documents),
            'total_words': total_words,
            'avg_words_per_doc': round(total_words / len(self.documents), 2),
            'date_range': {
                'earliest': min(timestamps).isoformat() if timestamps else None,
                'latest': max(timestamps).isoformat() if timestamps else None,
            },
            'top_keywords': top_keywords,
            'file_count_by_dir': dir_counts,
        }
    
    def find_duplicates(self, threshold: float = 0.9) -> List[Tuple[Dict, Dict, float]]:
        """
        查找重复或高度相似的文档
        
        Returns:
            相似文档对列表 (doc1, doc2, similarity)
        """
        duplicates = []
        docs = self.documents
        
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                sim = self._text_similarity(docs[i].get_searchable_text(),
                                            docs[j].get_searchable_text())
                if sim >= threshold:
                    duplicates.append((docs[i].to_dict(), docs[j].to_dict(), round(sim, 4)))
        
        return duplicates
    
    def refresh(self):
        """刷新知识库，增量重新加载文档"""
        self.load_documents()
        self._build_index()
    
    def full_rebuild(self):
        """完全重建知识库（清空后重新加载）"""
        self.documents = []
        self._file_mtimes = {}
        self.load_documents()
        self._build_index()


# 全局知识库实例
_kb_instance = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库实例（单例模式）"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance


def search_knowledge_base(query: str, top_k: int = 5, **kwargs) -> List[Dict]:
    """便捷函数：直接搜索知识库"""
    kb = get_knowledge_base()
    return kb.search(query, top_k=top_k, **kwargs)


if __name__ == "__main__":
    kb = get_knowledge_base()
    stats = kb.get_statistics()
    print(f"知识库统计:")
    print(f"  文档数: {stats['total_documents']}")
    print(f"  总字数: {stats['total_words']}")
    print(f"  平均字数: {stats['avg_words_per_doc']}")
    if stats['date_range']:
        print(f"  时间范围: {stats['date_range']['earliest']} ~ {stats['date_range']['latest']}")
    
    # 测试搜索
    test_queries = ["python", "go语言", "插件中台", "高并发"]
    for q in test_queries:
        results = kb.search(q, top_k=3)
        print(f"\n搜索 '{q}':")
        for r in results:
            print(f"  [{r['score']:.3f}] {r['title'][:40]}...")
