"""
图片工具函数
提供图片格式转换等实用功能
"""


def image_to_data_url(img) -> str:
    """
    将 ncatbot Image 转换为 base64 data URL（供 Qwen 多模态使用）
    
    Args:
        img: ncatbot Image 对象
        
    Returns:
        base64 data URL 字符串，失败返回空字符串
    """
    try:
        raw = img.get_base64()
        if raw and raw.startswith("base64://"):
            return "data:image/jpeg;base64," + raw[len("base64://"):]
        return ""
    except Exception:
        return ""


def extract_images_from_message(msg) -> list:
    """
    从消息对象中提取并转换所有图片
    
    Args:
        msg: ncatbot GroupMessage 对象
        
    Returns:
        转换后的图片 URL 列表（过滤掉失败的）
    """
    images_raw = msg.message.filter_image()
    image_urls = [image_to_data_url(img) for img in images_raw]
    return [u for u in image_urls if u]
