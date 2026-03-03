import React, { useState, useRef } from 'react'
import { Search, Loader2, Image as ImageIcon, User, AlertCircle, Square, FolderOpen } from 'lucide-react'
import axios from 'axios'
import ImageGallery from './components/ImageGallery'
import UserCard from './components/UserCard'

// API 基础 URL
const API_BASE_URL = 'http://localhost:8000'

// 类型定义
interface UserInfo {
  id: string
  screen_name: string
  description: string
  profile_image_url: string
  cover_image_phone: string
  followers_count: number
  friends_count: number
  statuses_count: number
}

interface ImageData {
  pid: string
  url: string
  thumbnail: string
  width: number
  height: number
  local_path: string
}

interface WeiboPost {
  id: string
  bid: string
  text: string
  created_at: string
  user_id: string
  screen_name: string
  reposts_count: number
  comments_count: number
  attitudes_count: number
  images: ImageData[]
}

interface CrawlResponse {
  success: boolean
  user_info?: UserInfo
  posts_count: number
  images_count: number
  message: string
}

function App() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [crawlResult, setCrawlResult] = useState<CrawlResponse | null>(null)
  const [userId, setUserId] = useState('')
  const [cookie, setCookie] = useState('')
  const [isCrawling, setIsCrawling] = useState(false)  // 爬取中状态
  const [localPosts, setLocalPosts] = useState<WeiboPost[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    setLoading(true)
    setIsCrawling(true)
    setError('')
    setCrawlResult(null)
    setLocalPosts([])

    try {
      const isUrl = input.includes('weibo.com') || input.includes('m.weibo.cn')
      
      const requestBody = isUrl 
        ? { url: input, max_pages: 3, cookie: cookie || undefined }  // 默认改为3页
        : { user_id: input, max_pages: 3, cookie: cookie || undefined }

      const response = await axios.post<CrawlResponse>(
        `${API_BASE_URL}/api/crawl`,
        requestBody
      )

      setCrawlResult(response.data)
      
      if (response.data.success && response.data.user_info) {
        setUserId(response.data.user_info.id)
      } else {
        setError(response.data.message)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '请求失败，请检查网络连接')
    } finally {
      setLoading(false)
      setIsCrawling(false)
    }
  }

  const handleStop = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/stop`)
      setIsCrawling(false)
      setLoading(false)
    } catch (err) {
      console.error('停止失败:', err)
    }
  }

  // 处理选择本地目录
  const handleSelectDirectory = () => {
    fileInputRef.current?.click()
  }

  // 读取本地目录文件
  const handleDirectoryChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setLoading(true)
    setError('')
    setCrawlResult(null)
    setLocalPosts([])

    try {
      // 查找 metadata.json 文件
      let metadataFile: File | null = null

      for (const file of Array.from(files)) {
        if (file.name === 'metadata.json') {
          metadataFile = file
          break
        }
      }

      if (!metadataFile) {
        throw new Error('未找到 metadata.json 文件，请确保选择的是正确的下载目录')
      }

      // 读取并解析 metadata.json
      const content = await metadataFile.text()
      const metadata = JSON.parse(content)

      if (!metadata.user_info || !metadata.posts) {
        throw new Error('metadata.json 格式不正确')
      }

      setLocalPosts(metadata.posts)
      setUserId(metadata.user_info.id)

      // 模拟一个成功的 crawlResult
      setCrawlResult({
        success: true,
        user_info: metadata.user_info,
        posts_count: metadata.posts_count || metadata.posts.length,
        images_count: metadata.images_count || metadata.posts.reduce((sum: number, post: WeiboPost) => sum + post.images.length, 0),
        message: '已从本地目录加载数据'
      })
    } catch (err: any) {
      setError(err.message || '读取本地目录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-8 h-8 text-red-500" />
            <h1 className="text-xl font-bold text-gray-800">微博相册浏览器</h1>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* 搜索区域 */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          {/* 模式切换 */}
          <div className="flex gap-4 mb-4">
            <h2 className="text-lg font-semibold text-gray-700 flex-1">
              输入微博用户 ID 或主页链接
            </h2>
            <input
              ref={fileInputRef}
              type="file"
              // @ts-ignore - webkitdirectory 是浏览器原生属性
              webkitdirectory=""
              directory=""
              multiple
              onChange={handleDirectoryChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={handleSelectDirectory}
              disabled={loading}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 flex items-center gap-2 transition-colors text-sm"
            >
              <FolderOpen className="w-4 h-4" />
              选择本地目录
            </button>
          </div>
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="例如: 2803301701 或 https://weibo.com/u/2803301701"
                className="w-full px-4 py-3 pl-11 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              />
              <User className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  爬取中...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  开始爬取
                </>
              )}
            </button>
            {isCrawling && (
              <button
                type="button"
                onClick={handleStop}
                className="px-4 py-3 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600 flex items-center gap-2 transition-colors"
              >
                <Square className="w-5 h-5" />
                停止
              </button>
            )}
          </form>
          
          {/* Cookie 输入框 */}
          <div className="mt-3">
            <input
              type="text"
              value={cookie}
              onChange={(e) => setCookie(e.target.value)}
              placeholder="Cookie（可选，用于解决反爬问题，格式：SUB=xxx;SUBP=xxx）"
              className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-400">
              提示：如遇到爬取失败，可登录微博后通过浏览器开发者工具复制 Cookie
            </p>
          </div>
          
          <p className="mt-3 text-sm text-gray-500">
            提示: 支持输入微博用户 ID 或主页 URL 进行在线爬取，或点击"选择本地目录"加载已下载的数据
          </p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-3 animate-fade-in">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* 爬取结果 */}
        {crawlResult?.success && crawlResult.user_info && (
          <div className="animate-fade-in">
            <UserCard 
              userInfo={crawlResult.user_info}
              postsCount={crawlResult.posts_count}
              imagesCount={crawlResult.images_count}
            />
            
            {/* 数据来源标签 */}
            {localPosts.length > 0 && (
              <div className="mt-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm inline-flex items-center gap-2">
                <FolderOpen className="w-4 h-4" />
                数据来源：本地目录
              </div>
            )}
            
            {/* 图片画廊 */}
            <div className="mt-6">
              <ImageGallery 
                userId={userId} 
                localPosts={localPosts.length > 0 ? localPosts : undefined}
              />
            </div>
          </div>
        )}

        {/* 空状态 */}
        {!loading && !crawlResult && !error && (
          <div className="text-center py-16">
            <ImageIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">开始浏览微博相册</h3>
            <p className="text-gray-500">输入微博用户 ID 或主页链接，即可查看该博主的所有公开图片</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
