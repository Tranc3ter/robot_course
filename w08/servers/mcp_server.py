# MCP Server using DeepSeek API
import zmq
import json
from openai import OpenAI

class MCPServer:
    def __init__(self, port: int = 5557):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{port}")  # 改为0.0.0.0允许外部连接
        
        # 修复OpenAI客户端初始化
        try:
            self.client = OpenAI(
                api_key="your_deepseek_api_key",  # 替换为您的DeepSeek API Key
                base_url="https://api.deepseek.com",
                # 移除 'proxies' 参数，因为它不再被支持
            )
            print(f"MCP Server (真实DeepSeek) started on port {port}")
        except Exception as e:
            print(f"警告: OpenAI客户端初始化失败: {e}")
            print("将使用模拟模式运行")
            self.client = None
        
        # 对话历史
        self.conversation_history = [
            {"role": "system", "content": "你是一个友好的助手。"},
        ]
    
    def generate_response(self, user_input: str) -> str:
        """生成对话回复"""
        try:
            # 添加用户输入到历史
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # 限制历史长度
            if len(self.conversation_history) > 10:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-8:]
            
            if self.client:
                # 调用真实API
                completion = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.conversation_history,
                    stream=False
                )
                
                # 获取助手回复
                assistant_reply = completion.choices[0].message.content
            else:
                # 模拟回复
                assistant_reply = f"模拟回复: 你说的是 '{user_input}'"
            
            # 添加到历史
            self.conversation_history.append({"role": "assistant", "content": assistant_reply})
            
            return assistant_reply
            
        except Exception as e:
            print(f"MCP生成错误: {e}")
            return f"抱歉，我遇到了一些问题: {str(e)}"
    
    def run(self):
        """运行服务器主循环"""
        while True:
            try:
                # 接收用户输入
                message = self.socket.recv_string()
                data = json.loads(message)
                
                user_input = data.get('text', '')
                print(f"[MCP] 收到请求: {user_input}")
                
                # 生成回复
                response_text = self.generate_response(user_input)
                print(f"[MCP] 生成回复: {response_text[:50]}...")
                
                # 发送响应
                response = {
                    'response': response_text,
                    'status': 'success'
                }
                
                self.socket.send_json(response)
                
            except Exception as e:
                print(f"MCP服务器错误: {e}")
                error_response = {
                    'response': '',
                    'status': 'error',
                    'error': str(e)
                }
                self.socket.send_json(error_response)

if __name__ == "__main__":
    server = MCPServer(port=5557)
    server.run()