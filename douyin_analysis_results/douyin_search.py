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
            # 设置浏览器选项
            co = ChromiumOptions()
            
            # 根据模式选择是否使用正常/无痕模式
            if self.use_normal_mode:
                co.set_paths(
                    local_port=9222,
                    cache_path=True  # 使用缓存，保留登录状态
                )
            else:
                co.set_paths(
                    local_port=9222,
                    cache_path=None  # 不使用缓存，相当于无痕模式
                )
            
            # 创建浏览器实例
            self.driver = ChromiumPage(co)
            
            # 在创建浏览器实例后设置窗口大小
            try:
                # 正确的API是driver.window.set_size
                self.driver.window.set_size(1280, 800)
            except Exception as e:
                # 如果设置窗口大小失败，记录错误但继续执行
                print(f"注意: 设置浏览器窗口大小失败，将使用默认大小。错误信息: {str(e)}")
            
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
        
        # 检测登录状态的函数
        def check_login_status():
            nonlocal login_detected
            while time.time() - start_time < max_wait_time and not login_detected:
                try:
                    # 使用多种方式检查是否已登录
                    # 1. 检查头像元素
                    try:
                        avatar_elements = self.driver.find_elements('xpath://div[contains(@class, "avatar")]')
                        for avatar in avatar_elements:
                            if avatar.is_displayed():
                                login_detected = True
                                break
                    except:
                        pass
                        
                    # 2. 检查用户名元素
                    if not login_detected:
                        try:
                            user_elements = self.driver.find_elements('xpath://p[contains(@class, "nickname") or contains(@class, "username")]')
                            for user_elem in user_elements:
                                if user_elem.is_displayed() and user_elem.text.strip():
                                    login_detected = True
                                    break
                        except:
                            pass
                    
                    # 3. 检查登录后特有的元素
                    if not login_detected:
                        try:
                            # 检查是否有消息图标等登录后才有的元素
                            logged_elements = self.driver.find_elements('xpath://div[contains(@class, "message") or contains(@class, "notification")]')
                            if logged_elements:
                                login_detected = True
                        except:
                            pass
                except Exception as e:
                    print(f"检测登录状态时出错: {str(e)}")
                    
                time.sleep(2)  # 每2秒检查一次
        
        # 启动检测线程
        import threading
        import msvcrt
        
        login_thread = threading.Thread(target=check_login_status)
        login_thread.daemon = True
        login_thread.start()
        
        # 主线程等待用户按Enter或登录完成
        print("等待登录中...(按Enter跳过)")
        while time.time() - start_time < max_wait_time and not login_detected:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\r':  # Enter键
                    print("用户手动跳过等待")
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
            encoded_keyword = quote(keyword)
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
        max_scrolls = (max_videos // 5) + 2  # 每次滚动大约加载5个视频，多滚动几次确保加载足够的视频
        
        for _ in range(max_scrolls):
            try:
                # 使用更兼容的滚动方式
                try:
                    # 尝试使用window.scroll方法
                    self.driver.execute_script(f"window.scrollBy(0, 800);")
                except:
                    # 备用滚动方式
                    try:
                        self.driver.scroll.down(800)
                    except:
                        # 最后的备用方式
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                scroll_count += 1
                
                # 随机等待一段时间，模拟人类行为
                wait_time = random.uniform(0.8, 1.5)
                time.sleep(wait_time)
                
                # 检查是否已经加载了足够的视频 - 使用更通用的选择器
                try:
                    # 尝试查找视频元素
                    video_elements = self.driver.find_elements('xpath://a[contains(@href, "/video/")]')
                    if len(video_elements) >= max_videos:
                        print(f"已加载 {len(video_elements)} 个视频结果")
                        break
                except:
                    # 使用备用选择器
                    try:
                        video_elements = self.driver.find_elements('tag:a', 'contains(@href, "/video/")')
                        if len(video_elements) >= max_videos:
                            print(f"已加载 {len(video_elements)} 个视频结果")
                            break
                    except:
                        pass
                    
            except Exception as e:
                print(f"滚动加载时出错: {str(e)}")
                time.sleep(1)  # 出错时多等待一下
        
        print(f"完成滚动 {scroll_count} 次")
        
    def _extract_video_info(self, max_videos):
        """提取视频信息"""
        results = []
        
        try:
            # 查找视频容器 - 更新XPath选择器，使其更通用
            video_containers = self.driver.find_elements('xpath://li[contains(@class, "search-result") or contains(@class, "video-card")]')
            
            if not video_containers:
                # 如果找不到视频容器，尝试更通用的选择器
                video_containers = self.driver.find_elements('tag:a', 'contains(@href, "/video/")')
                
            print(f"找到 {len(video_containers)} 个视频结果")
            
            # 提取每个视频的信息
            for i, container in enumerate(video_containers[:max_videos]):
                try:
                    # 视频链接和ID - 使用更灵活的方式查找
                    video_url = None
                    try:
                        # 尝试查找链接元素
                        video_link_elem = container.find_element('tag:a', 'contains(@href, "/video/")')
                        video_url = video_link_elem.get_attribute('href')
                    except:
                        # 如果容器本身就是链接元素
                        if 'href' in container.attrs and '/video/' in container.attrs['href']:
                            video_url = container.attrs['href']
                    
                    # 如果仍然找不到链接，跳过此视频
                    if not video_url:
                        continue
                        
                    video_id = self._extract_video_id(video_url)
                    
                    # 视频标题 - 使用更灵活的选择器
                    title = "未知标题"
                    try:
                        # 尝试多种方式查找标题
                        title_elem = container.find_element('xpath:.//p[contains(@class, "title")]')
                        title = title_elem.text.strip()
                    except:
                        try:
                            # 尝试其他常见的标题元素
                            title_elem = container.find_element('xpath:.//div[contains(@class, "title") or contains(@class, "desc")]')
                            title = title_elem.text.strip()
                        except:
                            # 尝试查找任何看起来像标题的文本
                            title_elems = container.find_elements('tag:p')
                            if title_elems:
                                title = title_elems[0].text.strip()
                    
                    # 作者信息 - 同样使用灵活的选择器
                    author = "未知作者"
                    try:
                        author_elem = container.find_element('xpath:.//p[contains(@class, "author")]')
                        author = author_elem.text.strip()
                    except:
                        try:
                            author_elem = container.find_element('xpath:.//div[contains(@class, "author") or contains(@class, "user")]')
                            author = author_elem.text.strip()
                        except:
                            pass
                    
                    # 统计信息比较难准确获取，使用默认值
                    likes = "未知"
                    comments = "未知"
                    
                    # 尝试获取统计信息
                    try:
                        stats_elems = container.find_elements('xpath:.//span[contains(@class, "count")]')
                        if len(stats_elems) > 0:
                            likes = stats_elems[0].text.strip()
                        if len(stats_elems) > 1:
                            comments = stats_elems[1].text.strip()
                    except:
                        pass
                    
                    results.append({
                        'title': title,
                        'url': video_url,
                        'video_id': video_id,
                        'author': author,
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
            print(f"\n[{i+1}] {video['title']}")
            print(f"   作者: {video['author']}")
            print(f"   点赞: {video['likes']} | 评论: {video['comments']}")
            print(f"   链接: {video['url']}")
            print("-" * 80)
            
    def select_video(self):
        """让用户选择一个视频"""
        if not self.search_results:
            return None
            
        while True:
            try:
                choice = input("\n请选择要爬取评论的视频编号 [1-{}]: ".format(len(self.search_results)))
                
                if not choice.strip():
                    return None
                    
                index = int(choice) - 1
                if 0 <= index < len(self.search_results):
                    selected_video = self.search_results[index]
                    print(f"\n已选择: {selected_video['title']}")
                    return selected_video
                else:
                    print(f"无效的选择，请输入 1-{len(self.search_results)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
                
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("浏览器已关闭") 