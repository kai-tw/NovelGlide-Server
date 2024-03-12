import asyncio
from crawler import Crawler

crawler = Crawler(['https://www.wenku8.net/novel/2/2763/index.htm'])
asyncio.run(crawler.crawl())

print(crawler.get_statistics())
