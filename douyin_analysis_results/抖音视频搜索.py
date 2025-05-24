"""
抖音视频搜索模块 - URL版本

功能：
1. 根据关键词搜索抖音视频
2. 返回搜索结果中的视频列表
3. 支持通过网络接口获取搜索结果，无需浏览器

日期: 2024年
"""

import time
import random
import re
import json
import requests
from urllib.parse import quote, urlencode
import hashlib


class DouyinVideoSearcher:
    """抖音视频搜索类 - URL版本"""
    
    def __init__(self):
        """初始化搜索器"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
        }
        self.search_results = []

    def search_direct_url(self, keyword, max_videos=10):
        """
        使用网络搜索API直接获取视频列表
        
        :param keyword: 搜索关键词
        :param max_videos: 最大返回视频数量
        :return: 视频列表
        """
        print(f"\n正在初始化搜索器...")
        
        if not keyword:
            print("错误: 搜索关键词不能为空")
            return []
        
        print(f"\n开始搜索关键词: \"{keyword}\"，请稍候...")
        
        try:
            # 方法1：搜索页URL格式
            encoded_keyword = quote(keyword)
            search_url = f"https://www.douyin.com/search/{encoded_keyword}"
            
            # 访问搜索页面
            results = self._fetch_search_results(search_url, max_videos)
            if results:
                print(f"搜索成功，找到 {len(results)} 个视频")
                self.search_results = results
                return results
            
            # 方法2：使用热门分享URL
            print("尝试使用备用方法搜索...")
            try:
                backup_results = self._search_by_keywords(keyword, max_videos)
                if backup_results:
                    print(f"备用搜索成功，找到 {len(backup_results)} 个视频")
                    self.search_results = backup_results
                    return backup_results
            except Exception as e:
                print(f"备用搜索方法失败: {e}")
            
            print("未找到相关视频或搜索失败")
            return []
            
        except Exception as e:
            print(f"搜索出错: {str(e)}")
            return []
    
    def _fetch_search_results(self, url, max_count=10):
        """从URL获取搜索结果"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
            
            # 尝试从HTML中提取视频信息
            html = response.text
            video_ids = re.findall(r'/video/(\d+)', html)
            
            if not video_ids:
                return []
            
            # 去重
            video_ids = list(set(video_ids))[:max_count]
            
            results = []
            for vid in video_ids:
                video_url = f"https://www.douyin.com/video/{vid}"
                # 获取视频详情
                try:
                    video_info = self._fetch_video_info(video_url)
                    if video_info:
                        results.append(video_info)
                except Exception as e:
                    print(f"获取视频 {vid} 信息失败: {str(e)}")
            
            return results
        
        except Exception as e:
            print(f"获取搜索结果失败: {str(e)}")
            return []
    
    def _fetch_video_info(self, video_url):
        """获取视频详细信息"""
        try:
            response = self.session.get(video_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # 提取标题
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html)
            title = title_match.group(1) if title_match else "未知标题"
            # 清理标题
            title = title.replace(" - 抖音", "").strip()
            
            # 提取作者
            author_match = re.search(r'name="author" content="([^"]+)"', html)
            author = author_match.group(1) if author_match else "未知作者"
            
            # 提取视频ID
            video_id = video_url.split("/")[-1].split("?")[0]
            
            return {
                'title': title,
                'author': author,
                'url': video_url,
                'video_id': video_id,
                'likes': "未知",
                'comments': "未知"
            }
        
        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            return None
    
    def _search_by_keywords(self, keyword, max_count=10):
        """使用关键词搜索抖音视频的URL方法"""
        # 构建搜索URL
        keyword_for_api = quote(keyword)
        search_api_url = f"https://www.douyin.com/aweme/v1/web/general/search/single/"
        
        # 生成时间戳和设备ID
        timestamp = str(int(time.time()))
        device_id = hashlib.md5(timestamp.encode()).hexdigest()[:16]  # 简单模拟设备ID
        
        # 搜索参数
        params = {
            'keyword': keyword,
            'device_platform': 'webapp',
            'source': 'normal_search',
            'search_channel': 'aweme_general',
            'type': 1,  # 视频类型
            'device_id': device_id,
            'count': max_count,
            'version_name': '23.5.0',
            'aid': 6383
        }
        
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/json'
        
        try:
            response = self.session.get(
                search_api_url, 
                params=params,
                headers=headers,
                timeout=10
            )
            
            # 尝试解析JSON响应
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'status_code' in data and data['status_code'] == 0:
                        # 提取视频信息
                        videos = []
                        for item in data.get('data', []):
                            if 'aweme_info' in item:
                                video = item['aweme_info']
                                video_id = video.get('aweme_id')
                                title = video.get('desc', '未知标题')
                                author = video.get('author', {}).get('nickname', '未知作者')
                                video_url = f"https://www.douyin.com/video/{video_id}"
                                
                                videos.append({
                                    'title': title,
                                    'author': author,
                                    'url': video_url,
                                    'video_id': video_id,
                                    'likes': "未知",
                                    'comments': "未知"
                                })
                        
                        return videos
                except json.JSONDecodeError:
                    pass
            
            # 备用方法：使用web搜索页面
            backup_url = f"https://www.douyin.com/search/{keyword_for_api}?source=normal_search&type=video"
            return self._fetch_search_results(backup_url, max_count)
            
        except Exception as e:
            print(f"通过关键词API搜索失败: {str(e)}")
            # 尝试备用方法
            try:
                backup_url = f"https://www.douyin.com/search/{keyword_for_api}?aid=0&source=normal_search&type=video"
                return self._fetch_search_results(backup_url, max_count)
            except:
                return []

    def search_videos(self, keyword, max_videos=10):
        """保留旧的接口名称兼容已有代码调用"""
        return self.search_direct_url(keyword, max_videos)
            
    def display_search_results(self):
        """显示搜索结果"""
        if not self.search_results:
            print("没有找到视频结果")
            return
            
        print("\n" + "=" * 80)
        print(" 搜索结果 ".center(78, "="))
        print("=" * 80)
        
        for i, video in enumerate(self.search_results):
            # 安全获取视频信息
            title = video.get('title', '未知标题')
            author = video.get('author', '未知作者')
            likes = video.get('likes', '未知')
            comments = video.get('comments', '未知')
            video_url = video.get('url', '')
            
            print(f"\n[{i+1}] {title}")
            print(f"   作者: {author}")
            print(f"   点赞: {likes} | 评论: {comments}")
            print(f"   链接: {video_url}")
            print("-" * 80)
            
    def select_video(self):
        """让用户选择一个视频"""
        if not self.search_results:
            print("没有可选择的视频")
            return None
            
        # 安全处理，确保至少有一个有效结果
        valid_results = [v for v in self.search_results if 'url' in v and v['url']]
        if not valid_results:
            print("没有找到有效的视频链接")
            return None
        
        # 将有效结果更新回搜索结果
        self.search_results = valid_results
            
        while True:
            try:
                choice = input("\n请选择要爬取评论的视频编号 [1-{}]: ".format(len(self.search_results)))
                
                if not choice.strip():
                    return None
                    
                index = int(choice) - 1
                if 0 <= index < len(self.search_results):
                    selected_video = self.search_results[index]
                    print(f"\n已选择: {selected_video.get('title', '未知视频')}")
                    return selected_video
                else:
                    print(f"无效的选择，请输入 1-{len(self.search_results)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
            except Exception as e:
                print(f"选择视频时发生错误: {str(e)}")
                return None


def main():
    """主函数"""
    print("=" * 60)
    print("抖音视频搜索工具 - URL版本")
    print("=" * 60)
    
    # 创建搜索器实例
    searcher = DouyinVideoSearcher()
    
    while True:
        # 获取搜索关键词
        keyword = input("\n请输入搜索关键词 (直接回车退出): ")
        
        if not keyword.strip():
            print("退出搜索")
            break
        
        # 设置最大返回结果数
        try:
            max_count_input = input("请输入最大返回结果数 (直接回车使用默认值10): ")
            max_count = int(max_count_input) if max_count_input.strip() else 10
        except ValueError:
            max_count = 10
            print("输入格式错误，使用默认值10")
        
        # 执行搜索
        videos = searcher.search_direct_url(keyword, max_count)
        
        # 显示搜索结果
        searcher.display_search_results()
        
        # 选择视频（如果有结果）
        if videos:
            selected = searcher.select_video()
            if selected:
                # 询问是否爬取评论
                crawl_choice = input("\n是否立即爬取该视频的评论? (y/n): ")
                if crawl_choice.lower() == 'y':
                    try:
                        # 导入爬虫模块并爬取评论
                        from 抖音评论爬虫 import DouyinCommentCrawler
                        
                        # 询问是否使用正常浏览器模式
                        use_normal_mode = input("是否使用正常浏览器模式 (可以登录账号) [Y/n]: ").lower() != 'n'
                        
                        # 创建爬虫实例
                        crawler = DouyinCommentCrawler(
                            video_url=selected['url'],
                            use_normal_mode=use_normal_mode,
                            login_first=False if not use_normal_mode else input("是否需要在爬取前先登录抖音账号 [y/N]: ").lower() == 'y'
                        )
                        
                        # 执行爬取
                        crawler.start_crawler()
                        
                    except ImportError:
                        print("未找到评论爬虫模块，请确保 douyin_crawler.py 在正确的位置")
                    except Exception as e:
                        print(f"爬取评论时出错: {str(e)}")
            
        # 询问是否继续搜索
        continue_choice = input("\n是否继续搜索? (y/n): ")
        if continue_choice.lower() != 'y':
            break
    
    print("\n感谢使用抖音视频搜索工具！")


if __name__ == "__main__":
    main() 