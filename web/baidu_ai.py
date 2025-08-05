import requests
import json

# 从你的TabsManager中获取的cookie字典
cookies = {
    "BDUSS": "你获取到的BDUSS值",
    "BAIDUID": "你获取到的BAIDUID值",
    "BIDUPSID": "你获取到的BIDUPSID值",
    "PSTM": "你获取到的PSTM值",
    # 其他可能需要的cookie...
}

def remove_background(image_path):
    # 上传图片的URL（你需要通过抓包确定具体的API端点）
    upload_url = "https://image.baidu.com/search/acjson"
    
    # 准备文件和表单数据
    files = {
        'file': open(image_path, 'rb')
    }
    
    # 准备请求头，模拟浏览器行为
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://image.baidu.com/search/index"
    }
    
    # 发送请求
    response = requests.post(upload_url, files=files, cookies=cookies, headers=headers)
    
    # 处理响应
    if response.status_code == 200:
        result = response.json()
        # 解析结果并下载处理后的图片
        # 具体的解析逻辑取决于API的响应格式
        print("处理成功!")
        return result
    else:
        print(f"请求失败: {response.status_code}")
        return None

# 使用函数
result = remove_background("your_image.jpg")

