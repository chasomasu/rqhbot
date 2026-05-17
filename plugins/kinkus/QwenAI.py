from openai import OpenAI

class QwenClient:
    def __init__(self, api_key, base_url):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.messages = [
            {
                "role": "system",
                "content": """无"""
            }
        ]
    
    def call(self, user_input):
        """发送请求并获取模型响应"""
        self.messages.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model="qwen3.5-omni-flash" ,
            messages=self.messages
        )
        assistant_output = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_output})
        return assistant_output
    
    def chat_loop(self):
        """启动对话循环"""
        assistant_output = "你好！"
        print(f"模型输出：{assistant_output}\n")
        
        while "我已了解" not in assistant_output:
            user_input = input("请输入：")
            assistant_output = self.call(user_input)
            print(f"模型输出：{assistant_output}")
            print("\n")

if __name__ == "__main__":
    # 初始化客户端
    chatbot = QwenClient(
        api_key="sk-66666666",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    # 启动对话
    chatbot.chat_loop()