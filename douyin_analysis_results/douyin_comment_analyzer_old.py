"""
抖音视频评论爬取与数据可视化分析工具

功能：
1. 自动爬取指定抖音视频的评论数据
2. 将评论数据保存为CSV格式
3. 生成评论词云图
4. 评论情感分析与地区分布可视化

日期: 2024年
"""

import time
import json
import datetime
import csv
import os
import random
import jieba
import pandas as pd
import numpy as np
from PIL import Image
import wordcloud
import matplotlib.pyplot as plt
from pyecharts import options as opts
from pyecharts.charts import Pie, Bar, Map, WordCloud as PyechartsWordCloud
from pyecharts.globals import ThemeType
from collections import Counter
from DrissionPage import ChromiumPage


class DouyinCommentCrawler:
    """抖音评论爬虫类"""
    
    def __init__(self, video_url=None, video_id=None, max_pages=None):
        """
        初始化爬虫
        :param video_url: 视频URL，例如 https://www.douyin.com/video/7353500880198536457
        :param video_id: 视频ID，如果提供了video_url则可不提供
        :param max_pages: 最大爬取页数，默认为None表示爬取全部评论
        """
        self.video_url = video_url
        self.video_id = video_id if video_id else self._extract_video_id(video_url)
        self.max_pages = max_pages
        self.comments = []
        self.driver = None
        self.comment_ids = set()  # 用于去重的评论ID集合
        
        # 使用当前日期和时间创建唯一的文件名
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = f"douyin_comments_{self.video_id}_{current_time}.csv"
    
    def _extract_video_id(self, url):
        """从URL中提取视频ID"""
        if not url:
            raise ValueError("需要提供视频URL或视频ID")
        return url.split("/")[-1].split("?")[0]
    
    def start_crawler(self):
        """启动爬虫"""
        print(f"开始爬取视频 {self.video_id} 的评论...")
        
        # 创建CSV文件
        f = open(self.output_file, mode='w', encoding='utf-8-sig', newline='')
        fieldnames = ['评论ID', '昵称', '地区', '时间', '评论', '点赞数']
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        try:
            # 初始化浏览器
            self.driver = ChromiumPage()
            # 监听评论数据API
            self.driver.listen.start('aweme/v1/web/comment/list/')
            
            # 访问视频页面
            if self.video_url:
                self.driver.get(self.video_url)
            else:
                self.driver.get(f'https://www.douyin.com/video/{self.video_id}')
            
            # 等待页面加载
            time.sleep(5)
            
            # 尝试点击"查看更多评论"按钮（如果存在）
            try:
                more_comment_btn = self.driver.find_element('xpath://div[contains(text(), "查看更多评论")]')
                if more_comment_btn:
                    more_comment_btn.click()
                    time.sleep(2)
            except:
                print("没有找到"查看更多评论"按钮，继续使用滚动加载评论")
            
            # 爬取评论
            page = 0
            no_new_comments_count = 0  # 连续没有新评论的次数
            last_comment_count = 0     # 上一次的评论总数
            retry_count = 0            # 当前页面重试次数
            max_retry = 5              # 最大重试次数
            
            # 如果设置了最大页数，则限制页数；否则一直爬取直到没有更多评论
            while self.max_pages is None or page < self.max_pages:
                try:
                    page += 1
                    print(f'正在爬取第 {page} 页评论...')
                    
                    # 使用不同的滚动策略
                    if page % 3 == 0:
                        # 精确滚动到评论区
                        try:
                            comment_area = self.driver.find_element('xpath://div[contains(@class, "comment-mainContent")]')
                            if comment_area:
                                self.driver.scroll.to_element(comment_area, center=True)
                                time.sleep(1)
                        except:
                            pass
                        
                        # 平滑滚动到底部
                        self.driver.scroll.to_bottom(smooth=True)
                    else:
                        # 先快速滚动一段距离，再滚动到底部
                        self.driver.scroll.down(300)
                        time.sleep(0.5)
                        self.driver.scroll.to_bottom()
                    
                    # 随机等待时间，模拟人工浏览
                    wait_time = 1 + random.random() * 2
                    time.sleep(wait_time)
                    
                    # 等待数据包
                    resp = self.driver.listen.wait(timeout=5)
                    
                    if not resp:
                        print(f"未检测到新的评论数据，尝试继续... (重试 {retry_count+1}/{max_retry})")
                        retry_count += 1
                        
                        if retry_count >= max_retry:
                            no_new_comments_count += 1
                            retry_count = 0
                            
                            if no_new_comments_count >= 3:
                                print("连续多次未检测到新评论，尝试使用其他方法加载评论")
                                
                                # 尝试其他方法触发评论加载
                                try:
                                    # 尝试点击"展开更多"按钮
                                    expand_btns = self.driver.find_elements('xpath://span[contains(text(), "展开") or contains(text(), "更多")]')
                                    if expand_btns:
                                        for btn in expand_btns[:3]:  # 最多点击前3个
                                            try:
                                                btn.click()
                                                time.sleep(1)
                                            except:
                                                pass
                                except:
                                    pass
                                
                                # 再尝试一次，如果还是失败则认为已到达末页
                                if no_new_comments_count >= 5:
                                    print("已尝试多种方法但无法加载更多评论，可能已到达末页")
                                    break
                        
                        # 再次尝试不同的滚动方式
                        self.driver.scroll.up(200)
                        time.sleep(1)
                        self.driver.scroll.to_bottom()
                        continue
                    
                    # 重置重试计数器
                    retry_count = 0
                    
                    # 解析JSON数据
                    json_data = resp.response.body
                    
                    if not json_data or 'comments' not in json_data:
                        print(f"未获取到有效评论数据，尝试继续... (尝试 {no_new_comments_count+1}/3)")
                        no_new_comments_count += 1
                        if no_new_comments_count >= 3:
                            print("连续多次未获取到有效评论数据，可能已到达末页")
                            break
                        continue
                    
                    # 提取评论
                    comments = json_data['comments']
                    if not comments:
                        print("本页无评论数据，可能已到达末页")
                        no_new_comments_count += 1
                        if no_new_comments_count >= 3:
                            break
                        continue
                    
                    # 重置无新评论计数器（如果找到了评论）
                    no_new_comments_count = 0
                    
                    # 记录爬取前的评论数和评论ID数
                    comment_count_before = len(self.comments)
                    comment_id_count_before = len(self.comment_ids)
                    
                    # 处理评论数据
                    for comment in comments:
                        try:
                            comment_id = comment.get('cid', '') or str(comment.get('id', ''))
                            
                            # 如果已经处理过这个评论，则跳过
                            if comment_id in self.comment_ids:
                                continue
                            
                            # 添加到已处理集合
                            self.comment_ids.add(comment_id)
                            
                            nickname = comment['user']['nickname']
                            create_time = comment['create_time']
                            date = str(datetime.datetime.fromtimestamp(create_time))
                            ip_label = comment.get('ip_label', '未知')
                            text = comment['text']
                            digg_count = comment.get('digg_count', 0)  # 点赞数
                            
                            # 创建评论数据字典
                            comment_data = {
                                '评论ID': comment_id,
                                '昵称': nickname,
                                '地区': ip_label,
                                '时间': date,
                                '评论': text,
                                '点赞数': digg_count
                            }
                            
                            # 保存到列表和文件
                            self.comments.append(comment_data)
                            csv_writer.writerow(comment_data)
                            print(f"[{len(self.comments)}] 评论: {text[:30]}... - 来自: {nickname} - {ip_label}")
                            
                        except Exception as e:
                            print(f"处理评论时出错: {str(e)}")
                    
                    # 检查是否有新的评论被添加
                    comment_count_added = len(self.comments) - comment_count_before
                    comment_id_added = len(self.comment_ids) - comment_id_count_before
                    
                    print(f"本次获取了 {comment_count_added} 条新评论，累计 {len(self.comments)} 条")
                    
                    # 如果没有新的评论ID被添加，说明可能需要尝试其他方法或已到达末页
                    if comment_id_added == 0:
                        no_new_comments_count += 1
                        print(f"未获取到新评论ID，尝试继续... (尝试 {no_new_comments_count}/3)")
                        
                        # 尝试点击页面上的"查看更多回复"按钮
                        try:
                            more_reply_btns = self.driver.find_elements('xpath://span[contains(text(), "查看") and contains(text(), "回复")]')
                            if more_reply_btns:
                                for btn in more_reply_btns[:5]:  # 最多点击前5个
                                    try:
                                        btn.click()
                                        time.sleep(1)
                                    except:
                                        pass
                                # 点击了按钮后重置计数器，再次尝试
                                no_new_comments_count = 0
                        except:
                            pass
                        
                        if no_new_comments_count >= 3:
                            print("连续多次未获取到新评论，可能已到达末页")
                            
                            # 最后再尝试一次刷新页面的方法
                            if no_new_comments_count == 3:
                                print("尝试刷新页面后继续爬取...")
                                self.driver.refresh()
                                time.sleep(5)
                                no_new_comments_count = 2  # 给最后一次机会
                                continue
                            break
                    else:
                        # 有新评论，重置计数器
                        no_new_comments_count = 0
                    
                except Exception as e:
                    print(f"爬取第 {page} 页时出错: {str(e)}")
                    no_new_comments_count += 1
                    if no_new_comments_count >= 3:
                        print("连续多次爬取出错，停止爬取")
                        break
            
            print(f"评论爬取完成，共获取 {len(self.comments)} 条评论")
            return self.comments
            
        except Exception as e:
            print(f"爬虫运行出错: {str(e)}")
            return []
        
        finally:
            # 关闭文件和浏览器
            f.close()
            if self.driver:
                self.driver.quit()
    
    def get_output_file(self):
        """获取输出文件路径"""
        return self.output_file


