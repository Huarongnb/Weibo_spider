"""
FastAPI 后端主程序
提供微博图片爬取和展示接口
"""
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from weibo_spider import WeiboSpider, extract_user_id_from_url


# Pydantic 模型定义
class UserInfo(BaseModel):
    """用户信息模型"""
    id: str 
    screen_name: str
    description: str = ""
    profile_image_url: str = ""
    cover_image_phone: str = ""
    followers_count: int = 0
    friends_count: int = 0
    statuses_count: int = 0


class ImageInfo(BaseModel):
    """图片信息模型"""
    url: str
    thumbnail: str
    pid: str
    width: int = 0
    height: int = 0


class WeiboPostInfo(BaseModel):
    """微博帖子信息模型"""
    id: str
    bid: str
    text: str
    created_at: str
    images: List[ImageInfo]
    user_id: str
    screen_name: str
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0


class CrawlRequest(BaseModel):
    """爬取请求模型"""
    user_id: Optional[str] = None
    url: Optional[str] = None
    max_pages: int = Field(default=5, ge=1, le=10, description="建议不超过5页，避免触发反爬")
    cookie: Optional[str] = None  # 可选 Cookie


class CrawlResponse(BaseModel):
    """爬取响应模型"""
    success: bool
    user_info: Optional[UserInfo] = None
    posts_count: int = 0
    images_count: int = 0
    message: str = ""


# FastAPI 应用实例
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("微博图片爬虫服务启动")
    yield
    print("微博图片爬虫服务关闭")


app = FastAPI(
    title="微博图片爬虫 API",
    description="爬取微博博主相册图片并展示",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 存储爬取结果 (简单内存存储，生产环境应使用数据库)
_cached_results = {}


@app.get("/")
async def root():
    """根路径"""
    return {"message": "微博图片爬虫 API 服务运行中", "docs": "/docs"}


@app.get("/api/user/{user_id}", response_model=UserInfo)
async def get_user_info(user_id: str):
    """
    获取微博用户信息
    Args:
        user_id: 微博用户 ID
    """
    try:
        async with WeiboSpider() as spider:
            user_info = await spider.get_user_info(user_id)
            return UserInfo(**user_info)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取用户信息失败: {str(e)}")


@app.post("/api/crawl", response_model=CrawlResponse)
async def crawl_weibo(request: CrawlRequest):
    """
    爬取微博图片
    Args:
        request: 包含 user_id 或 url，以及 max_pages 参数
    """
    # 确定用户 ID
    user_id = request.user_id
    if not user_id and request.url:
        user_id = extract_user_id_from_url(request.url)
    
    if not user_id:
        raise HTTPException(status_code=400, detail="请提供有效的 user_id 或微博主页 URL")
    
    # 调试日志
    if request.cookie:
        print(f"[DEBUG] 后端收到 Cookie: {request.cookie[:80]}...")
    else:
        print("[DEBUG] 后端未收到 Cookie")
    
    try:
        async with WeiboSpider(cookie=request.cookie) as spider:
            # 获取用户信息
            user_info = await spider.get_user_info(user_id)
            
            # 获取微博图片
            posts = await spider.get_all_images(user_id, max_pages=request.max_pages)
            
            # 统计图片数量
            images_count = sum(len(post.images) for post in posts)
            
            # 自动保存到本地
            if posts:
                save_dir = await spider.save_results(user_info, posts)
                print(f"[INFO] 结果已保存到: {save_dir}")
            
            # 缓存结果
            _cached_results[user_id] = {
                "user_info": user_info,
                "posts": posts
            }
            
            return CrawlResponse(
                success=True,
                user_info=UserInfo(**user_info),
                posts_count=len(posts),
                images_count=images_count,
                message=f"成功爬取 {len(posts)} 条微博，共 {images_count} 张图片，已保存到本地"
            )
    except Exception as e:
        return CrawlResponse(
            success=False,
            message=f"爬取失败: {str(e)}"
        )


@app.get("/api/images/{user_id}", response_model=List[WeiboPostInfo])
async def get_images(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    获取已爬取的图片列表
    Args:
        user_id: 微博用户 ID
        page: 页码
        page_size: 每页数量
    """
    if user_id not in _cached_results:
        raise HTTPException(status_code=404, detail="该用户数据尚未爬取，请先调用 /api/crawl")
    
    posts = _cached_results[user_id]["posts"]
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paginated_posts = posts[start:end]
    
    # 转换为响应模型
    result = []
    for post in paginated_posts:
        images = [ImageInfo(**img.__dict__) for img in post.images]
        result.append(WeiboPostInfo(
            id=post.id,
            bid=post.bid,
            text=post.text,
            created_at=post.created_at,
            images=images,
            user_id=post.user_id,
            screen_name=post.screen_name,
            reposts_count=post.reposts_count,
            comments_count=post.comments_count,
            attitudes_count=post.attitudes_count
        ))
    
    return result


@app.get("/api/stats/{user_id}")
async def get_stats(user_id: str):
    """
    获取爬取统计信息
    Args:
        user_id: 微博用户 ID
    """
    if user_id not in _cached_results:
        raise HTTPException(status_code=404, detail="该用户数据尚未爬取")
    
    posts = _cached_results[user_id]["posts"]
    images_count = sum(len(post.images) for post in posts)
    
    return {
        "user_id": user_id,
        "posts_count": len(posts),
        "images_count": images_count,
        "user_info": _cached_results[user_id]["user_info"]
    }


@app.post("/api/stop")
async def stop_crawl():
    """
    停止正在进行的爬取任务
    """
    WeiboSpider.stop()
    return {"message": "已发送停止信号，当前页完成后将停止爬取"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
