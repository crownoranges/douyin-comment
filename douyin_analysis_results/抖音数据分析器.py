"""
抖音评论数据分析工具

功能：
1. 读取已爬取的CSV文件评论数据
2. 生成评论词云图
3. 分析评论地区分布
4. 分析评论时间分布
5. 分析热门词汇统计

日期: 2024年
"""

import os
import pandas as pd
import numpy as np
import jieba
from PIL import Image
import wordcloud
import matplotlib.pyplot as plt
from pyecharts import options as opts
from pyecharts.charts import Pie, Bar, Map, WordCloud as PyechartsWordCloud, Page
from pyecharts.globals import ThemeType
from collections import Counter
import re
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer


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
        self.output_dir = "analysis_results"
        self.comments_dir = "crawled_comments"  # 添加评论文件目录
        
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
        
        # 确保评论目录存在
        if not os.path.exists(self.comments_dir):
            os.makedirs(self.comments_dir)
        
        # 优先在评论目录中搜索CSV文件
        for file in os.listdir(self.comments_dir):
            if file.startswith('douyin_comments_') and file.endswith('.csv'):
                # 如果指定了视频ID，则只查找该视频的CSV文件
                if video_id and video_id not in file:
                    continue
                all_csv_files.append(os.path.join(self.comments_dir, file))
        
        # 如果评论目录中没有找到文件，则尝试在当前目录查找(兼容旧数据)
        if not all_csv_files:
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
    
    def analyze_sentiment(self, output_file=None):
        """
        简单的情感分析（基于关键词匹配）
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "sentiment_analysis.html")
        
        print("正在进行情感分析...")
        
        # 简单的情感词典
        positive_words = {'喜欢', '好看', '漂亮', '美丽', '精彩', '帅', '棒', '赞', '支持',
                          '开心', '感动', '完美', '厉害', '牛', '笑', '爱', '感谢', '谢谢'}
        
        negative_words = {'不好', '难看', '失望', '差劲', '烂', '丑', '太差', '恶心', '讨厌',
                          '无聊', '垃圾', '白痴', '傻', '枯燥', '不行', '假', '骗', '坑'}
        
        # 对每条评论进行情感分析
        sentiments = []
        for comment in self.df['评论']:
            comment_str = str(comment)
            words = jieba.lcut(comment_str)
            
            # 计算正面和负面词出现的次数
            pos_count = sum(1 for word in words if word in positive_words)
            neg_count = sum(1 for word in words if word in negative_words)
            
            # 根据正负词数量判断情感
            if pos_count > neg_count:
                sentiment = '正面'
            elif neg_count > pos_count:
                sentiment = '负面'
            else:
                sentiment = '中性'
            
            sentiments.append(sentiment)
        
        # 添加情感列
        self.df['情感'] = sentiments
        
        # 统计情感分布
        sentiment_count = self.df['情感'].value_counts()
        
        # 创建饼图
        pie = (
            Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
            .add(
                "",
                [list(z) for z in zip(sentiment_count.index, sentiment_count.values)],
                radius=["30%", "75%"],
                center=["50%", "50%"],
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="评论情感分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="5%", pos_top="15%"),
                toolbox_opts=opts.ToolboxOpts()
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        )
        
        # 保存图表
        pie.render(output_file)
        print(f"情感分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_user_portraits(self, output_file=None):
        """
        用户群体画像分析 - 基于评论数据分析用户特征
        
        分析维度:
        1. 用户活跃时间分布
        2. 用户地域分布热力图
        3. 用户语言风格特征
        4. 用户互动行为模式
        
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "user_portraits.html")
        
        print("正在生成用户群体画像分析...")
        
        # 检查是否有用户ID列 (从增强版爬虫获取的数据)
        has_user_data = '用户ID' in self.df.columns
        
        # 1. 提取评论中表达习惯的关键词
        language_patterns = {
            '网络流行语': ['yyds', '绝绝子', '真的蛮', '蕉绿', '破防了', '笑死', '太真了', '奈斯', '无语子'],
            '学生用语': ['学校', '作业', '考试', '老师', '课程', '学习', '上课', '复习'],
            '职场用语': ['工作', '项目', '公司', '老板', '会议', '客户', '同事', '薪资'],
            '情感表达': ['喜欢', '爱', '感动', '哭了', '泪目', '心疼', '心动', '可爱'],
            '批判性表达': ['垃圾', '难看', '失望', '差评', '不行', '假', '水平', '浪费']
        }
        
        # 分析用户语言风格
        language_stats = {category: 0 for category in language_patterns}
        
        for comment in self.df['评论']:
            comment_str = str(comment).lower()  # 转小写便于匹配
            for category, keywords in language_patterns.items():
                if any(keyword in comment_str for keyword in keywords):
                    language_stats[category] += 1
        
        # 创建语言风格分布饼图
        language_pie = (
            Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="500px", height="400px"))
            .add(
                "",
                [list(z) for z in zip(language_stats.keys(), language_stats.values())],
                radius=["30%", "75%"],
                center=["50%", "50%"],
                rosetype="radius",
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="用户语言风格分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="5%", pos_top="15%")
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        )
        
        # 2. 分析用户评论的时段分布 (反映用户活跃时间)
        if '时间' in self.df.columns:
            self.df['时间'] = pd.to_datetime(self.df['时间'])
            self.df['小时'] = self.df['时间'].dt.hour
            
            # 用户活跃时段分析
            hour_groups = {
                '深夜 (0-5点)': list(range(0, 6)),
                '早晨 (6-9点)': list(range(6, 10)),
                '工作时间 (10-17点)': list(range(10, 18)),
                '晚间 (18-23点)': list(range(18, 24))
            }
            
            time_stats = {group: 0 for group in hour_groups}
            for hour in self.df['小时']:
                for group, hours in hour_groups.items():
                    if hour in hours:
                        time_stats[group] += 1
            
            # 创建用户活跃时段分布图
            active_pie = (
                Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="500px", height="400px"))
                .add(
                    "",
                    [list(z) for z in zip(time_stats.keys(), time_stats.values())],
                    radius=["30%", "75%"],
                    center=["50%", "50%"],
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="用户活跃时段分布"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos_left="5%", pos_top="15%")
                )
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
            )
        else:
            active_pie = None
        
        # 3. 如果有用户ID数据，分析用户互动频率
        user_interaction = None
        if has_user_data:
            # 分析每个用户的评论数
            user_comment_counts = self.df['用户ID'].value_counts()
            interaction_levels = {
                '高频互动用户 (5条以上)': len(user_comment_counts[user_comment_counts >= 5]),
                '中频互动用户 (3-4条)': len(user_comment_counts[(user_comment_counts >= 3) & (user_comment_counts < 5)]),
                '低频互动用户 (1-2条)': len(user_comment_counts[user_comment_counts < 3])
            }
            
            # 创建用户互动频率图
            user_interaction = (
                Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="500px", height="400px"))
                .add(
                    "",
                    [list(z) for z in zip(interaction_levels.keys(), interaction_levels.values())],
                    radius=["30%", "75%"],
                    center=["50%", "50%"],
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="用户互动频率分布"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos_left="5%", pos_top="15%")
                )
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
            )
        
        # 4. 地域分布高级分析
        # 提取省份信息
        province_map = {}
        if '地区' in self.df.columns:
            for area in self.df['地区']:
                area_str = str(area)
                # 提取省份名称
                for province in ['北京', '上海', '广东', '江苏', '浙江', '四川', '湖北', '湖南', 
                               '河南', '河北', '山东', '山西', '陕西', '安徽', '福建', '江西', 
                               '广西', '云南', '贵州', '辽宁', '吉林', '黑龙江', '内蒙古', '新疆', 
                               '宁夏', '甘肃', '青海', '西藏', '天津', '重庆', '海南']:
                    if province in area_str:
                        if province in province_map:
                            province_map[province] += 1
                        else:
                            province_map[province] = 1
                        break
            
            # 如果提取到省份数据，创建中国地图
            if province_map:
                geo_data = [(province, count) for province, count in province_map.items()]
                
                # 创建地理热力图
                geo_map = (
                    Map(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="600px"))
                    .add(
                        "评论数量", 
                        geo_data, 
                        "china",
                        is_map_symbol_show=False
                    )
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="用户地理分布"),
                        visualmap_opts=opts.VisualMapOpts(
                            is_piecewise=True,
                            pieces=[
                                {"min": 10, "label": "10人以上", "color": "#5475f5"},
                                {"min": 5, "max": 9, "label": "5-9人", "color": "#5470c6"},
                                {"min": 3, "max": 4, "label": "3-4人", "color": "#91cc75"},
                                {"min": 1, "max": 2, "label": "1-2人", "color": "#fac858"},
                            ]
                        )
                    )
                )
        else:
            geo_map = None
        
        # 5. 综合分析 - 用户画像总结
        # 创建页面对象
        page = Page(layout=Page.SimplePageLayout)
        
        # 添加所有图表到页面
        if active_pie:
            page.add(active_pie)
        page.add(language_pie)
        if user_interaction:
            page.add(user_interaction)
        if 'geo_map' in locals() and geo_map:
            page.add(geo_map)
        
        # 保存综合分析页面
        page.render(output_file)
        print(f"用户群体画像分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_interaction_network(self, output_file=None):
        """
        分析评论互动关系网络，生成用户互动关系图
        
        此功能可以识别：
        1. 用户之间的回复关系
        2. 中心用户和意见领袖
        3. 互动热点和讨论集群
        
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "interaction_network.html")
        
        print("正在分析用户互动关系网络...")
        
        # 检查数据是否包含回复关系
        has_reply_data = '回复给用户ID' in self.df.columns and '用户ID' in self.df.columns
        reply_relation_found = False
        
        # 如果没有完整的回复数据，检查评论内容中的@关系
        if not has_reply_data:
            print("未找到完整回复关系数据，尝试从评论内容中提取@关系...")
            
            # 创建用户ID列和回复列（如果不存在）
            if '用户ID' not in self.df.columns:
                self.df['用户ID'] = self.df['昵称'].apply(lambda x: str(x)[:8] + str(hash(x))[-4:])
            
            if '回复给用户ID' not in self.df.columns:
                # 初始化回复关系列
                self.df['回复给用户ID'] = None
                
                # 从评论中提取@用户名
                at_pattern = re.compile(r'@([^\s:：]+)')
                
                # 用户名到ID的映射
                name_to_id = dict(zip(self.df['昵称'], self.df['用户ID']))
                
                # 遍历评论，提取@关系
                for idx, row in self.df.iterrows():
                    comment = str(row['评论'])
                    # 查找所有@的用户名
                    at_users = at_pattern.findall(comment)
                    if at_users:
                        # 查找匹配的用户ID
                        for at_name in at_users:
                            # 查找最匹配的用户名
                            matched_names = [name for name in name_to_id.keys() 
                                            if at_name in name or name in at_name]
                            if matched_names:
                                # 使用最接近的匹配
                                best_match = max(matched_names, key=len)
                                self.df.at[idx, '回复给用户ID'] = name_to_id[best_match]
                                reply_relation_found = True
                                break
        else:
            reply_relation_found = self.df['回复给用户ID'].notna().any()
        
        # 如果仍然没有找到回复关系，则尝试基于评论时间和内容相似度建立关系
        if not reply_relation_found:
            print("未从评论中提取到@关系，尝试基于时间和内容相似度构建关系...")
            
            from difflib import SequenceMatcher
            
            # 计算两个字符串的相似度
            def similarity(a, b):
                return SequenceMatcher(None, a, b).ratio()
            
            # 按时间排序
            self.df['时间'] = pd.to_datetime(self.df['时间'])
            self.df = self.df.sort_values(by='时间')
            
            # 设置时间窗口 (5分钟)
            time_window = pd.Timedelta(minutes=5)
            
            # 对每条评论，查找之前5分钟内的相关评论
            for i, current in self.df.iterrows():
                current_time = current['时间']
                current_comment = str(current['评论'])
                
                # 跳过已经有回复关系的评论
                if pd.notna(current['回复给用户ID']):
                    continue
                
                # 查找时间窗口内的评论
                for j, previous in self.df.iterrows():
                    if i == j or previous['时间'] > current_time:
                        continue
                    
                    time_diff = current_time - previous['时间']
                    if time_diff <= time_window:
                        prev_comment = str(previous['评论'])
                        # 计算相似度
                        sim_score = similarity(current_comment, prev_comment)
                        # 如果相似度高，或者内容包含，则假设是回复关系
                        if sim_score > 0.4 or any(word in current_comment for word in prev_comment.split() if len(word) > 1):
                            self.df.at[i, '回复给用户ID'] = previous['用户ID']
                            reply_relation_found = True
                            break
        
        # 创建用户互动网络可视化
        from pyecharts.charts import Graph
        import networkx as nx
        
        if reply_relation_found:
            # 使用NetworkX构建网络图
            G = nx.DiGraph()
            
            # 添加评论用户节点
            for idx, row in self.df.iterrows():
                user_id = row['用户ID']
                user_name = row['昵称']
                G.add_node(user_id, name=user_name, symbolSize=10)
            
            # 添加回复关系边
            for idx, row in self.df.iterrows():
                if pd.notna(row['回复给用户ID']) and row['回复给用户ID'] in G:
                    G.add_edge(row['用户ID'], row['回复给用户ID'])
            
            # 识别中心用户（基于出入度）
            degree_centrality = nx.degree_centrality(G)
            
            # 调整节点大小
            max_centrality = max(degree_centrality.values()) if degree_centrality else 0.1
            for node in G.nodes():
                node_size = 10 + (degree_centrality.get(node, 0) / max_centrality) * 40
                G.nodes[node]['symbolSize'] = node_size
            
            # 转换为pyecharts可用的格式
            nodes = []
            for node, attrs in G.nodes(data=True):
                try:
                    user_name = attrs.get('name', str(node))
                    node_size = attrs.get('symbolSize', 10)
                    category = 0
                    
                    # 如果是中心用户，使用不同类别标记
                    if degree_centrality.get(node, 0) > 0.1:
                        category = 1
                    
                    nodes.append({
                        "name": user_name,
                        "symbolSize": node_size,
                        "category": category
                    })
                except:
                    continue
            
            # 边列表
            links = []
            for source, target in G.edges():
                try:
                    source_name = G.nodes[source].get('name', str(source))
                    target_name = G.nodes[target].get('name', str(target))
                    
                    links.append({
                        "source": source_name,
                        "target": target_name
                    })
                except:
                    continue
            
            # 创建互动网络图
            graph = (
                Graph(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="800px"))
                .add(
                    "",
                    nodes, 
                    links,
                    categories=[
                        {"name": "普通用户"},
                        {"name": "活跃用户/意见领袖"}
                    ],
                    repulsion=800,
                    edge_length=200,
                    layout="force",
                    is_draggable=True,
                    is_rotate_label=True
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="用户评论互动网络"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos_left="2%", pos_top="20%")
                )
            )
            
            # 保存图表
            graph.render(output_file)
            print(f"互动网络分析已保存至: {output_file}")
            return output_file
        else:
            print("未找到足够的互动关系数据，跳过互动网络分析")
            return None
    
    def analyze_content_tags(self, output_file=None):
        """
        内容标签分布分析 - 自动提取和分析评论中的关键话题和标签
        
        功能：
        1. 提取评论中的主要话题和标签
        2. 识别内容类别和兴趣点
        3. 生成多维度的内容分析图表
        
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "content_tags.html")
        
        print("正在进行内容标签分布分析...")
        
        # 1. 提取评论中的话题标签 (#标签)
        hashtag_pattern = re.compile(r'#([^#\s]+)')
        hashtags = []
        
        for comment in self.df['评论']:
            comment_str = str(comment)
            tags = hashtag_pattern.findall(comment_str)
            hashtags.extend(tags)
        
        # 统计标签频率
        hashtag_counter = Counter(hashtags)
        top_hashtags = hashtag_counter.most_common(20)
        
        # 2. 预定义的内容类别关键词
        content_categories = {
            '产品评价': ['质量', '做工', '好用', '实用', '推荐', '好看', '效果', '物超所值', '值得', '购买'],
            '价格讨论': ['价格', '贵', '便宜', '划算', '性价比', '优惠', '打折', '值得', '不值', '退款'],
            '功能咨询': ['怎么用', '使用', '功能', '操作', '如何', '教程', '说明书', '方法', '步骤'],
            '物流相关': ['发货', '快递', '物流', '送货', '收到', '包装', '到货', '破损', '完好'],
            '售后服务': ['售后', '退换', '保修', '客服', '维修', '退货', '换货', '联系', '解决'],
            '比较参考': ['对比', '差别', '区别', '比较', '选择', '推荐', '哪个好', '还是', '更好'],
            '创意灵感': ['创意', '灵感', '设计', '风格', '教程', '搭配', '点子', '技巧', '启发'],
            '情感表达': ['喜欢', '讨厌', '爱', '感动', '失望', '开心', '伤心', '期待', '惊喜', '难过'],
            '购买意向': ['想买', '想要', '准备', '下单', '入手', '购买', '剁手', '心动', '购物车'],
            '使用体验': ['体验', '感受', '使用感', '手感', '舒适度', '用着', '试用', '上手']
        }
        
        # 3. 分析评论内容与预定义类别的关联
        category_counts = {category: 0 for category in content_categories}
        
        for comment in self.df['评论']:
            comment_str = str(comment).lower()  # 转小写便于匹配
            words = jieba.lcut(comment_str)
            
            # 判断评论与哪些类别相关
            for category, keywords in content_categories.items():
                if any(keyword in comment_str for keyword in keywords):
                    category_counts[category] += 1
        
        # 4. 分析热门话题词汇
        content = ' '.join([str(i).replace('\n', '') for i in self.df['评论']])
        words = jieba.lcut(content)
        
        # 过滤掉停用词
        stopwords = {'了', '的', '我', '你', '是', '都', '把', '能', '就', '这', '还', 
                     '和', '啊', '在', '吧', '有', '也', '不', '呢', '吗', '啥', '怎么',
                     '一个', '什么', '一下', '一样', '一直', '为了', '可以', '那么'}
        filtered_words = [word for word in words if len(word) > 1 and word not in stopwords]
        
        # 词频统计
        word_counter = Counter(filtered_words)
        top_words = word_counter.most_common(30)
        
        # 创建词云图表
        from pyecharts.charts import WordCloud, Bar, Pie, Grid, Page
        
        # 5. 生成多维度分析图表
        page = Page(layout=Page.SimplePageLayout)
        
        # 5.1 内容类别分布
        category_items = [(k, v) for k, v in category_counts.items() if v > 0]
        if category_items:
            category_pie = (
                Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="700px", height="400px"))
                .add(
                    "",
                    category_items,
                    radius=["30%", "75%"],
                    center=["50%", "50%"],
                    rosetype="radius"
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="评论内容类别分布"),
                    legend_opts=opts.LegendOpts(orient="vertical", pos_left="2%", pos_top="15%")
                )
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
            )
            page.add(category_pie)
        
        # 5.2 热门话题词云
        if top_words:
            word_cloud = (
                WordCloud(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
                .add(
                    "", 
                    top_words,
                    word_size_range=[15, 80],
                    shape="circle"
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="热门话题词云")
                )
            )
            page.add(word_cloud)
        
        # 5.3 热门标签柱状图
        if top_hashtags:
            # 提取标签和计数
            tags, counts = zip(*top_hashtags) if top_hashtags else ([], [])
            tag_bar = (
                Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
                .add_xaxis(list(tags))
                .add_yaxis("出现次数", list(counts))
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="热门标签统计"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                    datazoom_opts=opts.DataZoomOpts()
                )
            )
            page.add(tag_bar)
            
        # 保存图表
        page.render(output_file)
        print(f"内容标签分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_user_influence(self, output_file=None):
        """
        用户活跃度与影响力分析 - 识别具有高影响力的用户和活跃用户
        
        分析维度:
        1. 用户评论频率 - 识别活跃用户
        2. 用户评论点赞量 - 识别高影响力用户
        3. 用户评论长度 - 识别高质量内容贡献者
        4. 用户活跃时段 - 分析用户活跃时间规律
        
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "user_influence.html")
        
        print("正在分析用户活跃度与影响力...")
        
        # 检查是否有必要的列
        required_columns = ['昵称', '点赞数', '评论']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        
        if missing_columns:
            print(f"缺少必要的列: {', '.join(missing_columns)}，影响力分析可能不完整")
        
        # 1. 用户评论频率分析
        user_comment_counts = self.df['昵称'].value_counts()
        top_active_users = user_comment_counts.head(20)
        
        # 2. 用户点赞总量分析
        if '点赞数' in self.df.columns:
            # 确保点赞数是数值类型
            try:
                self.df['点赞数'] = pd.to_numeric(self.df['点赞数'], errors='coerce').fillna(0)
            except:
                print("点赞数转换为数值类型时出错，使用默认值0")
                self.df['点赞数'] = 0
            
            # 按用户分组，计算总点赞数
            user_likes = self.df.groupby('昵称')['点赞数'].sum()
            top_liked_users = user_likes.sort_values(ascending=False).head(20)
        else:
            top_liked_users = None
        
        # 3. 用户评论长度分析
        self.df['评论长度'] = self.df['评论'].apply(lambda x: len(str(x)))
        avg_length_by_user = self.df.groupby('昵称')['评论长度'].mean()
        top_quality_users = avg_length_by_user.sort_values(ascending=False).head(20)
        
        # 4. 用户活跃时段分析
        if '时间' in self.df.columns:
            self.df['时间'] = pd.to_datetime(self.df['时间'])
            self.df['小时'] = self.df['时间'].dt.hour
            
            # 活跃时段分析
            hour_distribution = self.df['小时'].value_counts().sort_index()
        else:
            hour_distribution = None
        
        # 5. 影响力综合评分
        # 计算用户影响力得分 (评论数 * 0.4 + 总点赞数 * 0.4 + 平均评论长度 * 0.2)
        user_influence = pd.DataFrame()
        user_influence['评论数'] = user_comment_counts
        
        if '点赞数' in self.df.columns:
            user_influence['总点赞数'] = user_likes
        else:
            user_influence['总点赞数'] = 0
        
        user_influence['平均评论长度'] = avg_length_by_user
        
        # 标准化各项指标到0-1之间
        for col in ['评论数', '总点赞数', '平均评论长度']:
            max_val = user_influence[col].max()
            if max_val > 0:
                user_influence[f'{col}_标准化'] = user_influence[col] / max_val
            else:
                user_influence[f'{col}_标准化'] = 0
        
        # 计算综合影响力得分
        user_influence['影响力得分'] = (
            user_influence['评论数_标准化'] * 0.4 +
            user_influence['总点赞数_标准化'] * 0.4 +
            user_influence['平均评论长度_标准化'] * 0.2
        ) * 100  # 转为0-100分
        
        # 选出影响力前20名
        top_influential_users = user_influence.sort_values(by='影响力得分', ascending=False).head(20)
        
        # 6. 创建可视化图表
        from pyecharts.charts import Bar, Line, Grid, Page
        
        page = Page(layout=Page.SimplePageLayout)
        
        # 6.1 最活跃用户柱状图
        active_bar = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="500px"))
            .add_xaxis(top_active_users.index.tolist())
            .add_yaxis("评论数", top_active_users.values.tolist())
            .set_global_opts(
                title_opts=opts.TitleOpts(title="最活跃用户排行"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                datazoom_opts=opts.DataZoomOpts()
            )
        )
        page.add(active_bar)
        
        # 6.2 最具影响力用户柱状图
        influence_data = top_influential_users['影响力得分'].round(2)
        influence_bar = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="500px"))
            .add_xaxis(influence_data.index.tolist())
            .add_yaxis("影响力得分", influence_data.values.tolist())
            .set_global_opts(
                title_opts=opts.TitleOpts(title="最具影响力用户排行"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                datazoom_opts=opts.DataZoomOpts()
            )
        )
        page.add(influence_bar)
        
        # 6.3 用户点赞量排行
        if top_liked_users is not None:
            likes_bar = (
                Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="500px"))
                .add_xaxis(top_liked_users.index.tolist())
                .add_yaxis("总点赞数", top_liked_users.values.tolist())
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="用户点赞量排行"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                    datazoom_opts=opts.DataZoomOpts()
                )
            )
            page.add(likes_bar)
        
        # 6.4 用户活跃时段分析
        if hour_distribution is not None:
            active_time_line = (
                Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="400px"))
                .add_xaxis(hour_distribution.index.tolist())
                .add_yaxis("评论数", hour_distribution.values.tolist(), is_smooth=True)
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="用户活跃时段分布"),
                    xaxis_opts=opts.AxisOpts(name="小时", min_=0, max_=23),
                    yaxis_opts=opts.AxisOpts(name="评论数")
                )
            )
            page.add(active_time_line)
        
        # 保存图表
        page.render(output_file)
        print(f"用户活跃度与影响力分析已保存至: {output_file}")
        
        return output_file
    
    def analyze_hot_topics(self, output_file=None):
        """
        热点话题识别与趋势追踪 - 分析评论中的热点话题和时间趋势
        
        功能：
        1. 识别评论中的热点话题和关键词
        2. 追踪话题随时间的热度变化
        3. 分析热门话题的情感倾向
        4. 识别突发热点和持续话题
        
        :param output_file: 输出文件名
        :return: 输出文件路径
        """
        if self.df is None:
            self.load_data()
        
        if not output_file:
            output_file = os.path.join(self.output_dir, "hot_topics.html")
        
        print("正在识别和分析热点话题...")
        
        # 1. 时间序列预处理
        if '时间' in self.df.columns:
            # 确保时间列是日期时间类型
            self.df['时间'] = pd.to_datetime(self.df['时间'])
            
            # 添加日期和小时列
            self.df['日期'] = self.df['时间'].dt.date
            self.df['小时'] = self.df['时间'].dt.hour
            
            # 按日期排序
            self.df = self.df.sort_values('时间')
            
            # 检查评论跨越多少天
            dates = self.df['日期'].unique()
            date_count = len(dates)
            print(f"评论数据跨越 {date_count} 天")
            
            has_time_data = True
        else:
            has_time_data = False
            print("数据没有时间信息，将跳过时间趋势分析")
        
        # 2. 提取评论中的关键词和话题
        content = ' '.join([str(i).replace('\n', '') for i in self.df['评论']])
        
        # 使用jieba分词提取关键词
        jieba.setLogLevel(20)
        words = jieba.lcut(content)
        
        # 加载停用词
        stopwords = {'了', '的', '我', '你', '是', '都', '把', '能', '就', '这', '还', 
                     '和', '啊', '在', '吧', '有', '也', '不', '呢', '吗', '啥', '怎么',
                     '一个', '什么', '一下', '一样', '一直', '为了', '可以', '那么'}
        
        # 过滤停用词
        filtered_words = [word for word in words if len(word) > 1 and word not in stopwords]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        # 提取热门词汇 (Top 50)
        hot_words = word_counts.most_common(50)
        
        # 3. TF-IDF提取关键词 (每条评论作为一个文档)
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # 准备文档集合
        docs = self.df['评论'].astype(str).tolist()
        
        # 分词函数
        def tokenize_text(text):
            return [word for word in jieba.lcut(text) if len(word) > 1 and word not in stopwords]
        
        # 使用自定义分词器创建TF-IDF矢量器
        tfidf_vectorizer = TfidfVectorizer(
            max_features=100,  # 最多保留100个特征
            token_pattern=None,  # 禁用默认的token模式
            tokenizer=tokenize_text
        )
        
        try:
            # 计算TF-IDF矩阵
            tfidf_matrix = tfidf_vectorizer.fit_transform(docs)
            
            # 获取特征名称 (词语)
            feature_names = tfidf_vectorizer.get_feature_names_out()
            
            # 计算每个词语的TF-IDF均值 (作为重要性指标)
            tfidf_means = tfidf_matrix.mean(axis=0).A1
            
            # 创建词语和其重要性分数的映射
            tfidf_scores = {feature_names[i]: tfidf_means[i] for i in range(len(feature_names))}
            
            # 按重要性排序
            important_words = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:30]
            
            has_tfidf_results = True
        except Exception as e:
            print(f"TF-IDF分析出错: {str(e)}")
            important_words = []
            has_tfidf_results = False
        
        # 4. 提取评论中的主题 (通过规则和常见话题检测)
        topic_keywords = {
            '质量问题': ['质量', '差', '坏', '问题', '故障', '退货', '换货'],
            '价格相关': ['价格', '贵', '便宜', '值', '不值', '实惠', '优惠'],
            '服务体验': ['服务', '态度', '客服', '售后', '快递', '物流', '送货'],
            '使用体验': ['好用', '难用', '体验', '操作', '方便', '实用', '手感'],
            '外观设计': ['外观', '设计', '漂亮', '好看', '丑', '时尚', '颜值'],
            '功能特性': ['功能', '特性', '性能', '速度', '效果', '强大', '智能']
        }
        
        # 检测每条评论所属的主题
        for topic, keywords in topic_keywords.items():
            self.df[f'话题_{topic}'] = self.df['评论'].apply(
                lambda x: any(keyword in str(x) for keyword in keywords)
            )
        
        # 统计每个话题的评论数量
        topic_counts = {
            topic: self.df[f'话题_{topic}'].sum() 
            for topic in topic_keywords.keys()
        }
        
        # 5. 时间趋势分析 (如果有时间数据)
        time_trend_charts = []
        
        if has_time_data and date_count > 1:
            # 按日期统计话题分布
            daily_topic_counts = {}
            
            # 对每个话题，计算每天的出现次数
            for topic in topic_keywords.keys():
                topic_by_date = self.df.groupby('日期')[f'话题_{topic}'].sum()
                daily_topic_counts[topic] = topic_by_date
            
            # 创建话题时间趋势图
            from pyecharts.charts import Line
            
            all_dates = sorted(self.df['日期'].unique())
            
            # 创建时间趋势线图
            trend_line = (
                Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
                .add_xaxis([str(date) for date in all_dates])
            )
            
            # 为每个话题添加一条线
            for topic, counts in daily_topic_counts.items():
                trend_data = []
                for date in all_dates:
                    trend_data.append(counts.get(date, 0))
                
                trend_line.add_yaxis(
                    topic, 
                    trend_data,
                    is_smooth=True,
                    is_symbol_show=True,
                    symbol_size=8,
                    linestyle_opts=opts.LineStyleOpts(width=2)
                )
            
            trend_line.set_global_opts(
                title_opts=opts.TitleOpts(title="热点话题时间趋势"),
                xaxis_opts=opts.AxisOpts(name="日期"),
                yaxis_opts=opts.AxisOpts(name="话题出现次数"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="right", pos_top="middle"),
                tooltip_opts=opts.TooltipOpts(trigger="axis")
            )
            
            time_trend_charts.append(trend_line)
        
        # 6. 可视化结果
        from pyecharts.charts import Bar, Pie, WordCloud, Page
        
        page = Page(layout=Page.SimplePageLayout)
        
        # 6.1 热点话题分布饼图
        topic_pie = (
            Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="700px", height="500px"))
            .add(
                "",
                [list(z) for z in zip(topic_counts.keys(), topic_counts.values())],
                radius=["30%", "75%"],
                center=["50%", "50%"],
                rosetype="radius"
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="热点话题分布"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="2%", pos_top="15%")
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"))
        )
        page.add(topic_pie)
        
        # 6.2 热门词汇可视化
        wordcloud_chart = (
            WordCloud(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
            .add(
                "", 
                hot_words,
                word_size_range=[15, 80],
                shape="circle"
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="热门词汇")
            )
        )
        page.add(wordcloud_chart)
        
        # 6.3 TF-IDF重要词汇柱状图
        if has_tfidf_results:
            important_words_data = important_words[:15]  # 显示前15个
            words_list, scores_list = zip(*important_words_data)
            
            tfidf_bar = (
                Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="900px", height="500px"))
                .add_xaxis(list(words_list))
                .add_yaxis("重要性得分", [round(score * 100, 2) for score in scores_list])
                .set_global_opts(
                    title_opts=opts.TitleOpts(title="TF-IDF关键词重要性"),
                    xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
                    yaxis_opts=opts.AxisOpts(name="重要性得分")
                )
            )
            page.add(tfidf_bar)
        
        # 6.4 时间趋势图 (如果有)
        for chart in time_trend_charts:
            page.add(chart)
        
        # 保存图表
        page.render(output_file)
        print(f"热点话题分析已保存至: {output_file}")
        
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
        
        # 情感分析
        outputs.append(self.analyze_sentiment())
        
        # 用户群体画像分析
        outputs.append(self.analyze_user_portraits())
        
        # 互动网络分析
        outputs.append(self.analyze_interaction_network())
        
        # 内容标签分析
        outputs.append(self.analyze_content_tags())
        
        # 用户活跃度与影响力分析
        outputs.append(self.analyze_user_influence())
        
        # 热点话题分析
        outputs.append(self.analyze_hot_topics())
        
        print(f"所有分析已完成，结果保存在 {self.output_dir} 目录")
        return outputs


def main():
    """主函数"""
    print("=" * 60)
    print("抖音评论数据分析工具")
    print("=" * 60)
    
    # 询问用户选择操作类型
    print("\n请选择操作:")
    print("1. 分析最新爬取的评论数据")
    print("2. 指定CSV文件进行分析")
    choice = input("请输入选项 (1/2): ")
    
    csv_file = None
    if choice == "2":
        csv_file = input("请输入CSV文件路径: ")
        if not os.path.exists(csv_file):
            print(f"错误: 文件 {csv_file} 不存在!")
            return
    
    # 设置词云形状图片
    shape_img = input("请输入词云形状图片路径 (留空使用默认形状): ")
    if shape_img and not os.path.exists(shape_img):
        print(f"警告: 图片 {shape_img} 不存在，将使用默认形状")
        shape_img = None
    
    # 创建分析器
    analyzer = CommentAnalyzer(csv_file=csv_file)
    
    # 执行所有分析
    try:
        outputs = analyzer.run_all_analysis(shape_img=shape_img)
        print("\n分析完成! 生成的文件:")
        for output in outputs:
            print(f" - {output}")
    except Exception as e:
        print(f"分析过程中出错: {str(e)}")


if __name__ == "__main__":
    main() 