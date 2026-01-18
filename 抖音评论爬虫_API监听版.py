# -*- coding: utf-8 -*-
"""抖音评论爬虫 - API监听版（精简版）"""

from DrissionPage import ChromiumPage
import csv
import time
import datetime
import re
import os

class DouyinCommentCrawler:
    def __init__(self, video_url):
        self.video_url = video_url
        self.driver = None
        self.comments = []
    
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
    
    def parse_comment(self, comment):
        """解析评论数据"""
        user = comment.get('user', {})
        return {
            '评论ID': comment.get('cid', ''),
            '昵称': user.get('nickname', ''),
            '用户ID': user.get('uid', ''),
            '用户sec_id': user.get('sec_uid', ''),
            '头像': user.get('avatar_thumb', {}).get('url_list', [''])[0],
            '地区': comment.get('ip_label', ''),
            '时间': str(datetime.datetime.fromtimestamp(comment.get('create_time', 0))),
            '评论': comment.get('text', '').strip(),
            '点赞数': comment.get('digg_count', 0),
            '回复数': comment.get('reply_comment_total', 0),
            '回复给用户': comment.get('reply_to_username', ''),
            '回复给用户ID': comment.get('reply_to_userid', ''),
            '是否置顶': '是' if comment.get('stick_position', 0) > 0 else '否',
            '是否热评': '是' if comment.get('user_digged', 0) > 0 else '否',
            '包含话题': '',
            '提及用户': ''
        }
    
    def start(self, need_login=True):
        """开始爬取"""
        os.makedirs('crawled_comments', exist_ok=True)
        self.driver = ChromiumPage()
        
        if need_login:
            self.driver.get("https://www.douyin.com/")
            print("请在浏览器中登录，完成后按Enter...")
            input()
        
        self.driver.listen.start('aweme/v1/web/comment/list/')
        self.driver.get(self.video_url)
        time.sleep(5)
        
        video_title = self.get_video_title()
        print(f"视频: {video_title}")
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'crawled_comments/{video_title}_{timestamp}.csv'
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                '评论ID', '昵称', '用户ID', '用户sec_id', '头像', '地区', '时间', 
                '评论', '点赞数', '回复数', '回复给用户', '回复给用户ID', 
                '是否置顶', '是否热评', '包含话题', '提及用户'
            ])
            writer.writeheader()
            
            print("滚动并监听API...")
            for i in range(200):
                if i == 0:
                    self.driver.run_js("""
                        var allDivs = document.querySelectorAll('div');
                        for (var j = 0; j < allDivs.length; j++) {
                            var div = allDivs[j];
                            if (div.scrollHeight > div.clientHeight + 50 && 
                                (div.innerHTML.includes('评论') || div.className.includes('comment'))) {
                                window.__commentContainer = div;
                                break;
                            }
                        }
                    """)
                
                self.driver.run_js("var c = window.__commentContainer; if(c) c.scrollTop += 2000; else window.scrollBy(0, 2000);")
                
                if (i + 1) % 50 == 0:
                    print(f"已获取 {len(self.comments)} 条")
                
                time.sleep(0.3)
                
                while True:
                    resp = self.driver.listen.wait(timeout=0.1)
                    if not resp:
                        break
                    try:
                        for comment in resp.response.body.get('comments', []):
                            parsed = self.parse_comment(comment)
                            if parsed['评论ID'] not in [c['评论ID'] for c in self.comments]:
                                self.comments.append(parsed)
                                writer.writerow(parsed)
                    except:
                        pass
            
            time.sleep(2)
            for _ in range(10):
                resp = self.driver.listen.wait(timeout=1)
                if not resp:
                    break
                try:
                    for comment in resp.response.body.get('comments', []):
                        parsed = self.parse_comment(comment)
                        if parsed['评论ID'] not in [c['评论ID'] for c in self.comments]:
                            self.comments.append(parsed)
                            writer.writerow(parsed)
                except:
                    pass
        
        self.driver.quit()
        print(f"完成！共 {len(self.comments)} 条评论")
        print(f"保存: {output_file}")
        return output_file, len(self.comments)

if __name__ == '__main__':
    url = input("视频URL: ").strip() or "https://www.douyin.com/video/7587571141704043825"
    need_login = input("需要登录? (y/n): ").lower() == 'y'
    
    crawler = DouyinCommentCrawler(url)
    crawler.start(need_login=need_login)