class CommentAnalyzer:
    """评论分析与可视化类"""
    
    def __init__(self, csv_file=None, comments=None):
        """
        初始化分析器
        :param csv_file: CSV文件路径
        :param comments: 评论数据列表，如果没有提供CSV文件则使用此数据
        """
        self.csv_file = csv_file
        self.comments = comments
        self.df = None
        self.output_dir = "douyin_analysis_results"
        
        # 创建输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def find_latest_csv(self, video_id=None):
        """
        查找最新的评论CSV文件
        :param video_id: 可选的视频ID过滤条件
        :return: 最新CSV文件的路径，如果未找到则返回None
        """
        all_csv_files = []
        
        # 搜索当前目录下的所有CSV文件
        for file in os.listdir('.'):
            if file.startswith('douyin_comments_') and file.endswith('.csv'):
                # 如果指定了视频ID，则只查找该视频的CSV文件
                if video_id and video_id not in file:
                    continue
                all_csv_files.append(file)
        
        if not all_csv_files:
            return None
        
        # 按文件修改时间排序，返回最新的文件
        latest_file = max(all_csv_files, key=lambda x: os.path.getmtime(x))
        print(f"找到最新的CSV文件: {latest_file}")
        return latest_file
    
    def load_data(self):
        """加载数据"""
        if self.csv_file and os.path.exists(self.csv_file):
            self.df = pd.read_csv(self.csv_file)
            print(f"从 {self.csv_file} 加载了 {len(self.df)} 条评论")
        elif self.comments:
            self.df = pd.DataFrame(self.comments)
            print(f"从内存加载了 {len(self.df)} 条评论")
        else:
            # 尝试查找最新的CSV文件
            latest_csv = self.find_latest_csv()
            if latest_csv:
                self.csv_file = latest_csv
                self.df = pd.read_csv(self.csv_file)
                print(f"自动从最新文件 {self.csv_file} 加载了 {len(self.df)} 条评论")
            else:
                raise ValueError("需要提供CSV文件或评论数据")
        
        return self.df
    
    def generate_wordcloud(self, shape_img=None, output_file=None):
        """
        生成词云图
        :param shape_img: 形状图片路径
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        # 默认输出文件名
        if not output_file:
            output_file = os.path.join(self.output_dir, "comment_wordcloud.png")
        
        print("正在生成词云图...")
        
        # 合并所有评论
        content = ' '.join([str(i).replace('\n', '') for i in self.df['评论']])
        
        # 结巴分词
        jieba.setLogLevel(20)  # 设置日志级别，避免输出过多日志
        words = jieba.lcut(content)
        string = ' '.join(words)
        
        # 加载形状图片
        mask = None
        if shape_img and os.path.exists(shape_img):
            mask = np.array(Image.open(shape_img))
        
        # 设置停用词
        stopwords = {'了', '的', '我', '你', '是', '都', '把', '能', '就', '这', '还', 
                     '和', '啊', '在', '吧', '有', '也', '不', '呢', '吗', '啥', '怎么',
                     '一个', '什么', '一下', '一样', '一直', '为了', '可以', '那么'}
        
        # 配置词云
        wc = wordcloud.WordCloud(
            font_path='simhei.ttf' if os.path.exists('simhei.ttf') else None,  # 字体文件
            width=1000,  # 宽
            height=700,  # 高
            mask=mask,  # 词云形状
            background_color='white',  # 背景色
            max_words=200,  # 最大词数
            stopwords=stopwords,  # 停用词
            contour_width=1,  # 轮廓宽度
            contour_color='steelblue'  # 轮廓颜色
        )
        
        # 生成词云
        wc.generate(string)
        
        # 保存词云图
        wc.to_file(output_file)
        print(f"词云图已保存至: {output_file}")
        
        return output_file
    
    def analyze_location(self, output_file=None):
        """
        分析评论地区分布
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "location_analysis.html")
        
        print("正在分析评论地区分布...")
        
        # 统计地区
        location_count = self.df['地区'].value_counts()
        
        # 取前15个地区
        top_locations = location_count.head(15)
        
        # 创建饼图
        pie = (
            Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
            .add(
                "",
                [list(z) for z in zip(top_locations.index, top_locations.values)],
                radius=["30%", "75%"],
                center=["50%", "50%"],
                rosetype="radius",
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="评论地区分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="5%", pos_top="15%"),
                toolbox_opts=opts.ToolboxOpts()
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        )
        
        # 保存图表
        pie.render(output_file)
        print(f"地区分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_time_distribution(self, output_file=None):
        """
        分析评论时间分布
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "time_analysis.html")
        
        print("正在分析评论时间分布...")
        
        # 转换时间字符串为datetime对象
        self.df['时间'] = pd.to_datetime(self.df['时间'])
        
        # 提取小时
        self.df['小时'] = self.df['时间'].dt.hour
        
        # 统计每小时的评论数
        hour_count = self.df['小时'].value_counts().sort_index()
        
        # 创建条形图
        bar = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
            .add_xaxis(hour_count.index.tolist())
            .add_yaxis("评论数", hour_count.values.tolist())
            .set_global_opts(
                title_opts=opts.TitleOpts(title="评论时间分布 (小时)"),
                xaxis_opts=opts.AxisOpts(name="小时"),
                yaxis_opts=opts.AxisOpts(name="评论数"),
                toolbox_opts=opts.ToolboxOpts()
            )
        )
        
        # 保存图表
        bar.render(output_file)
        print(f"时间分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_hot_words(self, top_n=50, output_file=None):
        """
        分析热门词汇
        :param top_n: 热门词数量
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "hot_words.html")
        
        print(f"正在分析热门词汇 (Top {top_n})...")
        
        # 合并所有评论
        content = ' '.join([str(i).replace('\n', '') for i in self.df['评论']])
        
        # 结巴分词
        jieba.setLogLevel(20)
        words = jieba.lcut(content)
        
        # 过滤停用词
        stopwords = {'了', '的', '我', '你', '是', '都', '把', '能', '就', '这', '还', 
                     '和', '啊', '在', '吧', '有', '也', '不', '呢', '吗', '啥', '怎么',
                     '一个', '什么', '一下', '一样', '一直', '为了', '可以', '那么'}
        filtered_words = [word for word in words if len(word) > 1 and word not in stopwords]
        
        # 统计词频
        word_count = Counter(filtered_words)
        
        # 取前N个高频词
        top_words = word_count.most_common(top_n)
        
        # 创建词云图
        wordcloud_chart = (
            PyechartsWordCloud(init_opts=opts.InitOpts(
                theme=ThemeType.LIGHT, width="900px", height="500px")
            )
            .add(
                "",
                top_words,
                word_size_range=[20, 100],
                shape="circle"
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title=f"热门词汇 Top {top_n}"),
                toolbox_opts=opts.ToolboxOpts()
            )
        )
        
        # 保存图表
        wordcloud_chart.render(output_file)
        print(f"热门词汇分析已保存至: {output_file}")
        
        return output_file
    
    def run_all_analysis(self, shape_img=None):
        """
        运行所有分析
        :param shape_img: 词云形状图片
        :return: 所有输出文件的列表
        """
        if self.df is None:
            self.load_data()
        
        outputs = []
        
        # 生成词云
        outputs.append(self.generate_wordcloud(shape_img))
        
        # 地区分析
        outputs.append(self.analyze_location())
        
        # 时间分析
        outputs.append(self.analyze_time_distribution())
        
        # 热词分析
        outputs.append(self.analyze_hot_words())
        
        print(f"所有分析已完成，结果保存在 {self.output_dir} 目录")
        return outputs


