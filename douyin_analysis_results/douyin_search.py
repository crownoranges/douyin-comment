"""
抖音视频搜索模块

功能：
1. 根据关键词搜索抖音视频
2. 返回搜索结果中的视频列表
3. 支持选择视频进行评论爬取

日期: 2025年3月
"""

import time
import random
import re
import json
from urllib.parse import quote
from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions


class DouyinVideoSearcher:
    """抖音视频搜索类"""
    
    def __init__(self, use_normal_mode=True, login_first=False):
        """
        初始化搜索器
        :param use_normal_mode: 是否使用正常模式启动浏览器(不使用无痕模式)
        :param login_first: 启动后是否需要先让用户登录
        """
        self.driver = None
        self.use_normal_mode = use_normal_mode
        self.login_first = login_first
        self.search_results = []
        
    def _initialize_browser(self):
        """初始化浏览器"""
        try:
            # 完全重写浏览器初始化方法
            # 不使用任何可能不兼容的选项设置
            if self.use_normal_mode:
                # 使用最简单的方式创建浏览器实例
                # 使用正常模式（有缓存）
                self.driver = ChromiumPage()
            else:
                # 无痕模式（无缓存）
                self.driver = ChromiumPage(chromium_options={"headless": False, "incognito": True})
            
            # 注意：这里不设置窗口大小，使用浏览器默认窗口大小
            
            print("浏览器初始化成功")
            return True
        except Exception as e:
            print(f"浏览器初始化失败: {str(e)}")
            return False
            
    def _handle_login(self):
        """处理登录流程"""
        if not self.login_first:
            return True
            
        print("请在打开的浏览器中登录抖音账号...")
        print("提示: 登录后系统将自动检测并继续，您也可以按Enter键跳过等待")
        
        # 最多等待120秒让用户登录
        max_wait_time = 120
        start_time = time.time()
        
        # 创建检测登录状态的线程
        login_detected = False
        
        # 检测登录状态的函数 - 使用简化的检测方法
        def check_login_status():
            nonlocal login_detected
            while time.time() - start_time < max_wait_time and not login_detected:
                try:
                    # 检测用户头像元素 - 使用最基本的方法
                    try:
                        elems = self.driver.find_elements(xpath="//div[contains(@class, 'avatar')]")
                        if any(elem for elem in elems if elem.is_displayed()):
                            login_detected = True
                            break
                    except:
                        pass
                        
                    # 简单检查页面标题或URL变化
                    try:
                        if "我的主页" in self.driver.title or "我的" in self.driver.title:
                            login_detected = True
                            break
                    except:
                        pass
                        
                except:
                    # 忽略所有错误，继续检测
                    pass
                    
                time.sleep(2)  # 每2秒检查一次
        
        # 导入必要的模块
        import threading
        try:
            import msvcrt  # Windows
        except ImportError:
            msvcrt = None  # 非Windows系统
        
        # 启动检测线程
        login_thread = threading.Thread(target=check_login_status)
        login_thread.daemon = True
        login_thread.start()
        
        # 主线程等待用户按Enter或登录完成
        print("等待登录中...(按Enter跳过)")
        while time.time() - start_time < max_wait_time and not login_detected:
            if msvcrt:  # 仅在Windows上支持
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\r':  # Enter键
                        print("用户手动跳过等待")
                        break
            else:
                # 非Windows系统等待5秒
                time.sleep(5)
                break
                
            time.sleep(0.5)
            
        if login_detected:
            print("检测到已登录!")
        else:
            print("登录等待超时或用户跳过，继续执行...")
            
        return True
            
    def search_videos(self, keyword, max_videos=10):
        """
        搜索抖音视频
        :param keyword: 搜索关键词
        :param max_videos: 最大返回视频数量
        :return: 视频列表 [{'title': '标题', 'url': '视频链接', 'author': '作者', 'likes': '点赞数'}]
        """
        if not keyword:
            print("错误: 搜索关键词不能为空")
            return []
            
        # 初始化浏览器
        if not self.driver:
            if not self._initialize_browser():
                return []
                
        try:
            # 编码关键词，构建搜索URL
            try:
                from urllib.parse import quote
                encoded_keyword = quote(keyword)
            except:
                # 简单替换一些基本字符
                encoded_keyword = keyword.replace(' ', '%20')
                
            search_url = f"https://www.douyin.com/search/{encoded_keyword}?aid=0&source=normal_search&type=video"
            
            print(f"正在搜索: {keyword}")
            print(f"访问URL: {search_url}")
            
            # 访问搜索页面
            self.driver.get(search_url)
            time.sleep(3)  # 等待页面加载
            
            # 处理登录流程（如果需要）
            if self.use_normal_mode and self.login_first:
                self._handle_login()
                
            # 等待搜索结果加载
            print("等待搜索结果加载...")
            time.sleep(2)
            
            # 滚动页面加载更多结果
            self._load_more_results(max_videos)
            
            # 提取视频信息
            return self._extract_video_info(max_videos)
            
        except Exception as e:
            print(f"搜索视频时出错: {str(e)}")
            return []
        finally:
            # 不关闭浏览器，以便后续继续使用
            pass
            
    def _load_more_results(self, max_videos):
        """滚动加载更多搜索结果"""
        print("加载更多搜索结果...")
        scroll_count = 0
        max_scrolls = (max_videos // 3) + 3  # 增加滚动次数，确保加载足够的视频
        
        for _ in range(max_scrolls):
            try:
                # 使用纯JavaScript滚动，最大兼容性
                js_scroll = "window.scrollBy(0, 800);"
                self.driver.run_js(js_scroll)  # 尝试使用run_js
                
                scroll_count += 1
                
                # 等待加载
                time.sleep(1.5)
                
            except Exception as e:
                print(f"滚动加载时出错: {str(e)}")
                try:
                    # 备用JavaScript滚动方式
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    time.sleep(1)
                except:
                    pass
        
        print(f"完成滚动 {scroll_count} 次")
        
    def _extract_video_info(self, max_videos):
        """提取视频信息"""
        results = []
        
        try:
            # 使用最基本的XPath方式查找视频容器
            try:
                # 方法1：根据类名查找
                video_containers = self.driver.find_elements(xpath='//li[contains(@class, "search-result") or contains(@class, "video-card")]')
            except:
                try:
                    # 方法2：直接查找视频链接
                    video_containers = self.driver.find_elements(xpath='//a[contains(@href, "/video/")]')
                except:
                    # 兜底方法：尝试各种可能的选择器
                    video_containers = self.driver.find_elements(tag='li')
                
            if not video_containers:
                print("未找到任何视频结果")
                return []
                
            print(f"找到 {len(video_containers)} 个视频结果")
            
            # 提取每个视频的信息
            for i, container in enumerate(video_containers[:max_videos]):
                try:
                    # 视频链接和ID - 使用基本API
                    video_url = None
                    try:
                        # 尝试在容器内查找链接
                        try:
                            video_link_elem = container.find_element(xpath='.//a[contains(@href, "/video/")]')
                            video_url = video_link_elem.attr('href')  # 尝试使用attr属性
                        except:
                            try:
                                # 备用方法：使用get_attribute
                                video_url = video_link_elem.get_attribute('href')
                            except:
                                pass
                    except:
                        # 如果容器本身是链接
                        try:
                            if 'href' in container.attrs and '/video/' in container.attrs['href']:
                                video_url = container.attrs['href']
                        except:
                            # 最后尝试直接获取href属性
                            try:
                                video_url = container.attr('href')
                            except:
                                try:
                                    video_url = container.get_attribute('href')
                                except:
                                    pass
                    
                    # 如果仍然找不到链接，跳过此视频
                    if not video_url:
                        continue
                        
                    video_id = self._extract_video_id(video_url)
                    
                    # 视频标题 - 使用基本API
                    title = "未知标题"
                    try:
                        # 尝试多种元素定位方式
                        try:
                            title_elem = container.find_element(xpath='.//p[contains(@class, "title")]')
                            title = title_elem.text
                        except:
                            pass
                            
                        if not title or title == "未知标题":
                            # 尝试其他标题元素
                            try:
                                title_elem = container.find_element(xpath='.//div[contains(@class, "title")]')
                                title = title_elem.text
                            except:
                                pass
                                
                        if not title or title == "未知标题":
                            # 尝试查找任何文本段落
                            try:
                                title_elems = container.find_elements(tag='p')
                                if title_elems:
                                    title = title_elems[0].text
                            except:
                                pass
                    except:
                        pass
                    
                    # 作者信息 - 同样使用基本API
                    author = "未知作者"
                    try:
                        try:
                            author_elem = container.find_element(xpath='.//p[contains(@class, "author")]')
                            author = author_elem.text
                        except:
                            try:
                                author_elem = container.find_element(xpath='.//div[contains(@class, "author")]')
                                author = author_elem.text
                            except:
                                pass
                    except:
                        pass
                    
                    # 统计信息
                    likes = "未知"
                    comments = "未知"
                    
                    results.append({
                        'title': title.strip() if title else "未知标题",
                        'url': video_url,
                        'video_id': video_id,
                        'author': author.strip() if author else "未知作者",
                        'likes': likes,
                        'comments': comments
                    })
                    
                except Exception as e:
                    print(f"提取第 {i+1} 个视频信息时出错: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"提取视频信息出错: {str(e)}")
            
        self.search_results = results
        return results
        
    def _extract_video_id(self, url):
        """从URL中提取视频ID"""
        if not url:
            return None
            
        try:
            # 处理标准链接，例如 www.douyin.com/video/7353500880198536457
            parts = url.split("/")
            for part in parts:
                # 查找纯数字ID
                if part.strip().isdigit():
                    return part.strip()
                    
            # 如果没找到纯数字，就用最后一部分
            return parts[-1].split("?")[0]
        except:
            # 兜底，返回原始URL的一部分
            return url.split("/")[-1].split("?")[0]
            
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
                
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("浏览器已关闭") 