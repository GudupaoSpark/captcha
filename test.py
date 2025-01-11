import requests
import webbrowser
import time
import threading
import tkinter as tk
import webview

def create_session():
    """创建会话并返回会话ID"""
    response = requests.post('http://localhost:8000/captcha/session')
    return response.json()['session_id']

def check_session_status(session_id, window):
    """轮询会话状态"""
    max_attempts = 180  # 最大轮询次数，防止无限循环
    attempts = 0
    
    while attempts < max_attempts:
        try:
            response = requests.get(f'http://localhost:8000/captcha/session/{session_id}/status')
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

def main():
    # 创建会话
    session_id = create_session()
    print(f"创建会话: {session_id}")
    
    # 构建iframe URL
    iframe_url = f'http://localhost:8000/static/iframe.html?session={session_id}'
    
    # 创建弹出式窗口
    window = webview.create_window('验证码系统', iframe_url, width=400, height=500)
    
    # 在后台线程中检查状态
    status_thread = threading.Thread(target=check_session_status, args=(session_id, window))
    status_thread.start()
    
    # 启动窗口
    webview.start()
    
    # 等待状态检查线程结束
    status_thread.join()

if __name__ == '__main__':
    main()