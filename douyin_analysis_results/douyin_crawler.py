"""
抖音视频评论爬取工具 - 强化版

功能：
1. 自动爬取指定抖音视频的全部评论数据
2. 使用多种滚动策略和加载方式确保获取所有评论
3. 按日期和时间命名CSV文件，避免覆盖历史数据
4. 智能检测评论加载完成

日期: 2024年
"""

import time
import datetime
import csv
import os
import random
import json
import re
import threading
import msvcrt
import networkx as nx
from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions
from sklearn.feature_extraction.text import TfidfVectorizer


class DouyinCommentCrawler:
    """抖音评论爬虫类 - 强化版"""
    
    def __init__(self, video_url=None, video_id=None, max_pages=None, use_normal_mode=True, login_first=False):
        """
        初始化爬虫
        :param video_url: 视频URL，例如 https://www.douyin.com/video/7353500880198536457
        :param video_id: 视频ID，如果提供了video_url则可不提供
        :param max_pages: 最大爬取页数，默认为None表示爬取全部评论
        :param use_normal_mode: 是否使用正常模式启动浏览器(不使用无痕模式)
        :param login_first: 启动后是否需要先让用户登录
        """
        self.video_url = video_url
        self.video_id = video_id if video_id else self._extract_video_id(video_url)
        self.max_pages = max_pages
        self.comments = []
        self.comment_ids = set()  # 用于去重的评论ID集合
        self.driver = None
        self.processed_comments = 0  # 已处理的评论数
        self.use_normal_mode = use_normal_mode  # 是否使用正常模式
        self.login_first = login_first  # 是否需要先登录
        
        # 设置CSV文件存储目录
        self.comments_dir = "crawled_comments"
        
        # 确保目录存在
        if not os.path.exists(self.comments_dir):
            os.makedirs(self.comments_dir)
        
        # 使用当前日期和时间创建唯一的文件名
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = os.path.join(self.comments_dir, f"douyin_comments_{self.video_id}_{current_time}.csv")
    
    def _extract_video_id(self, url):
        """从URL中提取视频ID"""
        if not url:
            raise ValueError("需要提供视频URL或视频ID")
        
        # 规范化URL格式（替换中文冒号，确保格式正确）
        url = url.replace("：", ":").strip()
        if not url.startswith("http"):
            url = "https://" + url.lstrip(":/")
            
        # 处理短链接，例如 v.douyin.com/abcdef/
        if "v.douyin.com" in url:
            # 对于短链接，返回整个路径部分作为ID
            parts = url.split("/")
            # 找出非空的最后一个部分
            for part in reversed(parts):
                if part.strip():
                    return part.strip()
        
        # 处理标准链接，例如 www.douyin.com/video/7353500880198536457
        try:
            # 从路径中提取数字ID
            parts = url.split("/")
            for part in parts:
                # 查找纯数字ID
                if part.strip().isdigit():
                    return part.strip()
            
            # 如果没找到纯数字，就用最后一部分
            return parts[-1].split("?")[0]
        except:
            # 兜底，返回原始URL（可能会导致错误，但至少有返回值）
            print(f"警告: 无法从URL {url} 提取标准视频ID，将使用原始URL处理")
            return url.split("/")[-1].split("?")[0]
    
    def _scroll_to_comments(self):
        """滚动到评论区域"""
        try:
            # 尝试找到评论区域
            comment_area = self.driver.find_element('xpath://div[contains(@class, "comment-mainContent") or contains(@class, "comment-list")]')
            if comment_area:
                self.driver.scroll.to_element(comment_area, center=True)
                time.sleep(1)
        except:
            # 如果找不到评论区，就滚动到页面中部
            self.driver.scroll.to_half()
            time.sleep(1)
    
    def _try_load_more_comments(self):
        """尝试不同方法加载更多评论"""
        # 尝试点击"展开更多回复"按钮
        try:
            more_reply_btns = self.driver.find_elements('xpath://span[contains(text(), "查看") and contains(text(), "回复")]')
            if more_reply_btns:
                for btn in more_reply_btns[:5]:  # 最多点击前5个
                    try:
                        self.driver.scroll.to_element(btn)
                        time.sleep(0.5)
                        btn.click()
                        time.sleep(1)
                        return True
                    except:
                        pass
        except:
            pass
        
        # 尝试点击"展开"按钮
        try:
            expand_btns = self.driver.find_elements('xpath://span[contains(text(), "展开") or contains(text(), "更多")]')
            if expand_btns:
                for btn in expand_btns[:3]:  # 最多点击前3个
                    try:
                        self.driver.scroll.to_element(btn)
                        time.sleep(0.5)
                        btn.click()
                        time.sleep(1)
                        return True
                    except:
                        pass
        except:
            pass
            
        return False
    
    def _perform_scroll(self, method):
        """执行不同的滚动方法
        
        增强版滚动策略，支持多种不同的滚动模式，以适应不同页面结构和加载机制
        """
        print(f"使用滚动策略 {method}")
        try:
            if method == 1:
                # 平滑滚动到底部
                self.driver.scroll.to_bottom(smooth=True)
                time.sleep(0.5)
            elif method == 2:
                # 先向下滚动一部分，再滚动到底部
                self.driver.scroll.down(300)
                time.sleep(0.5)
                self.driver.scroll.to_bottom()
            elif method == 3:
                # 先向上滚动，再向下滚动（有时可以触发加载）
                self.driver.scroll.up(200)
                time.sleep(0.5)
                self.driver.scroll.to_bottom()
            elif method == 4:
                # 滚动到评论区，再滚动到底部
                self._scroll_to_comments()
                time.sleep(0.5)
                self.driver.scroll.to_bottom()
            elif method == 5:
                # 快速滚动到底部，然后慢慢向上滚动
                self.driver.scroll.to_bottom()
                time.sleep(0.5)
                for _ in range(3):
                    self.driver.scroll.up(100)
                    time.sleep(0.3)
            elif method == 6:
                # 【新增】渐进滚动策略：多次小幅度滚动
                height = self.driver.get_window_size()['height']
                for i in range(5):
                    scroll_distance = int(height * 0.3)  # 滚动页面高度的30%
                    self.driver.scroll.down(scroll_distance)
                    time.sleep(0.4)  # 小间隔等待
            elif method == 7:
                # 【新增】波浪式滚动：先下滚再小幅上滚
                for i in range(3):
                    self.driver.scroll.down(300)
                    time.sleep(0.3)
                    self.driver.scroll.up(50)  # 小幅上滚触发可能的加载逻辑
                    time.sleep(0.3)
                self.driver.scroll.to_bottom()
            elif method == 8:
                # 【新增】寻找加载更多按钮并点击
                try:
                    # 尝试找到"加载更多"类型的按钮
                    load_more_btns = self.driver.find_elements('xpath://div[contains(text(), "加载") or contains(text(), "更多") or contains(text(), "展开")]')
                    if load_more_btns:
                        for btn in load_more_btns[:3]:
                            try:
                                self.driver.scroll.to_element(btn, center=True)
                                time.sleep(0.5)
                                btn.click()
                                print("找到并点击了'加载更多'按钮")
                                time.sleep(1.5)  # 等待内容加载
                                return
                            except:
                                pass
                except:
                    pass
                # 如果没找到按钮，回退到常规滚动
                self.driver.scroll.to_bottom(smooth=True)
            elif method == 9:
                # 【新增】根据评论元素精确定位滚动策略
                try:
                    # 查找所有评论元素
                    comments = self.driver.find_elements('xpath://div[contains(@class, "comment-item") or contains(@class, "CommentItem")]')
                    if comments and len(comments) > 2:
                        # 滚动到倒数第二个评论处
                        target = comments[-2]
                        self.driver.scroll.to_element(target, center=True)
                        time.sleep(0.5)
                        # 再滑动一点点继续加载
                        self.driver.scroll.down(200)
                        return
                except:
                    pass
                # 回退到常规滚动
                self.driver.scroll.to_bottom()
            elif method == 10:
                # 【新增】JavaScript滚动，有时候比Python的滚动方法更稳定
                # 使用JS滚动到底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.8)
                # 再执行一个小振动，可能触发加载
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 100);")
                time.sleep(0.3)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            else:
                # 默认方法：平滑滚动到底部
                self.driver.scroll.to_bottom(smooth=True)
        except Exception as e:
            print(f"执行滚动策略 {method} 时出错: {str(e)}")
            # 出错时使用最基本的滚动方法
            try:
                self.driver.scroll.down(300)
            except:
                pass
    
    def start_crawler(self):
        """启动爬虫"""
        print(f"\n开始爬取视频 {self.video_id} 的评论...")
        
        # 创建CSV文件
        f = open(self.output_file, mode='w', encoding='utf-8-sig', newline='')
        # 更新字段列表，包含更多信息
        fieldnames = [
            '评论ID', '昵称', '用户ID', '用户sec_id', '头像', '地区', '时间', 
            '评论', '点赞数', '回复数', '回复给用户', '回复给用户ID', 
            '是否置顶', '是否热评', '包含话题', '提及用户'
        ]
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        try:
            # 初始化浏览器
            print("正在初始化浏览器...")
            if self.use_normal_mode:
                # 修改为使用新版API
                # 创建浏览器配置对象
                co = ChromiumOptions()
                # 设置为非无痕模式
                co.set_argument('--disable-incognito', True)
                # 创建带有自定义选项的浏览器
                self.driver = ChromiumPage(co)
                print("已启用正常浏览模式，您可以登录账号查看评论")
            else:
                # 使用默认配置(无痕模式)
                self.driver = ChromiumPage()
                print("使用默认无痕模式")
            
            # 如果需要先登录
            if self.login_first:
                print("\n请在打开的浏览器中登录抖音账号...")
                print("登录后程序将自动继续 (或按Enter键跳过等待)")
                # 先访问抖音主页
                self.driver.get("https://www.douyin.com/")
                
                # 添加中断机制，允许用户随时跳过等待
                wait_complete = False
                
                # 等待用户输入的线程
                def wait_for_keypress():
                    nonlocal wait_complete
                    while not wait_complete:
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            # 如果按下回车键
                            if key == b'\r':
                                print("\n用户跳过等待，继续执行...")
                                wait_complete = True
                                return
                        time.sleep(0.1)
                
                # 启动等待输入线程
                input_thread = threading.Thread(target=wait_for_keypress)
                input_thread.daemon = True
                input_thread.start()
                
                # 同时检测登录状态
                start_time = time.time()
                while not wait_complete and time.time() - start_time < 120:
                    # 每10秒显示一次提示
                    elapsed = int(time.time() - start_time)
                    if elapsed % 10 == 0:
                        remain = 120 - elapsed
                        print(f"请登录抖音账号，还剩 {remain} 秒... (按Enter跳过)")
                    
                    # 尝试检测是否已登录
                    try:
                        if self.driver.element_exists('xpath://div[contains(@class, "avatar")]'):
                            print("检测到已登录，继续执行...")
                            wait_complete = True
                            break
                    except:
                        pass
                    
                    time.sleep(1)
            
            # 监听评论数据API
            self.driver.listen.start('aweme/v1/web/comment/list/')
            
            # 访问视频页面
            print(f"正在访问视频页面...")
            try:
                # 处理短链接情况
                if self.video_url:
                    # 确保URL格式正确
                    url = self.video_url.replace("：", ":").strip()
                    if not url.startswith("http"):
                        url = "https://" + url.lstrip(":/")
                    
                    print(f"使用URL访问: {url}")
                    self.driver.get(url)
                else:
                    # 使用视频ID直接访问标准页面
                    standard_url = f'https://www.douyin.com/video/{self.video_id}'
                    print(f"使用标准URL访问: {standard_url}")
                    self.driver.get(standard_url)
                    
                # 检查页面是否加载成功
                time.sleep(5)
                
                # 检查是否到达了视频页面
                if "页面不存在" in self.driver.page_source or "404" in self.driver.title:
                    print(f"警告: 页面加载异常，可能是无效的URL或视频ID: {self.video_id}")
                    print("尝试使用备用方法加载...")
                    
                    # 尝试使用另一种方式访问
                    if "v.douyin.com" in (self.video_url or ""):
                        print("检测到短链接，尝试直接访问...")
                        self.driver.get(self.video_url)
            except Exception as e:
                print(f"访问视频页面时出错: {str(e)}")
                print("请检查您的网络连接或URL格式是否正确")
            
            # 等待页面加载
            time.sleep(5)
            
            # 尝试点击"查看更多评论"按钮（如果存在）
            try:
                more_comment_btn = self.driver.find_element('xpath://div[contains(text(), "查看更多评论")]')
                if more_comment_btn:
                    print("点击'查看更多评论'按钮...")
                    more_comment_btn.click()
                    time.sleep(2)
            except:
                print("没有找到'查看更多评论'按钮，继续使用滚动加载评论")
            
            # 先滚动到评论区
            self._scroll_to_comments()
            
            # 爬取评论
            page = 0
            no_new_comments_count = 0     # 连续没有新评论的次数
            max_no_new_attempts = 10      # 最大尝试次数，超过则认为已到达末页
            total_attempts = 0            # 总尝试次数
            last_comment_id_count = 0     # 上一次的评论ID数量
            
            # 添加中断机制
            is_crawling = True            # 爬取状态标志
            
            # 创建监听键盘输入的线程
            def monitor_for_interrupt():
                nonlocal is_crawling
                print("\n爬取过程中，随时可以按Enter键停止爬取并保存已获取的评论")
                while is_crawling:
                    try:
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            # 如果按下回车键
                            if key == b'\r':
                                print("\n用户中断爬取，即将保存当前评论...")
                                is_crawling = False
                                return
                    except:
                        pass
                    time.sleep(0.1)
            
            # 启动监听线程
            interrupt_thread = threading.Thread(target=monitor_for_interrupt)
            interrupt_thread.daemon = True
            interrupt_thread.start()
            
            # 如果设置了最大页数，则限制页数；否则一直爬取直到没有更多评论
            while (self.max_pages is None or page < self.max_pages) and is_crawling:
                try:
                    page += 1
                    print(f'正在爬取第 {page} 页评论...')
                    
                    # 使用不同的滚动策略 (轮流使用不同方法)
                    scroll_method = (page % 10) + 1
                    self._perform_scroll(scroll_method)
                    
                    # 随机等待时间，模拟人工浏览
                    wait_time = 1 + random.random() * 2
                    time.sleep(wait_time)
                    
                    # 等待数据包
                    resp = self.driver.listen.wait(timeout=5)
                    
                    # 如果没有接收到数据包
                    if not resp:
                        total_attempts += 1
                        print(f"未检测到新的评论数据，尝试使用其他方法... (尝试 {total_attempts})")
                        
                        # 尝试其他加载方法
                        if self._try_load_more_comments():
                            # 如果成功点击了某些按钮，给它一次机会
                            continue
                        
                        no_new_comments_count += 1
                        if no_new_comments_count >= max_no_new_attempts:
                            print(f"已连续 {max_no_new_attempts} 次未获取到新评论，可能已到达末页")
                            
                            # 最后尝试刷新页面
                            if no_new_comments_count == max_no_new_attempts:
                                print("尝试刷新页面后继续...")
                                self.driver.refresh()
                                time.sleep(5)
                                self._scroll_to_comments()
                                no_new_comments_count -= 1  # 给最后一次机会
                                continue
                            
                            print("确认已加载全部评论，结束爬取")
                            break
                        
                        continue
                    
                    # 重置计数器
                    total_attempts = 0
                    
                    # 解析JSON数据
                    json_data = resp.response.body
                    
                    if not json_data or 'comments' not in json_data:
                        no_new_comments_count += 1
                        print(f"未获取到有效评论数据，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})")
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次未获取到有效评论数据，可能已到达末页")
                            break
                        continue
                    
                    # 提取评论
                    comments = json_data['comments']
                    if not comments:
                        no_new_comments_count += 1
                        print(f"本页无评论数据，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})")
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次获取到空评论列表，可能已到达末页")
                            break
                        continue
                    
                    # 记录爬取前的评论ID数
                    comment_id_count_before = len(self.comment_ids)
                    
                    # 处理评论数据
                    for comment in comments:
                        try:
                            # 获取评论ID (用于去重)
                            comment_id = comment.get('cid', '') or str(comment.get('id', ''))
                            
                            # 如果已经处理过这个评论，则跳过
                            if comment_id in self.comment_ids:
                                continue
                            
                            # 添加到已处理集合
                            self.comment_ids.add(comment_id)
                            
                            # 使用增强的评论解析方法
                            comment_data = self._parse_comment_details(comment)
                            
                            # 保存到列表和文件
                            self.comments.append(comment_data)
                            csv_writer.writerow(comment_data)
                            
                            # 更新计数并打印
                            self.processed_comments += 1
                            if self.processed_comments % 10 == 0:  # 每10条评论打印一次进度
                                print(f"已爬取 {self.processed_comments} 条评论")
                            elif self.processed_comments % 5 == 0:  # 每5条打印一次简单信息
                                print(f"[{self.processed_comments}] {comment_data['昵称']}: {comment_data['评论'][:20]}...")
                            
                        except Exception as e:
                            print(f"处理评论时出错: {str(e)}")
                    
                    # 检查是否有新的评论ID被添加
                    comment_id_added = len(self.comment_ids) - comment_id_count_before
                    
                    if comment_id_added > 0:
                        print(f"本次获取了 {comment_id_added} 条新评论，累计 {len(self.comments)} 条")
                        no_new_comments_count = 0  # 重置计数器
                        last_comment_id_count = len(self.comment_ids)
                    else:
                        no_new_comments_count += 1
                        print(f"未获取到新评论，尝试继续... (尝试 {no_new_comments_count}/{max_no_new_attempts})")
                        
                        # 尝试点击"查看更多"按钮
                        if self._try_load_more_comments():
                            no_new_comments_count -= 1  # 如果成功点击，给一次机会
                        
                        if no_new_comments_count >= max_no_new_attempts:
                            print("多次未获取到新评论，可能已到达末页")
                            break
                    
                except Exception as e:
                    print(f"爬取第 {page} 页时出错: {str(e)}")
                    no_new_comments_count += 1
                    if no_new_comments_count >= 3:
                        print("连续多次爬取出错，停止爬取")
                        break
            
            print(f"\n评论爬取完成！共获取 {len(self.comments)} 条评论")
            
            # 尝试提取评论的回复内容(可选功能)
            try:
                print("\n是否尝试提取评论回复？这可能需要额外的时间 (y/n):")
                extract_replies = input().strip().lower() == 'y'
                
                if extract_replies and self.comments:
                    # 先保存当前爬取的结果
                    print("已保存主评论，开始提取回复评论...")
                    
                    # 提取回复评论
                    replies = self._try_extract_all_replies()
                    
                    if replies:
                        print(f"\n成功提取 {len(replies)} 条回复评论！")
                        
                        # 创建回复评论的CSV文件
                        replies_file = self.output_file.replace('.csv', '_replies.csv')
                        with open(replies_file, mode='w', encoding='utf-8-sig', newline='') as rf:
                            # 回复可能缺少某些字段，确保兼容
                            reply_writer = csv.DictWriter(rf, fieldnames=fieldnames)
                            reply_writer.writeheader()
                            
                            # 写入回复数据
                            for reply in replies:
                                try:
                                    # 填充缺失的字段
                                    for field in fieldnames:
                                        if field not in reply:
                                            reply[field] = ''
                                    reply_writer.writerow(reply)
                                except Exception as e:
                                    print(f"写入回复时出错: {str(e)}")
                        
                        print(f"回复评论已保存到文件: {replies_file}")
                        
                        # 将回复评论也添加到主评论列表
                        self.comments.extend(replies)
            except Exception as e:
                print(f"提取回复评论过程中出错: {str(e)}")
            
            print(f"\n全部评论爬取完成！共获取 {len(self.comments)} 条评论(含回复)")
            print(f"评论已保存到文件: {self.output_file}")
            return self.comments
            
        except Exception as e:
            print(f"爬虫运行出错: {str(e)}")
            return []
        
        finally:
            # 结束爬取状态 (如果定义了这个变量)
            if 'is_crawling' in locals():
                is_crawling = False
            
            # 关闭文件和浏览器
            f.close()
            if self.driver:
                self.driver.quit()
    
    def get_output_file(self):
        """获取输出文件路径"""
        return self.output_file

    def _parse_comment_details(self, comment):
        """解析评论详细信息，提取更全面的数据
        
        提取内容包括：
        - 基本信息（ID、内容、时间、点赞数）
        - 用户信息（昵称、ID、关注数、粉丝数等）
        - 位置信息
        - 回复信息
        - 额外标签（热评、置顶等）
        """
        try:
            # 基本评论信息
            comment_id = comment.get('cid', '') or str(comment.get('id', ''))
            text = comment.get('text', '').strip()
            create_time = comment.get('create_time', 0)
            date = str(datetime.datetime.fromtimestamp(create_time))
            digg_count = comment.get('digg_count', 0)  # 点赞数
            
            # 用户信息
            user = comment.get('user', {})
            nickname = user.get('nickname', '未知用户')
            user_id = user.get('uid', '')
            sec_uid = user.get('sec_uid', '')
            avatar = user.get('avatar_thumb', {}).get('url_list', [''])[0]
            
            # 位置和IP信息
            ip_label = comment.get('ip_label', '未知')
            
            # 回复信息
            reply_count = comment.get('reply_comment_total', 0)
            reply_to_userid = comment.get('reply_to_userid', '')
            reply_to_nickname = comment.get('reply_to_nickname', '')
            
            # 特殊标记
            is_top = bool(comment.get('stick_position', 0))  # 是否置顶
            is_hot = bool(comment.get('is_hot_comment', 0))  # 是否热评
            
            # 额外信息（如果有）
            extra_info = {}
            if comment.get('text_extra'):
                extra_info['hashtags'] = [item.get('hashtag_name') for item in comment.get('text_extra', []) if item.get('hashtag_name')]
            
            # 高级内容分析
            # 提取@用户
            at_users = []
            if comment.get('text_extra'):
                at_users = [item.get('user_id') for item in comment.get('text_extra', []) if item.get('type') == 0]
            
            # 创建全面的评论数据字典
            comment_data = {
                '评论ID': comment_id,
                '昵称': nickname,
                '用户ID': user_id,
                '用户sec_id': sec_uid,
                '头像': avatar,
                '地区': ip_label,
                '时间': date,
                '评论': text,
                '点赞数': digg_count,
                '回复数': reply_count,
                '回复给用户': reply_to_nickname,
                '回复给用户ID': reply_to_userid,
                '是否置顶': '是' if is_top else '否',
                '是否热评': '是' if is_hot else '否',
                '包含话题': ','.join(extra_info.get('hashtags', [])),
                '提及用户': ','.join(at_users)
            }
            
            return comment_data
            
        except Exception as e:
            print(f"解析评论详情时出错: {str(e)}")
            # 返回基本信息作为备选
            return {
                '评论ID': comment.get('cid', '') or str(comment.get('id', '')),
                '昵称': comment.get('user', {}).get('nickname', '未知'),
                '地区': comment.get('ip_label', '未知'),
                '时间': str(datetime.datetime.fromtimestamp(comment.get('create_time', 0))),
                '评论': comment.get('text', ''),
                '点赞数': comment.get('digg_count', 0)
            }

    def _extract_reply_comments(self, comment_id):
        """尝试提取某条评论的回复评论
        
        Args:
            comment_id: 主评论的ID
            
        Returns:
            list: 回复评论列表，如果无法提取则返回空列表
        """
        try:
            # 尝试找到对应评论
            comment_elem = self.driver.find_element(f'xpath://div[@data-comment-id="{comment_id}" or @id="{comment_id}"]')
            if not comment_elem:
                return []
                
            # 滚动到该评论
            self.driver.scroll.to_element(comment_elem)
            time.sleep(0.5)
            
            # 尝试点击"查看更多回复"按钮
            try:
                more_reply_btn = comment_elem.find_element('xpath:.//span[contains(text(), "查看") and contains(text(), "回复")]')
                if more_reply_btn:
                    more_reply_btn.click()
                    time.sleep(1.5)  # 等待回复加载
            except:
                pass
                
            # 查找所有回复元素
            reply_elements = comment_elem.find_elements('xpath:.//div[contains(@class, "reply-item") or contains(@class, "ReplyItem")]')
            
            replies = []
            for reply_elem in reply_elements:
                try:
                    # 提取回复内容
                    reply_text = reply_elem.text
                    # 查找回复者昵称
                    replier = reply_elem.find_element('xpath:.//span[contains(@class, "nickname") or contains(@class, "user-name")]').text
                    
                    # 提取回复ID (如果可能)
                    reply_id = reply_elem.get_attribute('data-id') or reply_elem.get_attribute('id') or f"{comment_id}_reply_{len(replies)}"
                    
                    # 提取其他可能的信息
                    like_count_elem = reply_elem.find_element('xpath:.//span[contains(@class, "like") or contains(@class, "digg")]')
                    like_count = like_count_elem.text if like_count_elem else "0"
                    
                    # 创建回复字典
                    reply = {
                        '评论ID': reply_id,
                        '昵称': replier,
                        '评论': reply_text,
                        '点赞数': like_count,
                        '回复给用户ID': comment_id,
                        '是否回复评论': '是'
                    }
                    
                    replies.append(reply)
                except Exception as e:
                    print(f"提取单条回复时出错: {str(e)}")
                    
            return replies
            
        except Exception as e:
            print(f"提取评论 {comment_id} 的回复时出错: {str(e)}")
            return []
            
    def _try_extract_all_replies(self):
        """尝试提取所有主评论的回复"""
        all_replies = []
        
        # 限制提取回复的评论数，避免耗时过长
        top_comments = list(self.comment_ids)[:50]  # 最多提取前50条评论的回复
        
        print(f"\n尝试提取 {len(top_comments)} 条主评论的回复...")
        
        for i, comment_id in enumerate(top_comments):
            if i % 5 == 0:
                print(f"正在提取第 {i+1}/{len(top_comments)} 条评论的回复...")
                
            replies = self._extract_reply_comments(comment_id)
            if replies:
                print(f"评论 {comment_id} 获取到 {len(replies)} 条回复")
                all_replies.extend(replies)
                
        return all_replies


