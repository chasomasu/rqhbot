import json
import os
from threading import Lock


hmd=[""]
gly=["2654278608"]

class AnswerManager:
    """管理问答数据的类，使用内存缓存 + 异步写入策略，消除并发干扰"""
    def __init__(self, precise_file_path, fuzzy_file_path):
        self.precise_file_path = precise_file_path
        self.fuzzy_file_path = fuzzy_file_path
        self.lock = Lock()  # 用于保护内存数据的读锁
        self.write_lock = Lock()  # 专门用于写文件的锁
        self.precise_data = {}  # 内存缓存
        self.fuzzy_data = {}    # 内存缓存
        self.dirty = False  # 脏标记，记录是否需要保存
        self.load_all_to_memory()  # 启动时加载到内存
        
    def load_all_to_memory(self):
        """启动时一次性加载所有数据到内存"""
        with self.lock:
            self.precise_data = self._safe_load(self.precise_file_path, {})
            self.fuzzy_data = self._safe_load(self.fuzzy_file_path, {})
        print(f"问答数据已加载到内存：精确{len(self.precise_data)}条，模糊{len(self.fuzzy_data)}条")
    
    def _safe_load(self, path, default):
        """安全地加载 JSON 文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else default
        except FileNotFoundError:
            # 如果文件不存在，创建一个空的问答文件
            self._save_file(path, {})
            return default
        except json.JSONDecodeError:
            # 如果文件格式错误，创建一个空的问答文件
            self._save_file(path, {})
            return default
        except Exception as e:
            print(f"加载文件失败 {path}: {e}")
            return default
    
    def _save_file(self, path, data):
        """保存数据到文件（内部方法，不加锁）"""
        temp_file = path + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(temp_file, path)
            return True
        except Exception as e:
            print(f"保存文件失败 {path}: {e}")
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False
    
    
    def save_if_dirty(self):
        """如果数据被修改过，则保存并返回是否成功"""
        if not self.dirty:
            return True
        
        with self.write_lock:  # 确保同一时间只有一个线程在写文件
            success_precise = self._save_file(self.precise_file_path, self.precise_data)
            success_fuzzy = self._save_file(self.fuzzy_file_path, self.fuzzy_data)
            
            if success_precise and success_fuzzy:
                self.dirty = False  # 保存成功后清除标记
                return True
            return False
    
    def load_all_data(self):
        """加载所有问答数据（精确 + 模糊），从内存缓存读取"""
        with self.lock:
            all_data = self.precise_data.copy()
            all_data.update(self.fuzzy_data)
            return all_data
    
    def save_precise_data(self, data):
        """安全地保存精确问答数据（保留接口兼容性，实际使用内存缓存）"""
        with self.lock:
            self.precise_data = data
            self.dirty = True
        return self.save_if_dirty()
    
    def save_fuzzy_data(self, data):
        """安全地保存模糊问答数据（保留接口兼容性，实际使用内存缓存）"""
        with self.lock:
            self.fuzzy_data = data
            self.dirty = True
        return self.save_if_dirty()
    
    def add_precise_answer(self, question, answer):
        """添加精确问答对（只写内存，标记为脏，由后台任务异步保存）"""
        with self.lock:
            self.precise_data[question.strip()] = answer.strip()
            self.dirty = True  # 标记需要保存
        return True
    
    def add_fuzzy_answer(self, question, answer):
        """添加模糊问答对（只写内存，标记为脏，由后台任务异步保存）"""
        with self.lock:
            self.fuzzy_data[question.strip()] = answer.strip()
            self.dirty = True  # 标记需要保存
        return True
    
    def add_normal_answer(self, question, answer):
        """添加普通问答对（默认到模糊文件）"""
        return self.add_fuzzy_answer(question, answer)
    
    def update_answer(self, question, new_answer):
        """更新问答对（先检查精确文件，再检查模糊文件，只写内存）"""
        with self.lock:
            if question in self.precise_data:
                self.precise_data[question] = new_answer.strip()
                self.dirty = True
                return True
            
            if question in self.fuzzy_data:
                self.fuzzy_data[question] = new_answer.strip()
                self.dirty = True
                return True
            
            return False
    
    def delete_answer(self, question):
        """删除问答对（检查两个文件，只写内存）"""
        deleted = False
        
        with self.lock:
            # 尝试从精确问答中删除
            if question in self.precise_data:
                del self.precise_data[question]
                self.dirty = True
                deleted = True
            
            # 尝试从模糊问答中删除
            if question in self.fuzzy_data:
                del self.fuzzy_data[question]
                self.dirty = True
                deleted = True
                
        return deleted
    
    def clear_all_answers(self):
        """清空所有问答（只清空内存，标记为脏）"""
        with self.lock:
            self.precise_data.clear()
            self.fuzzy_data.clear()
            self.dirty = True
        return True
    
    def search_precise(self, question):
        """精确匹配问题（直接在内存缓存中搜索，速度极快）"""
        with self.lock:
            data = self.precise_data
        
        if not question:
            return None
        # 预处理输入问题
        question_processed = self._preprocess_text(question.lower())
        # 在数据中寻找预处理后匹配的项
        for stored_question, answer in data.items():
            stored_processed = self._preprocess_text(stored_question.lower())
            if question_processed == stored_processed:
                return answer
        return None
    
    def search_fuzzy(self, text):
        """模糊匹配问题，key 必须作为连续整体出现，不能拆分、不能少字
        例如：key='ab' 只匹配 'ab'、'abc'、'xab'，不匹配 'a'、'b'、'axby'"""
        with self.lock:
            data = self.fuzzy_data
        
        if not text:
            return None
            
        text_lower = text.lower()
        # 预处理文本，标准化换行符和多余空白
        text_processed = self._preprocess_text(text_lower)
        best_match = None
        best_score = 0
        
        for question, answer in data.items():
            question_lower = question.lower()
            question_processed = self._preprocess_text(question_lower)
            
            # 计算匹配分数
            score = 0
            
            # 精确匹配加分（完全相同）
            if question_processed == text_processed or question_lower == text_lower:
                score += 100
            # 【核心逻辑】输入内容包含完整的 key（连续子串）- key 作为整体，不能拆分
            elif question_lower in text_lower or question_processed in text_processed:
                # key 必须作为连续的整体出现
                score += 80 + len(question)  # 长度越长，相关性可能越高
            # 删除了被包含关系的判断，避免输入部分内容就匹配整个 key
            
            # 更新最佳匹配
            if score > best_score:
                best_score = score
                best_match = answer
        
        return best_match

    def _preprocess_text(self, text):
        """预处理文本，标准化换行符、标点符号和空白字符"""
        import re
        # 标准化换行符为单个空格
        text = re.sub(r'\n+', ' ', text)
        # 标准化多个连续空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 移除首尾空白
        text = text.strip()
        return text

    def _has_common_substring(self, str1, str2, min_length=2):
        """检查两个字符串是否有公共子串"""
        for i in range(len(str1)):
            for j in range(i + min_length, len(str1) + 1):
                substring = str1[i:j]
                if substring in str2:
                    return True
        return False

    def _get_longest_common_substring_length(self, str1, str2):
        """获取两个字符串最长公共子串的长度"""
        m, n = len(str1), len(str2)
        # 创建二维数组存储长度
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        longest = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i - 1] == str2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    longest = max(longest, dp[i][j])
                else:
                    dp[i][j] = 0
        
        return longest
    
    def _levenshtein_distance(self, str1, str2):
        """计算两个字符串之间的 Levenshtein 距离（编辑距离）
        返回将 str1 转换为 str2 所需的最少单字符编辑操作次数"""
        m, n = len(str1), len(str2)
        # 创建二维数组存储距离
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # 初始化边界条件
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # 填充 DP 表
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i - 1] == str2[j - 1]:
                    cost = 0
                else:
                    cost = 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # 删除
                    dp[i][j - 1] + 1,      # 插入
                    dp[i - 1][j - 1] + cost  # 替换
                )
        
        return dp[m][n]


# 获取插件所在目录
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# 初始化问答管理器（会自动加载数据到内存）
answer_manager = AnswerManager(
    os.path.join(PLUGIN_DIR, "precise_ans.json"),
    os.path.join(PLUGIN_DIR, "fuzzy_ans.json")
)


# 插件类已迁移至 main.py，本文件仅保留数据层
