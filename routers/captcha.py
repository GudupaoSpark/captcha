from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from captcha.image import ImageCaptcha
import uuid
import base64
import random
from io import BytesIO
from datetime import datetime, timedelta

router = APIRouter(prefix="/captcha", tags=["captcha"])

# 会话和验证码存储字典
session_store = {}  # {session_id: {"expire_time": datetime, "captcha_text": str, "captcha_data": base64_encoded_data}}

@router.post("/session")
async def create_session():
    """
    创建一个新的会话。
    
    返回:
        dict: 包含唯一会话ID的字典，该会话ID将在后续验证码操作中使用。
        会话有效期为10分钟。
    """
    session_id = str(uuid.uuid4())
    session_store[session_id] = {
        "expire_time": datetime.now() + timedelta(minutes=10)
    }
    return {"session_id": session_id}

@router.post("/generate/{session_id}")
async def generate_captcha(session_id: str):
    """
    为指定会话生成或刷新数学验证码。
    
    参数:
        session_id (str): 要生成/刷新验证码的会话ID。
    
    返回:
        dict: 包含base64编码的验证码图片。
    
    异常:
        HTTPException: 如果会话不存在或已过期。
    """
    # 检查会话是否存在
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 检查会话是否过期
    if session_store[session_id]["expire_time"] < datetime.now():
        del session_store[session_id]
        raise HTTPException(status_code=404, detail="Session expired")
    
    # 生成随机验证码
    jg = str((j1 := random.randint(2, 9)) + (j2 := random.randint(2, 9)))
    captcha_text = f"{j1} + {j2} ="
    
    # 生成图片
    image = ImageCaptcha()
    image.generate(captcha_text)
    
    # 保存图片到内存并转换为base64
    image_byte_arr = BytesIO()
    image.write(captcha_text, image_byte_arr)
    image_byte_arr = image_byte_arr.getvalue()
    base64_encoded_data = base64.b64encode(image_byte_arr).decode('utf-8')
    
    # 更新会话信息
    session_store[session_id].update({
        "captcha_text": jg,
        "captcha_data": base64_encoded_data,
        "captcha_expire_time": datetime.now() + timedelta(seconds=30),
        "verified": False
    })
    
    return {
        "captcha_image": base64_encoded_data
    }

@router.get("/image/{session_id}")
async def get_captcha_image(session_id: str):
    """
    获取指定会话的验证码图片。
    
    参数:
        session_id (str): 会话ID。
    
    返回:
        Response: PNG格式的验证码图片。
    
    异常:
        HTTPException: 如果会话不存在或验证码已过期。
    """
    # 检查会话是否存在
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_info = session_store[session_id]
    
    # 检查验证码是否过期
    if session_info.get("captcha_expire_time", datetime.min) < datetime.now():
        raise HTTPException(status_code=404, detail="Captcha expired")
    
    base64_encoded_data = session_info.get("captcha_data")
    # 将Base64编码的图片数据解码为字节流
    image_data = base64.b64decode(base64_encoded_data)
    
    # 返回图片响应
    return Response(content=image_data, media_type="image/png")

@router.get("/verify/{session_id}/{user_input}")
async def verify_captcha(session_id: str, user_input: str):
    """
    验证用户输入的验证码是否正确。
    
    参数:
        session_id (str): 会话ID。
        user_input (str): 用户输入的验证码。
    
    返回:
        dict: 验证结果，包含状态和消息。
        - success: 验证成功
        - error: 验证失败
    
    异常:
        HTTPException: 如果会话不存在、已过期或验证码已过期。
    """
    # 检查会话是否存在
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 检查会话是否过期
    if session_store[session_id]["expire_time"] < datetime.now():
        del session_store[session_id]
        raise HTTPException(status_code=404, detail="Session expired")
    
    # 检查会话是否已经验证过
    if session_store[session_id].get("verified", False):
        raise HTTPException(status_code=403, detail="Session already verified")
    
    # 获取验证码文本
    original_text = session_store[session_id].get("captcha_text")
    
    # 检查验证码是否过期
    if session_store[session_id].get("captcha_expire_time", datetime.min) < datetime.now():
        raise HTTPException(status_code=404, detail="Captcha expired")
    
    # 比较用户输入和原始验证码（不区分大小写）
    if user_input.lower() == original_text.lower():
        # 验证成功后锁定会话状态
        session_store[session_id]["verified"] = True
        session_store[session_id]["verified_at"] = datetime.now()
        
        # 删除验证码相关信息，确保验证码只能使用一次
        session_store[session_id].pop("captcha_text", None)
        session_store[session_id].pop("captcha_data", None)
        session_store[session_id].pop("captcha_expire_time", None)
        
        return {"status": "success", "message": "验证码验证成功"}
    else:
        return {"status": "error", "message": "验证码无效"}

@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """
    获取指定会话的状态。
    
    参数:
        session_id (str): 会话ID。
    
    返回:
        dict: 会话状态信息，包括：
        - exists: 会话是否存在
        - expired: 会话是否已过期
        - verified: 会话是否已验证
        - has_captcha: 会话是否有未过期的验证码
    """
    # 检查会话是否存在
    if session_id not in session_store:
        return {
            "exists": False,
            "expired": True,
            "verified": False,
            "has_captcha": False
        }
    
    session_info = session_store[session_id]
    
    # 检查会话是否过期
    is_expired = session_info["expire_time"] < datetime.now()
    
    # 检查验证码是否存在且未过期
    has_captcha = (
        "captcha_text" in session_info and 
        session_info.get("captcha_expire_time", datetime.min) >= datetime.now()
    )
    
    return {
        "exists": True,
        "expired": is_expired,
        "verified": session_info.get("verified", False),
        "has_captcha": has_captcha
    }
