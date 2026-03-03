import React from 'react'
import { Users, Image, FileText } from 'lucide-react'

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

interface UserCardProps {
  userInfo: UserInfo
  postsCount: number
  imagesCount: number
}

const UserCard: React.FC<UserCardProps> = ({ userInfo, postsCount, imagesCount }) => {
  const formatNumber = (num: number): string => {
    if (num >= 10000) {
      return (num / 10000).toFixed(1) + '万'
    }
    return num.toLocaleString()
  }

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden animate-slide-up">
      {/* 封面图 */}
      {userInfo.cover_image_phone && (
        <div className="h-32 bg-gradient-to-r from-red-400 to-red-600 relative">
          <img
            src={userInfo.cover_image_phone}
            alt="cover"
            className="w-full h-full object-cover"
          />
        </div>
      )}
      
      <div className="p-6">
        <div className="flex items-start gap-4">
          {/* 头像 */}
          <div className="flex-shrink-0">
            <img
              src={userInfo.profile_image_url || '/default-avatar.png'}
              alt={userInfo.screen_name}
              className="w-20 h-20 rounded-full border-4 border-white shadow-md object-cover"
            />
          </div>
          
          {/* 用户信息 */}
          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-bold text-gray-900 truncate">
              {userInfo.screen_name}
            </h3>
            <p className="text-gray-500 text-sm mt-1 line-clamp-2">
              {userInfo.description || '暂无简介'}
            </p>
            
            {/* 统计数据 */}
            <div className="flex items-center gap-6 mt-4 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                <span className="font-medium">{formatNumber(userInfo.followers_count)}</span>
                <span className="text-gray-400">粉丝</span>
              </div>
              <div className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                <span className="font-medium">{formatNumber(userInfo.statuses_count)}</span>
                <span className="text-gray-400">微博</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* 爬取结果统计 */}
        <div className="mt-6 pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2 text-green-600">
                <FileText className="w-5 h-5" />
                <span className="font-semibold">{postsCount}</span>
                <span className="text-gray-600">条带图微博</span>
              </div>
              <div className="flex items-center gap-2 text-blue-600">
                <Image className="w-5 h-5" />
                <span className="font-semibold">{imagesCount}</span>
                <span className="text-gray-600">张图片</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default UserCard