def main():
    """主函数"""
    print("=" * 60)
    print("抖音视频评论爬取工具 - 强化版")
    print("=" * 60)
    
    # 获取视频URL
    video_url = input("请输入抖音视频URL (例如: https://www.douyin.com/video/7353500880198536457): ")
    
    # 设置最大爬取页数
    try:
        pages_input = input("请输入最大爬取页数 (直接回车表示爬取全部评论): ")
        max_pages = int(pages_input) if pages_input.strip() else None
    except ValueError:
        max_pages = None
    
    if max_pages is None:
        print("将爬取全部评论，直到没有更多评论为止")
    else:
        print(f"将爬取最多 {max_pages} 页评论")
    
    # 询问是否使用正常模式
    use_normal_mode = input("是否使用正常浏览器模式 (可以登录账号) [Y/n]: ").lower() != 'n'
    
    # 如果使用正常模式，询问是否需要先登录
    login_first = False
    if use_normal_mode:
        login_first = input("是否需要在爬取前先登录抖音账号 [y/N]: ").lower() == 'y'
    
    # 创建爬虫实例
    crawler = DouyinCommentCrawler(
        video_url=video_url, 
        max_pages=max_pages, 
        use_normal_mode=use_normal_mode,
        login_first=login_first
    )
    
    # 执行爬取
    comments = crawler.start_crawler()
    
    # 打印爬取结果
    if comments:
        print(f"\n成功爬取 {len(comments)} 条评论")
        print(f"评论已保存到文件: {crawler.get_output_file()}")
    else:
        print("\n爬取失败或未获取到评论")


if __name__ == "__main__":
    main() 