"""
港股新闻爬虫启动脚本
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.hkstocks import HKStocksScraper
from src.services import get_news_service
from src.core.models import NewsSource


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='港股新闻爬虫 - 自动提取关键词',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用默认参数（最近1天，3个工作线程）
    python run_hkstocks_crawler.py

    # 爬取最近3天的新闻，使用5个工作线程
    python run_hkstocks_crawler.py --days 3 --workers 5

    # 限制爬取数量为50条
    python run_hkstocks_crawler.py --max-count 50

    # 不提取关键词（仅保存原文）
    python run_hkstocks_crawler.py --no-keywords
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='爬取最近几天的新闻（默认: 1）'
    )

    parser.add_argument(
        '--max-count',
        type=int,
        default=1000,
        help='最多爬取数量（默认: 1000）'
    )

    parser.add_argument(
        '--no-keywords',
        action='store_true',
        help='不提取关键词'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='消费者线程数量（默认: 3）'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("港股新闻爬虫 - AAStocks")
    print("=" * 60)
    print(f"爬取范围: 最近 {args.days} 天")
    print(f"最大数量: {args.max_count} 条")
    print(f"提取关键词: {'否' if args.no_keywords else '是'}")
    print(f"工作模式: 生产者-消费者 (线程数: {args.workers})")
    print("=" * 60)

    try:
        # 创建服务
        news_service = get_news_service(
            source=NewsSource.HKSTOCKS,
            auto_extract_keywords=not args.no_keywords,
            auto_generate_summary=False
        )

        # 创建爬虫
        scraper = HKStocksScraper(news_service=news_service)

        # 运行爬虫
        print("\n使用生产者-消费者模式...")
        stats = scraper.fetch_and_save_with_pipeline(
            days=args.days,
            max_count=args.max_count,
            num_workers=args.workers,
            extract_keywords=not args.no_keywords
        )

        # 输出结果
        print("\n运行完成:")
        print(f"  抓取: {stats['fetched']}")
        print(f"  保存: {stats['saved']}")
        print(f"  重复: {stats['duplicated']}")
        print(f"  失败: {stats['failed']}")

        # 数据库统计
        total_stats = news_service.get_statistics()
        print("\n" + "=" * 60)
        print("数据库统计")
        print("=" * 60)
        print(f"总新闻数: {total_stats['total_count']}")
        print(f"已提取关键词: {total_stats['with_keywords']}")
        print(f"关键词覆盖率: {total_stats['keyword_rate']:.2%}")
        print("=" * 60)

    except ImportError as e:
        print(f"\n错误: 模块导入失败: {e}")
        print("\n请确保已安装所有依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
