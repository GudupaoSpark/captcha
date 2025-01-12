import requests
import time
import threading
import webview
import json
import traceback

# 定义基础 URL
BASE_URL = 'https://captcha.1nk.ltd'

def create_session():
    """创建会话并返回会话ID"""
    response = requests.post(f'{BASE_URL}/captcha/session')
    return response.json()['session_id']

def check_session_status(session_id, window):
    """轮询会话状态"""
    max_attempts = 180  # 最大轮询次数，防止无限循环
    attempts = 0
    
    while attempts < max_attempts:
        try:
            response = requests.get(f'{BASE_URL}/captcha/session/{session_id}/status')
            status = response.json()
            
            if status['verified']:
                print("✅ 验证成功！")
                window.destroy()
                break
            
            time.sleep(1)  # 每秒轮询一次
            attempts += 1
        except Exception as e:
            print(f"状态检查出错: {e}")
            break
    
    if attempts >= max_attempts:
        print("❌ 验证超时")
        window.destroy()

def on_script_notify(message):
    """处理 webview 脚本通知的异常处理函数"""
    try:
        if message is not None:
            # 尝试解析 JSON 消息
            parsed_message = json.loads(message)
            print(f"收到脚本通知: {parsed_message}")
        else:
            print("收到空的脚本通知")
    except Exception as e:
        print(f"脚本通知处理错误: {e}")
        traceback.print_exc()

def main():
    # 创建会话
    session_id = create_session()
    print(f"创建会话: {session_id}")
    
    # 构建iframe URL
    iframe_url = f'{BASE_URL}/static/iframe.html?session={session_id}'
    
    # 创建弹出式窗口，并添加脚本通知处理
    window = webview.create_window('验证码系统', iframe_url, width=400, height=500)
    window.events.script_notify = on_script_notify
    
    # 在后台线程中检查状态
    status_thread = threading.Thread(target=check_session_status, args=(session_id, window))
    status_thread.start()
    
    # 启动窗口
    webview.start()
    
    # 等待状态检查线程结束
    status_thread.join()

if __name__ == '__main__':
    main()