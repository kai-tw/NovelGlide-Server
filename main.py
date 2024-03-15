import asyncio
from crawler import Crawler

crawler = Crawler('https://www.wenku8.net/novel/2/2763/index.htm')
# crawler = Crawler('http://httpbin.org/get')
asyncio.run(crawler.main())
