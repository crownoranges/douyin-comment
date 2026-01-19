# -*- coding: utf-8 -*-
"""抖音评论爬虫 - 含回复版（精简版）"""

from DrissionPage import ChromiumPage
import time
import csv
import os
import re
from datetime import datetime

class DouyinCommentCrawlerWithReplies:
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
                    window.__commentContainer = div;
                    break;
                }
            }
        """)
        
        print("滚动加载...")
        for i in range(200):
            self.driver.run_js("var c = window.__commentContainer; if(c) c.scrollTop += 2000;")
            time.sleep(0.2)
        time.sleep(2)
    
    def extract_comments(self):
        """提取评论"""
        return self.driver.run_js("""
            var commentItems = document.querySelectorAll('[data-e2e="comment-item"]');
            var infoWraps = document.querySelectorAll('[class*="comment-item-info-wrap"]');
            
            if (infoWraps.length > commentItems.length) {
                var parentSet = new Set();
                infoWraps.forEach(function(wrap) {
                    if (wrap.parentElement && wrap.parentElement.parentElement) {
                        parentSet.add(wrap.parentElement.parentElement);
                    }
                });
                commentItems = Array.from(parentSet);
            }
            
            var comments = [];
            commentItems.forEach(function(item, index) {
                try {
                    var id = item.getAttribute('data-id') || 'comment_' + index;
                    var nickname = (item.querySelector('span.arnSiSbK.xtTwhlGw') || {}).textContent || '';
                    
                    // 评论内容（100%可靠方法）
                    var content = '';
                    var contentEl = item.querySelector('span.WFJiGxr7') || 
                                   (item.querySelector('div.C7LroK_h') || {}).querySelector('span');
                    if (contentEl) content = contentEl.textContent.trim();
                    if (!content) return;
                    
                    var timeIpEl = item.querySelector('div.fJhvAqos span');
                    var timeText = '', ipLabel = '';
                    if (timeIpEl) {
                        var parts = timeIpEl.textContent.trim().split('·');
                        timeText = parts[0] || '';
                        ipLabel = parts[1] || '';
                    }
                    
                    var likeEl = item.querySelector('p.xZhLomAs span');
                    var likes = likeEl ? (likeEl.textContent.match(/\\d+/) || ['0'])[0] : '0';
                    
                    var replyEl = item.querySelector('div.f8nOLNQF span');
                    var replies = replyEl ? parseInt((replyEl.textContent.match(/\\d+/) || ['0'])[0]) : 0;
                    
                    comments.push({
                        id: id,
                        nickname: nickname,
                        content: content,
                        time: timeText,
                        ip: ipLabel,
                        likes: likes,
                        replies: replies,
                        level: 1
                    });
                } catch (e) {}
            });
            
            return comments;
        """)
    
    def expand_replies(self, max_expand, primary_ids):
        """展开并提取回复"""
        result = self.driver.run_js(f"""
            var clicked = 0;
            var allElements = document.querySelectorAll('div, span, button');
            
            for (var i = 0; i < allElements.length && clicked < {max_expand}; i++) {{
                var text = allElements[i].textContent.trim();
                if (text.match(/展开\\d+条回复/) && !text.match(/已展开/)) {{
                    try {{
                        allElements[i].click();
                        clicked++;
                    }} catch(e) {{}}
                }}
            }}
            
            return clicked;
        """)
        
        print(f"展开了 {result} 个回复")
        if result > 0:
            time.sleep(3)
            all_comments = self.extract_comments()
            replies = [c for c in all_comments if c['id'] not in primary_ids]
            for r in replies:
                r['level'] = 2
            return replies
        return []
    
    def save_csv(self, comments, video_title):
        """保存CSV"""
        os.makedirs('crawled_comments', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'crawled_comments/{video_title}_{timestamp}_with_replies.csv'
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '评论ID', '层级', '昵称', '地区', '时间', '评论内容', '点赞数', '回复数'
            ])
            writer.writeheader()
            for c in comments:
                writer.writerow({
                    '评论ID': c['id'],
                    '层级': c['level'],
                    '昵称': c['nickname'],
                    '地区': c['ip'],
                    '时间': c['time'],
                    '评论内容': c['content'],
                    '点赞数': c['likes'],
                    '回复数': c['replies']
                })
        
        return output_file
    
    def start(self, need_login=False, max_replies_to_expand=10):
        """开始爬取"""
        self.driver = ChromiumPage()
        
        print(f"访问: {self.video_url}")
        self.driver.get(self.video_url)
        time.sleep(3)
        
        if need_login:
            print("请登录，完成后按Enter...")
            input()
        
        video_title = self.get_video_title()
        print(f"视频: {video_title}")
        
        self.scroll_comments()
        
        print("提取一级评论...")
        primary_comments = self.extract_comments()
        print(f"一级评论: {len(primary_comments)} 条")
        
        print(f"展开回复（最多{max_replies_to_expand}个）...")
        primary_ids = set(c['id'] for c in primary_comments)
        secondary_comments = self.expand_replies(max_replies_to_expand, primary_ids)
        print(f"二级评论: {len(secondary_comments)} 条")
        
        all_comments = primary_comments + secondary_comments
        print(f"总计: {len(all_comments)} 条")
        
        output_file = self.save_csv(all_comments, video_title)
        print(f"保存: {output_file}")
        
        self.driver.quit()
        return output_file, len(all_comments)

if __name__ == '__main__':
    url = input("视频URL（回车=测试）: ").strip() or "https://www.douyin.com/video/7587571141704043825"
    expand = int(input("展开几个回复? (默认10): ").strip() or "10")
    
    crawler = DouyinCommentCrawlerWithReplies(url)
    crawler.start(need_login=False, max_replies_to_expand=expand)

