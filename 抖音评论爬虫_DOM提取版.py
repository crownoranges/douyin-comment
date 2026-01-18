# -*- coding: utf-8 -*-
"""抖音评论爬虫 - DOM提取版（精简版）"""

from DrissionPage import ChromiumPage
import csv
import time
import datetime
import msvcrt
import os
import re

class DouyinCommentCrawler:
    def __init__(self, video_url):
        self.video_url = video_url
        self.driver = None
    
    def get_video_title(self):
        """提取视频标题"""
        try:
            title = self.driver.run_js("""
                var title = (document.querySelector('meta[property="og:title"]') || {}).content || 
                           document.title || '未知视频';
                return title.replace(/\s*[-–—|]\s*抖音.*$/, '').trim();
            """)
            title = re.sub(r'[<>:"/\\|?*]', '_', title)
            return title[:50] if title else '未知视频'
        except:
            return '未知视频'
    
    def scroll_comments(self):
        """滚动加载评论"""
        self.driver.run_js("""
            var allDivs = document.querySelectorAll('div');
            for (var i = 0; i < allDivs.length; i++) {
                var div = allDivs[i];
                if (div.scrollHeight > div.clientHeight + 50 && 
                    (div.innerHTML.includes('评论') || div.className.includes('comment'))) {
                    div.setAttribute('tabindex', '-1');
                    div.focus();
                    window.__commentContainer = div;
                    break;
                }
            }
        """)
        
        print("滚动加载中...")
        for i in range(200):
            self.driver.run_js("var c = window.__commentContainer; if(c) c.scrollTop += 2000;")
            time.sleep(0.2)
        time.sleep(2)
    
    def extract_comments(self):
        """提取评论"""
        comments = self.driver.run_js("""
            // 查找评论元素
            var commentItems = document.querySelectorAll('[data-e2e="comment-item"]');
            var infoWraps = document.querySelectorAll('[class*="comment-item-info-wrap"]');
            
            if (infoWraps.length > commentItems.length) {
                var parentSet = new Set();
                infoWraps.forEach(function(wrap) {
                    var parent = wrap.parentElement;
                    if (parent && parent.parentElement) {
                        parentSet.add(parent.parentElement);
                    }
                });
                commentItems = Array.from(parentSet);
            }
            
            var comments = [];
            var processedIds = new Set();
            
            commentItems.forEach(function(item, index) {
                try {
                    var commentId = item.getAttribute('data-id') || 'comment_' + index;
                    if (processedIds.has(commentId)) return;
                    processedIds.add(commentId);
                    
                    // 昵称
                    var nicknameEl = item.querySelector('span.arnSiSbK.xtTwhlGw');
                    var nickname = nicknameEl ? nicknameEl.textContent.trim() : '';
                    
                    // 用户链接
                    var userLinkEl = item.querySelector('a.uz1VJwFY');
                    var userLink = userLinkEl ? userLinkEl.getAttribute('href') : '';
                    if (userLink && userLink.startsWith('//')) userLink = 'https:' + userLink;
                    
                    // 评论内容
                    var content = '';
                    var contentEl = item.querySelector('span.WFJiGxr7');
                    if (contentEl) {
                        content = contentEl.textContent.trim();
                    } else {
                        var arnSpans = item.querySelectorAll('span.arnSiSbK');
                        for (var i = 0; i < arnSpans.length; i++) {
                            var text = arnSpans[i].textContent.trim();
                            if (text && text !== nickname && text.length > 1) {
                                content = text;
                                break;
                            }
                        }
                    }
                    
                    if (!content || content === nickname) {
                        var allSpans = item.querySelectorAll('span, p');
                        var longestText = '';
                        for (var j = 0; j < allSpans.length; j++) {
                            var text = allSpans[j].textContent.trim();
                            if (text.length > longestText.length && text.length > 2 && 
                                text !== nickname && /[\u4e00-\u9fa5a-zA-Z]/.test(text)) {
                                longestText = text;
                            }
                        }
                        content = longestText;
                    }
                    
                    if (!content || content.length < 1) return;
                    
                    // 时间和地区
                    var timeText = '', ipLabel = '';
                    var timeIpEl = item.querySelector('div.fJhvAqos span');
                    if (timeIpEl) {
                        var timeIpText = timeIpEl.textContent.trim();
                        if (timeIpText.includes('·')) {
                            var parts = timeIpText.split('·');
                            timeText = parts[0].trim();
                            ipLabel = parts[1].trim();
                        } else {
                            timeText = timeIpText;
                        }
                    }
                    
                    // 点赞数
                    var likeEl = item.querySelector('p.xZhLomAs span');
                    var likeCount = '0';
                    if (likeEl) {
                        var match = likeEl.textContent.trim().match(/\\d+/);
                        likeCount = match ? match[0] : '0';
                    }
                    
                    // 回复数
                    var replyEl = item.querySelector('div.f8nOLNQF span');
                    var replyCount = 0;
                    if (replyEl) {
                        var match = replyEl.textContent.trim().match(/\\d+/);
                        replyCount = match ? parseInt(match[0]) : 0;
                    }
                    
                    comments.push({
                        commentId: commentId,
                        nickname: nickname,
                        userLink: userLink,
                        content: content,
                        time: timeText,
                        ip: ipLabel,
                        likes: likeCount,
                        replies: replyCount
                    });
                } catch (e) {}
            });
            
            return comments;
        """)
        
        print(f"提取到 {len(comments)} 条评论")
        return comments
    
    def start(self, need_login=False):
        """开始爬取"""
        os.makedirs('crawled_comments', exist_ok=True)
        self.driver = ChromiumPage()
        
        if need_login:
            self.driver.get("https://www.douyin.com/")
            print("请登录，完成后按Enter...")
            start_time = time.time()
            while True:
                if time.time() - start_time > 120:
                    break
                try:
                    if self.driver.run_js("return document.querySelector('[class*=\"avatar\"]') !== null;"):
                        print("已登录")
                        break
                except:
                    pass
                if msvcrt.kbhit() and msvcrt.getch() == b'\r':
                    break
                time.sleep(0.5)
        
        print(f"访问: {self.video_url}")
        self.driver.get(self.video_url)
        time.sleep(5)
        
        video_title = self.get_video_title()
        print(f"视频: {video_title}")
        
        self.scroll_comments()
        comments = self.extract_comments()
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'crawled_comments/{video_title}_{timestamp}.csv'
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '评论ID', '昵称', '用户ID', '用户sec_id', '头像', '地区', '时间', 
                '评论', '点赞数', '回复数', '回复给用户', '回复给用户ID', 
                '是否置顶', '是否热评', '包含话题', '提及用户'
            ])
            writer.writeheader()
            
            for comment in comments:
                writer.writerow({
                    '评论ID': comment.get('commentId', ''),
                    '昵称': comment.get('nickname', ''),
                    '用户ID': '',
                    '用户sec_id': '',
                    '头像': comment.get('userLink', ''),
                    '地区': comment.get('ip', ''),
                    '时间': comment.get('time', ''),
                    '评论': comment.get('content', ''),
                    '点赞数': comment.get('likes', '0'),
                    '回复数': comment.get('replies', '0'),
                    '回复给用户': '',
                    '回复给用户ID': '',
                    '是否置顶': '否',
                    '是否热评': '否',
                    '包含话题': '',
                    '提及用户': ''
                })
        
        self.driver.quit()
        print(f"完成！保存: {output_file}")
        return output_file, len(comments)

if __name__ == '__main__':
    url = input("视频URL（回车=测试URL）: ").strip() or "https://www.douyin.com/video/7587571141704043825"
    need_login = input("需要登录? (y/n): ").lower() == 'y'
    
    crawler = DouyinCommentCrawler(url)
    crawler.start(need_login=need_login)