def main():
    """主函数"""
    print("=" * 60)
    print("抖音视频评论爬取与数据可视化分析工具")
    print("=" * 60)
    
    # 询问用户操作类型
    mode = input("请选择操作类型：\n1. 爬取新的评论并分析\n2. 分析已有的CSV文件\n请输入选项编号 (1/2): ")
    
    if mode == "2":
        # 分析现有CSV文件
        print("\n== 分析已有评论数据 ==")
        
        # 初始化分析器 - 会自动查找最新的CSV文件
        analyzer = CommentAnalyzer()
        
        # 设置词云形状图片
        shape_img = input("请输入词云形状图片路径 (留空使用默认形状): ")
        if shape_img and not os.path.exists(shape_img):
            print(f"警告: 图片 {shape_img} 不存在，将使用默认形状")
            shape_img = None
        
        # 执行所有分析
        analyzer.run_all_analysis(shape_img=shape_img)
        
    else:
        # 爬取新的评论数据
        print("\n== 爬取新的评论数据 ==")
        
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
        
        # 设置词云形状图片
        shape_img = input("请输入词云形状图片路径 (留空使用默认形状): ")
        if shape_img and not os.path.exists(shape_img):
            print(f"警告: 图片 {shape_img} 不存在，将使用默认形状")
            shape_img = None
        
        # 创建爬虫实例
        crawler = DouyinCommentCrawler(video_url=video_url, max_pages=max_pages)
        
        # 执行爬取
        comments = crawler.start_crawler()
        
        if comments:
            # 获取输出文件
            csv_file = crawler.get_output_file()
            
            # 创建分析器
            analyzer = CommentAnalyzer(csv_file=csv_file)
            
            # 执行所有分析
            analyzer.run_all_analysis(shape_img=shape_img)
    
    print("程序运行完成!")


if __name__ == "__main__":
    main() 