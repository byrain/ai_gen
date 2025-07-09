import requests
import json
import hashlib
import hmac
import uuid
import time
import random
import os
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode, quote
import binascii
from pathlib import Path

# 第三方依赖：需要安装 pip install requests crcmod
try:
    import crcmod
except ImportError:
    raise ImportError("请安装 crcmod 库: pip install crcmod")


class JimengApiClient:
    """即梦AI图像生成API客户端"""
    
    # 模型映射
    MODEL_MAP = {
        'jimeng-3.1': 'high_aes_general_v30l_art_fangzhou:general_v3.0_18b',
        'jimeng-3.0': 'high_aes_general_v30l:general_v3.0_18b',
        'jimeng-2.1': 'high_aes_general_v21_L:general_v2.1_L',
        'jimeng-2.0-pro': 'high_aes_general_v20_L:general_v2.0_L',
        'jimeng-2.0': 'high_aes_general_v20:general_v2.0',
        'jimeng-1.4': 'high_aes_general_v14:general_v1.4',
        'jimeng-xl-pro': 'text2img_xl_sft',
    }
    
    # 常量定义
    DEFAULT_MODEL = 'jimeng-3.1'
    DEFAULT_BLEND_MODEL = 'jimeng-3.0'
    DRAFT_VERSION = '3.0.2'
    DEFAULT_ASSISTANT_ID = '513695'
    
    def __init__(self, refresh_token: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            refresh_token: 刷新令牌，也可以通过环境变量 JIMENG_API_TOKEN 设置
        """
        self.refresh_token = refresh_token or os.getenv('JIMENG_API_TOKEN')
        if not self.refresh_token:
            raise ValueError('JIMENG_API_TOKEN 环境变量未设置或未提供 refresh_token')
        
        self.web_id = random.random() * 999999999999999999 + 7000000000000000000
        self.user_id = str(uuid.uuid4()).replace('-', '')
        self.upload_image_proof_url = 'https://imagex.bytedanceapi.com/'
        
        # 设置会话
        self.session = requests.Session()
        self.session.headers.update(self._get_fake_headers())
    
    def _get_fake_headers(self) -> Dict[str, str]:
        """获取伪造的请求头"""
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Last-Event-Id": "undefined",
            "Appid": self.DEFAULT_ASSISTANT_ID,
            "Appvr": "5.8.0",
            "Origin": "https://jimeng.jianying.com",
            "Pragma": "no-cache",
            "Priority": "u=1, i",
            "Referer": "https://jimeng.jianying.com",
            "Pf": "7",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
    
    def _generate_cookie(self) -> str:
        """生成Cookie"""
        timestamp = int(time.time())
        cookie_parts = [
            f"_tea_web_id={self.web_id}",
            "is_staff_user=false",
            "store-region=cn-gd",
            "store-region-src=uid",
            f"sid_guard={self.refresh_token}%7C{timestamp}%7C5184000%7CMon%2C+03-Feb-2025+08%3A17%3A09+GMT",
            f"uid_tt={self.user_id}",
            f"uid_tt_ss={self.user_id}",
            f"sid_tt={self.refresh_token}",
            f"sessionid={self.refresh_token}",
            f"sessionid_ss={self.refresh_token}",
            f"sid_tt={self.refresh_token}"
        ]
        return "; ".join(cookie_parts)
    
    def _get_model(self, model: str) -> str:
        """获取模型映射"""
        return self.MODEL_MAP.get(model, self.MODEL_MAP[self.DEFAULT_MODEL])
    
    def _generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4())
    
    def _unix_timestamp(self) -> int:
        """获取Unix时间戳"""
        return int(time.time())
    
    def _request(self, method: str, path: str, data: Optional[Dict] = None, 
                params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        发送请求到即梦API
        
        Args:
            method: 请求方法
            path: 请求路径
            data: 请求数据
            params: 请求参数
            headers: 请求头
            
        Returns:
            响应结果
        """
        base_url = 'https://jimeng.jianying.com'
        url = path if path.startswith('https://') else f"{base_url}{path}"
        
        request_headers = {
            'Cookie': self._generate_cookie(),
            **(headers or {})
        }
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params={**(data or {}), **(params or {})}, headers=request_headers)
            else:
                response = self.session.request(
                    method.lower(), 
                    url, 
                    json=data, 
                    params=params, 
                    headers=request_headers
                )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"即梦API请求失败: {str(e)}")
    
    def get_credit(self) -> Dict[str, int]:
        """
        获取积分信息
        
        Returns:
            积分信息字典
        """
        result = self._request(
            'POST',
            '/commerce/v1/benefits/user_credit',
            {},
            {},
            {'Referer': 'https://jimeng.jianying.com/ai-tool/image/generate'}
        )
        
        credit = result.get('credit', {})
        gift_credit = credit.get('gift_credit', 0)
        purchase_credit = credit.get('purchase_credit', 0)
        vip_credit = credit.get('vip_credit', 0)
        
        return {
            'gift_credit': gift_credit,
            'purchase_credit': purchase_credit,
            'vip_credit': vip_credit,
            'total_credit': gift_credit + purchase_credit + vip_credit
        }
    
    def receive_credit(self) -> None:
        """领取积分"""
        self._request(
            'POST',
            '/commerce/v1/benefits/credit_receive',
            {'time_zone': 'Asia/Shanghai'},
            {},
            {'Referer': 'https://jimeng.jianying.com/ai-tool/image/generate'}
        )
    
    def _get_file_content(self, file_path: str) -> bytes:
        """获取文件内容"""
        try:
            if file_path.startswith(('http://', 'https://')):
                # 从URL获取图片
                response = requests.get(file_path)
                response.raise_for_status()
                return response.content
            else:
                # 从本地文件获取
                with open(file_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"读取文件失败: {file_path}, 错误: {str(e)}")
    
    def _generate_random_string(self, length: int) -> str:
        """生成随机字符串"""
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choice(characters) for _ in range(length))
    
    def _get_upload_auth(self) -> Dict:
        """获取上传凭证所需Ak和Tk"""
        auth_res = self._request(
            'POST',
            '/mweb/v1/get_upload_token?aid=513695&da_version=3.2.2&aigc_features=app_lip_sync',
            {'scene': 2}
        )
        
        if not auth_res.get('data'):
            raise Exception(auth_res.get('errmsg', '获取上传凭证失败,账号可能已掉线!'))
        
        return auth_res['data']
    
    def _add_headers(self, amz_date: str, session_token: str, request_body: Dict) -> Dict:
        """生成请求所需Header"""
        headers = {
            'X-Amz-Date': amz_date,
            'X-Amz-Security-Token': session_token,
        }
        
        if request_body:
            headers['X-Amz-Content-Sha256'] = hashlib.sha256(
                json.dumps(request_body).encode('utf-8')
            ).hexdigest()
        
        return headers
    
    def _credential_string(self, amz_date: str, region: str, service: str) -> str:
        """获取credentialString"""
        credential_arr = [
            amz_date[:8],
            region,
            service,
            'aws4_request',
        ]
        return '/'.join(credential_arr)
    
    def _signed_headers(self, request_headers: Dict) -> str:
        """生成签名headers"""
        headers = [key.lower() for key in request_headers.keys()]
        return ';'.join(sorted(headers))
    
    def _canonical_string(self, request_method: str, request_params: Dict, 
                         request_headers: Dict, request_body: Dict) -> str:
        """生成canonicalString"""
        # 生成canonical headers
        canonical_headers = []
        for key in sorted(request_headers.keys()):
            canonical_headers.append(f"{key.lower()}:{request_headers[key]}")
        canonical_headers_str = '\n'.join(canonical_headers) + '\n'
        
        # 处理请求体
        body = json.dumps(request_body) if request_body else ''
        
        canonical_string_arr = [
            request_method.upper(),
            '/',
            urlencode(request_params),
            canonical_headers_str,
            self._signed_headers(request_headers),
            hashlib.sha256(body.encode('utf-8')).hexdigest(),
        ]
        
        return '\n'.join(canonical_string_arr)
    
    def _signature(self, secret_access_key: str, amz_date: str, region: str, 
                  service: str, request_method: str, request_params: Dict,
                  request_headers: Dict, request_body: Dict) -> str:
        """生成签名"""
        # 生成signingKey
        amz_day = amz_date[:8]
        k_date = hmac.new(
            f'AWS4{secret_access_key}'.encode('utf-8'),
            amz_day.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        k_region = hmac.new(k_date, region.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode('utf-8'), hashlib.sha256).digest()
        signing_key = hmac.new(k_service, 'aws4_request'.encode('utf-8'), hashlib.sha256).digest()
        
        # 生成StringToSign
        string_to_sign_arr = [
            'AWS4-HMAC-SHA256',
            amz_date,
            self._credential_string(amz_date, region, service),
            hashlib.sha256(
                self._canonical_string(request_method, request_params, request_headers, request_body).encode('utf-8')
            ).hexdigest(),
        ]
        string_to_sign = '\n'.join(string_to_sign_arr)
        
        return hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    def _generate_authorization_and_header(self, access_key_id: str, secret_access_key: str,
                                         session_token: str, region: str, service: str,
                                         request_method: str, request_params: Dict,
                                         request_body: Dict = None) -> Dict:
        """生成请求所需Header和Authorization"""
        # 获取当前ISO时间
        now = time.gmtime()
        amz_date = time.strftime('%Y%m%dT%H%M%SZ', now)
        
        if request_body is None:
            request_body = {}
        
        # 生成请求的Header
        request_headers = self._add_headers(amz_date, session_token, request_body)
        
        # 生成Authorization
        authorization_params = [
            f'AWS4-HMAC-SHA256 Credential={access_key_id}/{self._credential_string(amz_date, region, service)}',
            f'SignedHeaders={self._signed_headers(request_headers)}',
            f'Signature={self._signature(secret_access_key, amz_date, region, service, request_method, request_params, request_headers, request_body)}',
        ]
        authorization = ', '.join(authorization_params)
        
        # 返回Headers
        headers = dict(request_headers)
        headers['Authorization'] = authorization
        return headers
    
    def _upload_cover_file(self, file_path: str) -> str:
        """上传封面文件"""
        try:
            # 获取上传令牌所需Ak和Tk
            upload_auth = self._get_upload_auth()
            
            # 获取图片数据
            image_data = self._get_file_content(file_path)
            
            # 计算CRC32
            crc32_func = crcmod.mkCrcFun(0x104c11db7, initCrc=0, xorOut=0xFFFFFFFF)
            image_crc32 = hex(crc32_func(image_data))[2:]
            
            # 获取图片上传凭证签名所需参数
            get_upload_image_proof_request_params = {
                'Action': 'ApplyImageUpload',
                'FileSize': len(image_data),
                'ServiceId': 'tb4s082cfz',
                'Version': '2018-08-01',
                's': self._generate_random_string(11),
            }
            
            # 获取图片上传请求头
            request_headers_info = self._generate_authorization_and_header(
                upload_auth['access_key_id'],
                upload_auth['secret_access_key'],
                upload_auth['session_token'],
                'cn-north-1',
                'imagex',
                'GET',
                get_upload_image_proof_request_params,
            )
            
            # 获取图片上传凭证
            upload_img_res = self._request(
                'GET',
                f"{self.upload_image_proof_url}?{urlencode(get_upload_image_proof_request_params)}",
                {},
                {},
                request_headers_info
            )
            
            if 'Response' in upload_img_res and 'Error' in upload_img_res['Response']:
                raise Exception(upload_img_res['Response']['Error']['Message'])
            
            upload_address = upload_img_res['Result']['UploadAddress']
            
            # 用凭证拼接上传图片接口
            upload_img_url = f"https://{upload_address['UploadHosts'][0]}/upload/v1/{upload_address['StoreInfos'][0]['StoreUri']}"
            
            # 上传图片
            upload_headers = {
                'Authorization': upload_address['StoreInfos'][0]['Auth'],
                'Content-Crc32': image_crc32,
                'Content-Type': 'application/octet-stream',
            }
            
            response = requests.post(upload_img_url, data=image_data, headers=upload_headers)
            image_upload_res = response.json()
            
            if image_upload_res.get('code') != 2000:
                raise Exception(image_upload_res.get('message', '上传失败'))
            
            # 提交图片上传
            commit_img_params = {
                'Action': 'CommitImageUpload',
                'FileSize': len(image_data),
                'ServiceId': 'tb4s082cfz',
                'Version': '2018-08-01',
            }
            
            commit_img_content = {
                'SessionKey': upload_address['SessionKey'],
            }
            
            commit_img_head = self._generate_authorization_and_header(
                upload_auth['access_key_id'],
                upload_auth['secret_access_key'],
                upload_auth['session_token'],
                'cn-north-1',
                'imagex',
                'POST',
                commit_img_params,
                commit_img_content,
            )
            
            commit_img_head['Content-Type'] = 'application/json'
            
            # 提交图片上传
            commit_img = self._request(
                'POST',
                f"{self.upload_image_proof_url}?{urlencode(commit_img_params)}",
                commit_img_content,
                {},
                commit_img_head
            )
            
            if 'Response' in commit_img and 'Error' in commit_img['Response']:
                raise Exception(commit_img['Response']['Error']['Message'])
            
            return commit_img['Result']['Results'][0]['Uri']
            
        except Exception as e:
            raise Exception(f"上传文件失败: {str(e)}")
    
    def generate_image(self, prompt: str, file_path: Optional[str] = None,
                      model: Optional[str] = None, width: int = 1024, height: int = 1024,
                      sample_strength: float = 0.5, negative_prompt: str = "") -> List[str]:
        """
        生成图像
        
        Args:
            prompt: 提示词
            file_path: 参考图片路径（可选）
            model: 模型名称
            width: 图像宽度
            height: 图像高度
            sample_strength: 精细度
            negative_prompt: 反向提示词
            
        Returns:
            生成的图像URL列表
        """
        if not prompt or not isinstance(prompt, str):
            raise ValueError('prompt必须是非空字符串')
        
        has_file_path = bool(file_path)
        upload_id = None
        
        if has_file_path:
            upload_id = self._upload_cover_file(file_path)
        
        # 获取实际模型
        model_name = self.DEFAULT_BLEND_MODEL if has_file_path else (model or self.DEFAULT_MODEL)
        actual_model = self._get_model(model_name)
        
        # 检查积分
        credit_info = self.get_credit()
        if credit_info['total_credit'] <= 0:
            self.receive_credit()
        
        # 生成组件ID
        component_id = self._generate_uuid()
        
        # 构建请求参数
        rq_params = {
            "babi_param": quote(json.dumps({
                "scenario": "image_video_generation",
                "feature_key": "to_image_referenceimage_generate" if has_file_path else "aigc_to_image",
                "feature_entrance": "to_image",
                "feature_entrance_detail": f"to_image-referenceimage-byte_edit" if has_file_path else f"to_image-{actual_model}",
            })),
            "aid": int(self.DEFAULT_ASSISTANT_ID),
            "device_platform": "web",
            "region": "CN",
            "web_id": int(self.web_id)
        }
        
        # 构建能力参数
        if has_file_path:
            abilities = {
                "blend": {
                    "type": "",
                    "id": self._generate_uuid(),
                    "min_features": [],
                    "core_param": {
                        "type": "",
                        "id": self._generate_uuid(),
                        "model": actual_model,
                        "prompt": prompt + '##',
                        "sample_strength": sample_strength,
                        "image_ratio": 1,
                        "large_image_info": {
                            "type": "",
                            "id": self._generate_uuid(),
                            "height": 1360,
                            "width": 1360,
                            "resolution_type": '1k'
                        }
                    },
                    "ability_list": [
                        {
                            "type": "",
                            "id": self._generate_uuid(),
                            "name": "byte_edit",
                            "image_uri_list": [upload_id],
                            "image_list": [
                                {
                                    "type": "image",
                                    "id": self._generate_uuid(),
                                    "source_from": "upload",
                                    "platform_type": 1,
                                    "name": "",
                                    "image_uri": upload_id,
                                    "width": 0,
                                    "height": 0,
                                    "format": "",
                                    "uri": upload_id
                                }
                            ],
                            "strength": 0.5
                        }
                    ],
                    "history_option": {
                        "type": "",
                        "id": self._generate_uuid(),
                    },
                    "prompt_placeholder_info_list": [
                        {
                            "type": "",
                            "id": self._generate_uuid(),
                            "ability_index": 0
                        }
                    ],
                    "postedit_param": {
                        "type": "",
                        "id": self._generate_uuid(),
                        "generate_type": 0
                    }
                }
            }
        else:
            abilities = {
                "generate": {
                    "type": "",
                    "id": self._generate_uuid(),
                    "core_param": {
                        "type": "",
                        "id": self._generate_uuid(),
                        "model": actual_model,
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "seed": random.randint(2500000000, 2600000000),
                        "sample_strength": sample_strength,
                        "image_ratio": 1,
                        "large_image_info": {
                            "type": "",
                            "id": self._generate_uuid(),
                            "height": height,
                            "width": width,
                            "resolution_type": '1k'
                        }
                    },
                    "history_option": {
                        "type": "",
                        "id": self._generate_uuid(),
                    }
                }
            }
        
        # 构建请求数据
        rq_data = {
            "extend": {
                "root_model": actual_model,
                "template_id": "",
            },
            "submit_id": self._generate_uuid(),
            "draft_content": json.dumps({
                "type": "draft",
                "id": self._generate_uuid(),
                "min_version": self.DRAFT_VERSION,
                "is_from_tsn": True,
                "version": "3.2.2",
                "main_component_id": component_id,
                "component_list": [{
                    "type": "image_base_component",
                    "id": component_id,
                    "min_version": self.DRAFT_VERSION,
                    "metadata": {
                        "type": "",
                        "id": self._generate_uuid(),
                        "created_platform": 3,
                        "created_platform_version": "",
                        "created_time_in_ms": int(time.time() * 1000),
                        "created_did": ""
                    },
                    "generate_type": "blend" if has_file_path else "generate",
                    "aigc_mode": "workbench",
                    "abilities": {
                        "type": "",
                        "id": self._generate_uuid(),
                        **abilities
                    }
                }]
            }),
        }
        
        # 添加metrics_extra（仅限非混合模式）
        if not has_file_path:
            rq_data["metrics_extra"] = json.dumps({
                "templateId": "",
                "generateCount": 1,
                "promptSource": "custom",
                "templateSource": "",
                "lastRequestId": "",
                "originRequestId": "",
            })
        
        # 发送生成请求
        result = self._request('POST', '/mweb/v1/aigc_draft/generate', rq_data, rq_params)
        
        # 获取历史记录ID
        history_id = result.get('data', {}).get('aigc_data', {}).get('history_record_id')
        if not history_id:
            error_msg = result.get('errmsg', '记录ID不存在')
            raise Exception(error_msg)
        
        # 轮询获取结果
        status = 20
        fail_code = None
        item_list = []
        
        while status == 20:
            time.sleep(1)
            
            result = self._request('POST', '/mweb/v1/get_history_by_ids', {
                "history_ids": [history_id],
                "image_info": {
                    "width": 2048,
                    "height": 2048,
                    "format": "webp",
                    "image_scene_list": [
                        {"scene": "smart_crop", "width": 360, "height": 360, "uniq_key": "smart_crop-w:360-h:360", "format": "webp"},
                        {"scene": "smart_crop", "width": 480, "height": 480, "uniq_key": "smart_crop-w:480-h:480", "format": "webp"},
                        {"scene": "smart_crop", "width": 720, "height": 720, "uniq_key": "smart_crop-w:720-h:720", "format": "webp"},
                        {"scene": "smart_crop", "width": 720, "height": 480, "uniq_key": "smart_crop-w:720-h:480", "format": "webp"},
                        {"scene": "smart_crop", "width": 360, "height": 240, "uniq_key": "smart_crop-w:360-h:240", "format": "webp"},
                        {"scene": "smart_crop", "width": 240, "height": 320, "uniq_key": "smart_crop-w:240-h:320", "format": "webp"},
                        {"scene": "smart_crop", "width": 480, "height": 640, "uniq_key": "smart_crop-w:480-h:640", "format": "webp"},
                        {"scene": "normal", "width": 2400, "height": 2400, "uniq_key": "2400", "format": "webp"},
                        {"scene": "normal", "width": 1080, "height": 1080, "uniq_key": "1080", "format": "webp"},
                        {"scene": "normal", "width": 720, "height": 720, "uniq_key": "720", "format": "webp"},
                        {"scene": "normal", "width": 480, "height": 480, "uniq_key": "480", "format": "webp"},
                        {"scene": "normal", "width": 360, "height": 360, "uniq_key": "360", "format": "webp"}
                    ]
                },
                "http_common_info": {
                    "aid": int(self.DEFAULT_ASSISTANT_ID)
                }
            })
            
            record = result.get('data', {}).get(history_id)
            if not record:
                raise Exception('记录不存在')
            
            status = record.get('status')
            fail_code = record.get('fail_code')
            item_list = record.get('item_list', [])
            
            if status == 30:
                if fail_code == '2038':
                    raise Exception('内容被过滤')
                raise Exception('图像生成失败')
        
        # 提取图片URL
        image_urls = []
        for item in item_list:
            image_url = None
            if item.get('image', {}).get('large_images'):
                image_url = item['image']['large_images'][0].get('image_url')
            elif item.get('common_attr', {}).get('cover_url'):
                image_url = item['common_attr']['cover_url']
            
            if image_url:
                image_urls.append(image_url)
        
        return image_urls


# 使用示例
if __name__ == "__main__":
    # 设置你的refresh_token
    IMENG_API_TOKEN = "xxxxx"
    r = JimengApiClient(refresh_token=IMENG_API_TOKEN)
    image_urls = r.generate_image("可爱的小狗",file_path="01.jpeg")
    print(image_urls)
