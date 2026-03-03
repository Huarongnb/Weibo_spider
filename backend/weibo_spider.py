"""
微博爬虫核心模块
功能: 通过微博移动端 API 获取博主微博中的图片
修复: HTTP 432 反爬错误处理
"""
import re
import json
import asyncio
import random
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlencode

import httpx
import aiofiles


def parse_count(value: Any) -> int:
    """
    解析微博关注数/粉丝数字符串（支持 '775万' 格式）
    Args:
        value: 原始值（可能是数字或带单位的字符串）
    Returns:
        解析后的整数
    """
    if value is None:
        return 0
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        
        # 处理 "775万" 格式
        if '万' in value:
            try:
                num = float(value.replace('万', '').strip())
                return int(num * 10000)
            except (ValueError, TypeError):
                return 0
        
        # 处理普通数字
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    return 0


@dataclass
class WeiboImage:
    """微博图片数据结构"""
    url: str
    thumbnail: str
    pid: str
    width: int = 0
    height: int = 0


@dataclass
class WeiboPost:
    """微博帖子数据结构"""
    id: str
    bid: str
    text: str
    created_at: str
    images: List[WeiboImage]
    user_id: str
    screen_name: str
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0


class WeiboSpider:
    """微博爬虫类 - 增强反爬处理能力，支持停止"""
    
    # 类级别的停止标志
    _should_stop = False
    
    # 微博移动端 API 基础 URL
    BASE_URL = "https://m.weibo.cn"
    
    # 随机 User-Agent 列表
    USER_AGENTS = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, cookie: Optional[str] = None):
        """
        初始化爬虫
        Args:
            cookie: 微博登录 cookie，可选。如需爬取大量数据，建议提供登录后的 cookie
        """
        self.cookie = cookie
        self.headers = self._build_headers()
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头 - 模拟真实浏览器"""
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
            "Referer": "https://m.weibo.cn/",
        }
        
        if self.cookie:
            headers["Cookie"] = self.cookie
            
        return headers
    
    def _rotate_user_agent(self):
        """轮换 User-Agent"""
        self.headers["User-Agent"] = random.choice(self.USER_AGENTS)
        if self.client:
            self.client.headers["User-Agent"] = self.headers["User-Agent"]
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 打印调试信息
        if self.cookie:
            print(f"[DEBUG] 使用 Cookie 长度: {len(self.cookie)} 字符")
            print(f"[DEBUG] Cookie 前50字符: {self.cookie[:50]}...")
        else:
            print("[DEBUG] 未使用 Cookie")
        
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            http1=True,
            http2=False,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.aclose()
    
    async def _get_with_retry(
        self, 
        url: str, 
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        发送 GET 请求（带重试机制）
        Args:
            url: 请求 URL
            params: 请求参数
            max_retries: 最大重试次数
        Returns:
            JSON 响应数据
        """
        if not self.client:
            raise RuntimeError("Spider not initialized. Use 'async with' context manager.")
        
        for attempt in range(max_retries):
            try:
                # 增加请求间隔，随机延迟 1-3 秒
                if self.request_count > 0:
                    delay = random.uniform(1.0, 3.0)
                    await asyncio.sleep(delay)
                
                self.request_count += 1
                
                # 每 5 个请求轮换一次 User-Agent
                if self.request_count % 5 == 0:
                    self._rotate_user_agent()
                
                response = await self.client.get(url, params=params)
                
                # 处理 432 错误
                if response.status_code == 432:
                    print(f"检测到反爬限制 (432)，等待后重试... (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(random.uniform(5.0, 10.0))  # 更长的等待
                    self._rotate_user_agent()
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 432 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 指数退避
                    print(f"HTTP 432 错误，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    self._rotate_user_agent()
                else:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"请求失败: {e}，{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"达到最大重试次数 ({max_retries})，请求仍失败")
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户信息
        Args:
            user_id: 微博用户 ID
        Returns:
            用户信息字典
        """
        url = f"{self.BASE_URL}/api/container/getIndex"
        params = {
            "type": "uid",
            "value": user_id,
            "containerid": f"100505{user_id}"
        }
        data = await self._get_with_retry(url, params)
        
        if data.get("ok") != 1:
            error_msg = data.get('msg', 'Unknown error')
            # 打印完整响应用于诊断
            print(f"[DEBUG] API 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if "访客过多" in error_msg or "登录" in error_msg or "身份" in error_msg:
                raise ValueError(f"需要登录才能访问该用户: {error_msg}")
            if not error_msg or error_msg == 'Unknown error':
                # 检查是否有重定向到登录页
                if data.get('url') and 'passport.weibo.com' in data.get('url', ''):
                    raise ValueError(f"Cookie 无效或已过期: 请重新登录微博获取完整 Cookie（必须包含 SUB 和 SUBP 字段）")
                raise ValueError(f"获取用户信息失败: 用户ID可能不存在 (ok={data.get('ok')})")
            raise ValueError(f"获取用户信息失败: {error_msg}")
        
        user_info = data.get("data", {}).get("userInfo", {})
        return {
            "id": str(user_info.get("id", "")),
            "screen_name": user_info.get("screen_name", ""),
            "description": user_info.get("description", ""),
            "profile_image_url": user_info.get("profile_image_url", ""),
            "cover_image_phone": user_info.get("cover_image_phone", ""),
            "followers_count": parse_count(user_info.get("followers_count", 0)),
            "friends_count": parse_count(user_info.get("friends_count", 0)),
            "statuses_count": parse_count(user_info.get("statuses_count", 0)),
        }
    
    def _parse_images(self, pics: List[Dict]) -> List[WeiboImage]:
        """解析图片数据"""
        images = []
        for pic in pics:
            large_url = pic.get("large", {}).get("url", "")
            if not large_url:
                large_url = pic.get("url", "")
            
            thumbnail = pic.get("url", "")
            
            if large_url:
                images.append(WeiboImage(
                    url=large_url,
                    thumbnail=thumbnail,
                    pid=pic.get("pid", ""),
                    width=pic.get("large", {}).get("geo", {}).get("width", 0),
                    height=pic.get("large", {}).get("geo", {}).get("height", 0)
                ))
        return images
    
    async def get_user_weibos(
        self, 
        user_id: str, 
        page: int = 1, 
        feature: int = 0
    ) -> List[WeiboPost]:
        """
        获取用户微博列表
        Args:
            user_id: 微博用户 ID
            page: 页码
            feature: 过滤类型 (0:全部, 1:原创, 2:图片, 3:视频, 4:音乐)
        Returns:
            WeiboPost 对象列表
        """
        url = f"{self.BASE_URL}/api/container/getIndex"
        params = {
            "type": "uid",
            "value": user_id,
            "containerid": f"107603{user_id}",
            "page": page,
            "feature": feature
        }
        
        data = await self._get_with_retry(url, params)
        
        if data.get("ok") != 1:
            error_msg = data.get('msg', 'Unknown error')
            raise ValueError(f"获取微博列表失败: {error_msg}")
        
        cards = data.get("data", {}).get("cards", [])
        posts = []
        
        for card in cards:
            if card.get("card_type") != 9:
                continue
            
            mblog = card.get("mblog", {})
            if not mblog:
                continue
            
            pics = mblog.get("pics", [])
            if not pics:
                continue
            
            images = self._parse_images(pics)
            if not images:
                continue
            
            user = mblog.get("user", {})
            
            post = WeiboPost(
                id=str(mblog.get("id", "")),
                bid=mblog.get("bid", ""),
                text=mblog.get("text", ""),
                created_at=mblog.get("created_at", ""),
                images=images,
                user_id=str(user.get("id", "")),
                screen_name=user.get("screen_name", ""),
                reposts_count=mblog.get("reposts_count", 0),
                comments_count=mblog.get("comments_count", 0),
                attitudes_count=mblog.get("attitudes_count", 0)
            )
            posts.append(post)
        
        return posts
    
    async def get_all_images(
        self, 
        user_id: str, 
        max_pages: int = 5,
        on_progress: Optional[callable] = None
    ) -> List[WeiboPost]:
        """
        获取用户所有带图片的微博（支持停止）
        Args:
            user_id: 微博用户 ID
            max_pages: 最大抓取页数
            on_progress: 进度回调函数 (current_page, total_posts)
        Returns:
            所有包含图片的微博列表
        """
        all_posts = []
        
        for page in range(1, max_pages + 1):
            # 检查是否被要求停止
            if WeiboSpider._should_stop:
                print(f"[INFO] 爬取被用户停止，已获取 {len(all_posts)} 条微博")
                WeiboSpider._should_stop = False  # 重置标志
                break
            
            try:
                posts = await self.get_user_weibos(user_id, page=page, feature=2)
                if not posts:
                    break
                all_posts.extend(posts)
                
                # 调用进度回调
                if on_progress:
                    on_progress(page, len(all_posts))
                
                print(f"已获取第 {page} 页，共 {len(posts)} 条微博，总计 {len(all_posts)} 条")
                
                # 每页之间增加随机延迟
                if page < max_pages:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    
            except Exception as e:
                print(f"获取第 {page} 页失败: {e}")
                break
        
        return all_posts
    
    @classmethod
    def stop(cls):
        """停止爬取"""
        cls._should_stop = True
        print("[INFO] 已发送停止信号")
    
    @classmethod
    def reset_stop(cls):
        """重置停止标志"""
        cls._should_stop = False
    
    async def save_results(
        self,
        user_info: Dict[str, Any],
        posts: List[WeiboPost],
        base_dir: str = r"C:\Cursor\codes\finalspider",
        download_images: bool = True
    ) -> str:
        """
        保存爬取结果到本地
        Args:
            user_info: 用户信息
            posts: 微博帖子列表
            base_dir: 保存基础目录
            download_images: 是否下载图片
        Returns:
            保存目录路径
        """
        # 创建日期命名的目录
        today = datetime.now().strftime("%Y-%m-%d")
        user_name = user_info.get('screen_name', 'unknown')
        save_dir = os.path.join(base_dir, f"{today}_{user_name}_{user_info['id']}")
        
        # 创建目录
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(os.path.join(save_dir, "images"), exist_ok=True)
        
        print(f"\n📁 保存目录: {save_dir}")
        
        # 准备元数据
        metadata = {
            "user_info": user_info,
            "crawl_time": datetime.now().isoformat(),
            "posts_count": len(posts),
            "images_count": sum(len(post.images) for post in posts),
            "posts": []
        }
        
        # 下载图片并保存元数据
        for i, post in enumerate(posts):
            post_data = {
                "id": post.id,
                "bid": post.bid,
                "text": post.text,
                "created_at": post.created_at,
                "user_id": post.user_id,
                "screen_name": post.screen_name,
                "reposts_count": post.reposts_count,
                "comments_count": post.comments_count,
                "attitudes_count": post.attitudes_count,
                "images": []
            }
            
            for j, img in enumerate(post.images):
                img_filename = f"{post.id}_{j+1}_{img.pid}.jpg"
                local_path = os.path.join("images", img_filename)
                
                img_data = {
                    "pid": img.pid,
                    "url": img.url,
                    "thumbnail": img.thumbnail,
                    "width": img.width,
                    "height": img.height,
                    "local_path": local_path
                }
                post_data["images"].append(img_data)
                
                # 下载图片
                if download_images and self.client:
                    try:
                        img_response = await self.client.get(img.url, timeout=30.0)
                        img_response.raise_for_status()
                        
                        full_path = os.path.join(save_dir, local_path)
                        async with aiofiles.open(full_path, 'wb') as f:
                            await f.write(img_response.content)
                        
                        print(f"  ✅ 已保存图片: {img_filename}")
                        
                        # 添加延迟避免请求过快
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        print(f"  ❌ 下载图片失败 {img_filename}: {e}")
            
            metadata["posts"].append(post_data)
            
            # 每5条微博显示一次进度
            if (i + 1) % 5 == 0:
                print(f"📊 已处理 {i + 1}/{len(posts)} 条微博")
        
        # 保存元数据 JSON
        metadata_path = os.path.join(save_dir, "metadata.json")
        async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
        
        print(f"\n✅ 保存完成!")
        print(f"   📄 元数据: {metadata_path}")
        print(f"   🖼️ 图片目录: {os.path.join(save_dir, 'images')}")
        print(f"   📊 总计: {metadata['posts_count']} 条微博, {metadata['images_count']} 张图片")
        
        return save_dir


def extract_user_id_from_url(url: str) -> Optional[str]:
    """从微博 URL 中提取用户 ID"""
    patterns = [
        r"weibo\.com/u/(\d+)",
        r"weibo\.com/([\w\d]+)",  # 支持昵称链接
        r"m\.weibo\.cn/u/(\d+)",
        r"m\.weibo\.cn/profile/(\d+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # 如果 URL 是纯数字，直接返回
    if url.isdigit():
        return url
    
    return None


# 测试代码
async def test_spider():
    """测试爬虫功能"""
    test_user_id = "1669879400"  # 使用用户提供的 UID 测试
    
    print("=" * 50)
    print("微博图片爬虫测试")
    print("=" * 50)
    
    async with WeiboSpider() as spider:
        try:
            print(f"\n正在获取用户 {test_user_id} 的信息...")
            user_info = await spider.get_user_info(test_user_id)
            print(f"✅ 用户名: {user_info['screen_name']}")
            print(f"   微博数: {user_info['statuses_count']}")
            
            print(f"\n正在获取微博列表（最多 3 页）...")
            posts = await spider.get_all_images(test_user_id, max_pages=3)
            
            total_images = sum(len(post.images) for post in posts)
            print(f"\n✅ 共获取 {len(posts)} 条带图片的微博")
            print(f"   总图片数: {total_images}")
            
            if posts:
                print("\n前 3 条微博预览:")
                for i, post in enumerate(posts[:3], 1):
                    print(f"\n{i}. 微博 ID: {post.id}")
                    print(f"   发布时间: {post.created_at}")
                    print(f"   图片数: {len(post.images)}")
                    print(f"   首图: {post.images[0].url[:60]}...")
                    
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            print("\n建议：")
            print("1. 检查网络连接")
            print("2. 减少 max_pages 参数")
            print("3. 添加登录 Cookie 后再试")


if __name__ == "__main__":
    asyncio.run(test_spider())
