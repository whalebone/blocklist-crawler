from apscheduler.schedulers.background import BlockingScheduler
import os
from crawler.crawler import BlockListCrawler

if __name__ == '__main__':
    crawler = BlockListCrawler()
    if "TEST" in os.environ:
        crawler.get_all()
    while True:
        try:
            scheduler = BlockingScheduler(timezone="utc")
            scheduler.add_job(crawler.get_all, "interval", minutes=int(os.environ.get("CHECK_PERIOD")),
                              replace_existing=True, misfire_grace_time=60)
            scheduler.start()
        except Exception as re:
            print("Error in runtime {}".format(re))
        finally:
            try:
                scheduler.remove_all_jobs()
                scheduler.shutdown(wait=False)
            except Exception as e:
                print("Failed to cleanup scheduler")
