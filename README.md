# 微博相册浏览器 (Weibo Photo Browser)

**微博相册浏览器** 是一款专为高效获取与优雅展示微博博主图片而设计的全栈应用。它通过集成 FastAPI 后端与 React + TailwindCSS 前端，为用户提供了一个沉浸式、无干扰的图片浏览环境。

### 核心价值
在信息碎片化的社交时代，本项目旨在通过简单的用户 ID 或主页链接，自动抓取并解析博主相册中的公开原图，并以现代感十足的瀑布流形式进行展示。无论是摄影爱好者收集素材，还是粉丝回顾偶像瞬间，都能通过本项目获得极速且纯净的视觉体验。

### 关键特性
- **极简操作**：支持直接输入微博用户 ID 或主页 URL。
- **智能爬取**：基于微博移动端 API，稳定抓取高清原图。
- **现代 UI**：响应式瀑布流布局，完美适配桌面与移动端。
- **无感加载**：分页技术确保在大规模图片库下依然保持丝滑体验。

---

## 技术栈

- **后端**: Python + FastAPI + httpx
- **前端**: React + TypeScript + TailwindCSS + Vite
- **爬虫**: 微博移动端 API (m.weibo.cn)

## 项目结构

```
finalspider/
├── backend/
│   ├── requirements.txt      # Python 依赖
│   ├── weibo_spider.py      # 爬虫核心逻辑
│   └── main.py              # FastAPI 后端服务
├── frontend/
│   ├── package.json         # Node.js 依赖
│   ├── src/
│   │   ├── App.tsx          # 主应用组件
│   │   ├── components/      # UI 组件
│   │   │   ├── UserCard.tsx     # 用户信息卡片
│   │   │   └── ImageGallery.tsx # 图片画廊
│   │   └── main.tsx         # 入口文件
│   └── ...                  # 配置文件
└── README.md
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python main.py
```

后端服务将在 http://localhost:8000 启动，API 文档可在 http://localhost:8000/docs 查看。

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 启动。

## 使用方法

1. 打开浏览器访问 http://localhost:3000
2. 在搜索框中输入微博用户 ID 或主页链接，例如：
   - 用户 ID: `2803301701`
   - 主页链接: `https://weibo.com/u/2803301701`
3. 点击"开始爬取"按钮
4. 等待爬取完成后，即可浏览该博主的所有公开图片

## API 接口

### 爬取微博图片
```http
POST /api/crawl
Content-Type: application/json

{
  "user_id": "2803301701",
  "max_pages": 10
}
```

### 获取图片列表
```http
GET /api/images/{user_id}?page=1&page_size=20
```

### 获取用户信息
```http
GET /api/user/{user_id}
```

## 注意事项

1. **反爬机制**: 微博有反爬虫机制，频繁请求可能导致 IP 被临时封禁。建议：
   - 控制爬取频率（代码中已设置 0.5 秒间隔）
   - 限制爬取页数（默认 10 页）
   - 如需大规模爬取，建议添加代理池或登录 Cookie

2. **版权问题**: 爬取的图片仅用于个人学习研究，请勿用于商业用途。

3. **图片加载**: 图片直接引用微博 CDN 链接，如果链接失效可能无法显示。

## 功能特性

- ✅ 支持通过用户 ID 或主页链接爬取
- ✅ 自动提取带图片的微博
- ✅ 瀑布流展示图片
- ✅ 灯箱查看大图
- ✅ 图片下载功能
- ✅ 分页加载
- ✅ 响应式设计

## 开发计划

- [ ] 添加 Cookie 登录支持（用于抓取更多内容）
- [ ] 图片本地缓存
- [ ] 批量下载功能
- [ ] 视频下载支持
- [ ] 数据持久化（SQLite/PostgreSQL）

## License

MIT License
