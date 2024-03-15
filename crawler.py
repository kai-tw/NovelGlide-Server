import aiohttp

from bs4 import BeautifulSoup
from charset_normalizer import detect
from queue import Queue
from urllib.parse import urlparse
from urllib.parse import urljoin


class Crawler:

    def __init__(self, arg_url):
        self.__arg_url = arg_url
        self.__queue = Queue()

    async def main(self):
        # Put the request url into the queue.
        self.__queue.put(self.__arg_url)

        async with aiohttp.ClientSession(
                fallback_charset_resolver=lambda r, b: detect(b)[
                    'encoding'] or 'utf-8') as client:
            while not self.__queue.empty():
                await self.fetch(client)

    async def fetch(self, client):
        headers = {
            'Accept':
            'text/html',
            'Accept-Language':
            'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7',
            'Dnt':
            '1',
            'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 ' +
            'Safari/537.36'
        }
        url = self.__queue.get(False)
        content = ''
        async with client.get(url, headers=headers) as response:
            print(response.status, url)
            content = await response.text()

        self.parse(url, content)

        self.__queue.task_done()

    def parse(self, url, raw_text):
        document = BeautifulSoup(raw_text, 'lxml')
        for a in document.find_all('a', href=True):
            link = a['href'] if self.__is_absolute_path(
                a['href']) else urljoin(url, a['href'])
            text = a.text
            print(link, text)

    def __is_absolute_path(self, link) -> bool:
        return bool(urlparse(link).netloc)
