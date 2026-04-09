import aiohttp
from django.conf import settings

class VisionServiceClient:
    """视觉识别微服务客户端"""
    
    def __init__(self):
        self.base_url = settings.VISION_SERVICE_URL
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时

    async def detect_products(self, image_file) -> dict:
        """
        发送图像到视觉识别服务进行商品识别
        :param image_file: 图像文件对象
        :return: 识别结果
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                data = aiohttp.FormData()
                data.add_field(
                    'file',
                    image_file,
                    filename='product_image.jpg',
                    content_type='image/jpeg'
                )
                
                async with session.post(self.base_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'success': True,
                            'data': result
                        }
                    else:
                        error_msg = await response.text()
                        return {
                            'success': False,
                            'error': f"识别服务返回错误: {error_msg}",
                            'status_code': response.status
                        }
        except Exception as e:
            return {
                'success': False,
                'error': f"调用识别服务失败: {str(e)}"
            }
