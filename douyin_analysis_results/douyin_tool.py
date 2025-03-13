"""
抖音评论爬取与分析工具 - 统一入口

功能:
1. 爬取抖音视频评论
2. 分析评论数据并生成可视化图表1
3. 支持爬取全部评论，不受限于页数
4. 按日期时间保存数据，便于历史追踪

日期: 2025年3月12日
版本: 3.0
作者: TO：梁
"""

import os
import sys
import time

# 导入爬虫和分析器
try:
    from douyin_crawler import DouyinCommentCrawler
    from douyin_analyzer import CommentAnalyzer
except ImportError:
    print("正在导入模块...")
    # 尝试相对导入
    try:
        # 当前文件目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        from douyin_crawler import DouyinCommentCrawler
        from douyin_analyzer import CommentAnalyzer
    except ImportError:
        print("无法导入必要模块。请确保 douyin_crawler.py 和 douyin_analyzer.py 文件位于同一目录下。")
        sys.exit(1)


def show_banner():
    """显示欢迎横幅"""
    print("\n" + "=" * 80)
    print("抖音评论爬取与分析工具 V3.0".center(78))
    print("=" * 80)
    print("  功能：爬取抖音视频评论数据并生成多维度分析图表")
    print("  特点：支持爬取全部评论 | 自动保存历史数据 | 多维度数据可视化")
    print("  作者：TO：梁")
    print("=" * 80 + "\n")


def print_section(title):
    """打印带有分隔符的小节标题"""
    print("\n" + "-" * 50)
    print(f" {title} ".center(48, "-"))
    print("-" * 50)


def show_menu():
    """显示主菜单"""
    print_section("主菜单")
    print("1. 爬取新的评论并分析")
    print("2. 分析已有的评论数据")
    print("3. 同时执行爬取和分析")
    print("0. 退出程序")
    return input("\n请选择操作 [0-3]: ")


def crawl_comments():
    """爬取评论功能"""
    print_section("评论爬取")
    
    # 获取视频URL
    video_url = input("请输入抖音视频URL (例如: https://www.douyin.com/video/7353500880198536457): ")
    if not video_url:
        print("错误: URL不能为空!")
        return None
    
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
    print("\n正在初始化爬虫...")
    crawler = DouyinCommentCrawler(
        video_url=video_url, 
        max_pages=max_pages,
        use_normal_mode=use_normal_mode,
        login_first=login_first
    )
    
    # 执行爬取
    print("\n开始爬取评论，请稍候...\n")
    start_time = time.time()
    comments = crawler.start_crawler()
    end_time = time.time()
    
    # 打印爬取结果
    if comments:
        print(f"\n成功爬取 {len(comments)} 条评论，耗时 {end_time - start_time:.2f} 秒")
        print(f"评论已保存到文件: {crawler.get_output_file()}")
        return crawler.get_output_file()
    else:
        print("\n爬取失败或未获取到评论")
        return None


def analyze_comments(csv_file=None):
    """分析评论功能"""
    print_section("评论分析")
    
    if not csv_file:
        print("\n请选择操作:")
        print("1. 分析最新爬取的评论数据")
        print("2. 指定CSV文件进行分析")
        choice = input("请输入选项 (1/2): ")
        
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
    print("\n正在初始化分析器...")
    analyzer = CommentAnalyzer(csv_file=csv_file)
    
    # 执行所有分析
    print("\n开始分析评论数据，请稍候...\n")
    start_time = time.time()
    try:
        outputs = analyzer.run_all_analysis(shape_img=shape_img)
        end_time = time.time()
        
        print(f"\n分析完成! 耗时 {end_time - start_time:.2f} 秒")
        print("生成的文件:")
        for output in outputs:
            print(f" - {output}")
    except Exception as e:
        print(f"分析过程中出错: {str(e)}")


def main():
    """主函数"""
    show_banner()
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            # 爬取新评论
            csv_file = crawl_comments()
            
            # 询问是否要分析
            if csv_file:
                if input("\n是否要分析刚爬取的评论数据? (y/n): ").lower() == 'y':
                    analyze_comments(csv_file)
        
        elif choice == "2":
            # 分析已有评论
            analyze_comments()
        
        elif choice == "3":
            # 爬取并分析
            csv_file = crawl_comments()
            if csv_file:
                print("\n自动开始分析评论数据...")
                analyze_comments(csv_file)
        
        elif choice == "0":
            print("\n感谢使用，再见!")
            break
        
        else:
            print("\n无效的选择，请重新输入")
        
        input("\n按Enter键继续...")


if __name__ == "__main__":
    main()