import React, { useState, useEffect } from 'react'
import { Loader2, Download, X, ChevronLeft, ChevronRight, ImageIcon } from 'lucide-react'
import axios from 'axios'

// API 基础 URL
const API_BASE_URL = 'http://localhost:8000'

// 类型定义
interface ImageInfo {
  url: string
  thumbnail: string
  pid: string
  width: number
  height: number
  local_path?: string
}

interface WeiboPost {
  id: string
  bid: string
  text: string
  created_at: string
  images: ImageInfo[]
  user_id: string
  screen_name: string
  reposts_count: number
  comments_count: number
  attitudes_count: number
}

interface ImageGalleryProps {
  userId: string
  localPosts?: WeiboPost[]
}

const ImageGallery: React.FC<ImageGalleryProps> = ({ userId, localPosts }) => {
  const [posts, setPosts] = useState<WeiboPost[]>(localPosts || [])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(!localPosts || localPosts.length === 0)
  const [selectedImage, setSelectedImage] = useState<{url: string, index: number, post: WeiboPost} | null>(null)
  const [error, setError] = useState('')

  // 如果有本地数据，直接使用
  useEffect(() => {
    if (localPosts && localPosts.length > 0) {
      setPosts(localPosts)
      setHasMore(false) // 本地数据一次性加载完毕
      setError('')
    }
  }, [localPosts])

  const fetchImages = async (pageNum: number) => {
    setLoading(true)
    setError('')
    
    try {
      const response = await axios.get<WeiboPost[]>(
        `${API_BASE_URL}/api/images/${userId}`,
        { params: { page: pageNum, page_size: 20 } }
      )
      
      if (response.data.length === 0) {
        setHasMore(false)
      } else {
        setPosts(prev => pageNum === 1 ? response.data : [...prev, ...response.data])
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载图片失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId && (!localPosts || localPosts.length === 0)) {
      setPage(1)
      setHasMore(true)
      fetchImages(1)
    }
  }, [userId, localPosts])

  const loadMore = () => {
    if (!loading && hasMore) {
      const nextPage = page + 1
      setPage(nextPage)
      fetchImages(nextPage)
    }
  }

  const openLightbox = (image: ImageInfo, imageIndex: number, post: WeiboPost) => {
    setSelectedImage({ url: image.url, index: imageIndex, post })
  }

  const closeLightbox = () => {
    setSelectedImage(null)
  }

  const navigateImage = (direction: 'prev' | 'next') => {
    if (!selectedImage) return
    
    const { post, index } = selectedImage
    const newIndex = direction === 'prev' ? index - 1 : index + 1
    
    if (newIndex >= 0 && newIndex < post.images.length) {
      setSelectedImage({ url: post.images[newIndex].url, index: newIndex, post })
    }
  }

  const downloadImage = (url: string, filename: string) => {
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // 提取所有图片用于瀑布流展示
  const allImages: {image: ImageInfo, post: WeiboPost, index: number}[] = []
  posts.forEach(post => {
    post.images.forEach((image, index) => {
      allImages.push({ image, post, index })
    })
  })

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => fetchImages(1)}
          className="mt-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <ImageIcon className="w-5 h-5" />
          图片相册
        </h3>
        <span className="text-sm text-gray-500">共 {allImages.length} 张</span>
      </div>
      
      {/* 瀑布流图片网格 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {allImages.map(({ image, post, index }, i) => (
          <div
            key={`${post.id}-${image.pid}`}
            className="group relative aspect-square rounded-lg overflow-hidden cursor-pointer bg-gray-100 hover:shadow-lg transition-all duration-300 animate-fade-in"
            style={{ animationDelay: `${i * 30}ms` }}
            onClick={() => openLightbox(image, index, post)}
          >
            <img
              src={image.thumbnail}
              alt={`图片 ${i + 1}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              loading="lazy"
            />
            {/* 悬停遮罩 */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300 flex items-center justify-center opacity-0 group-hover:opacity-100">
              <Download className="w-8 h-8 text-white drop-shadow-lg" />
            </div>
          </div>
        ))}
      </div>
      
      {/* 加载更多 */}
      {hasMore && (
        <div className="mt-6 text-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                加载中...
              </>
            ) : (
              '加载更多'
            )}
          </button>
        </div>
      )}
      
      {!hasMore && allImages.length > 0 && (
        <p className="text-center text-gray-500 mt-6">已加载全部图片</p>
      )}

      {/* 灯箱查看器 */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center animate-fade-in"
          onClick={closeLightbox}
        >
          {/* 关闭按钮 */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition-colors z-10"
          >
            <X className="w-8 h-8" />
          </button>
          
          {/* 下载按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              downloadImage(selectedImage.url, `weibo_${selectedImage.post.id}_${selectedImage.index + 1}.jpg`)
            }}
            className="absolute top-4 right-16 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition-colors z-10"
          >
            <Download className="w-8 h-8" />
          </button>
          
          {/* 导航按钮 */}
          {selectedImage.index > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                navigateImage('prev')
              }}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition-colors z-10"
            >
              <ChevronLeft className="w-10 h-10" />
            </button>
          )}
          
          {selectedImage.post.images.length > 1 && selectedImage.index < selectedImage.post.images.length - 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                navigateImage('next')
              }}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-full transition-colors z-10"
            >
              <ChevronRight className="w-10 h-10" />
            </button>
          )}
          
          {/* 图片 */}
          <img
            src={selectedImage.url}
            alt="查看大图"
            className="max-w-[90%] max-h-[90vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          
          {/* 图片信息 */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/80 text-sm bg-black/50 px-4 py-2 rounded-full">
            {selectedImage.index + 1} / {selectedImage.post.images.length}
          </div>
        </div>
      )}
    </div>
  )
}

export default ImageGallery
