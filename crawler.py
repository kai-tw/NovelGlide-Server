import asyncio
import aiohttp
import cgi
import re
from collections import namedtuple

import urllib.parse


class Crawler:

    def __init__(self, arg_roots):
        self.__arg_roots = arg_roots
        self.__domains = []
        self.__max_redirect = 10
        self.__max_tries = 4
        self.__seen_urls = set()
        self.__max_workers = 10
        self.__exclude = '.css'
        self.__fetch_statistics = []

    async def crawl(self):
        self.q = asyncio.Queue()
        self.session = aiohttp

        for root in self.__arg_roots:
            url_parts = urllib.parse.urlparse(root)
            hostname = url_parts.hostname

            if not hostname:
                continue

            # Check the hostname is an IP or domain name.
            if re.match(r'\A[\d\.]*\Z', hostname):
                # It's an IP.
                self.__domains.add(hostname)
            else:
                # It's a domain name, so convert it to lowercase.
                hostname = hostname.lower()

            self.add_url(root)

        workers = [
            asyncio.create_task(self.work()) for _ in range(self.__max_workers)
        ]

        await self.q.join()
        for w in workers:
            w.cancel()
        print('Task complete.')
        await self.session.close()

    def add_url(self, url, max_redirect=None):
        if max_redirect is None:
            max_redirect = self.__max_redirect

        if url not in self.__seen_urls and max_redirect >= 0:
            self.__seen_urls.add(url)
            self.q.put_nowait((url, max_redirect))
            print('Add url: ', url)

    async def work(self):
        try:
            while not self.q.empty():
                url, max_redirect = await self.q.get()
                print('Start fetching: ', url)
                await self.fetch(url, max_redirect)
                print('Return from fetching: ', url)
                self.q.task_done()
                print('Complete fetching: ', url)
        except asyncio.CancelledError:
            pass

    async def fetch(self, url, max_redirect):
        tried_count = 0
        exception = None

        while tried_count < self.__max_tries:
            print('Tried: ', tried_count, ' - ', url)
            try:
                response = await self.session.get(url, allow_redirect=False)
                break
            except Exception as e:
                exception = e
            tried_count += 1
        else:
            print('Reach the tried limit.')
            self.__fetch_statistics(
                CrawlerFetchStatistic(url=url,
                                      next_url=None,
                                      status=None,
                                      exception=exception,
                                      size=0,
                                      content_type=None,
                                      encoding=None,
                                      num_urls=0,
                                      num_new_urls=0))
            return
        try:
            print('Response: ', response.status)
            if self.is_redirect(response):
                location = response.headers['locations']
                next_url = urllib.parse.urljoin(url, location)
                self.__fetch_statistics(
                    CrawlerFetchStatistic(url=url,
                                          next_url=next_url,
                                          status=response.status,
                                          size=0,
                                          content_type=None,
                                          encoding=None,
                                          num_urls=0,
                                          num_new_urls=0))
                self.add_url(url, max_redirect - 1)
            else:
                statistics, links = await self.parse_links(response)
                self.__fetch_statistics(statistics)
                for link in links.difference(self.__seen_urls):
                    self.add_url(link, self.__max_redirect)
                self.__seen_urls.update(links)
        finally:
            await response.release()

    def is_redirect(response):
        return response.status in (300, 301, 302, 303, 307)

    async def parse_links(self, response):
        links = set()
        content_type = None
        encoding = None
        body = await response.read()

        if response.status == 200:
            content_type = response.header.get('content_type')
            pdict = {}

            if content_type:
                content_type, pdict = cgi.parse_header(content_type)

            encoding = pdict.get('encoding', 'utf-8')

            if content_type in ('text/html'):
                text = await response.text()
                urls = set(re.findall(r'''(?i)href=["']([^\s"'<>]+)''', text))

                for url in urls:
                    url_join = urllib.parse.urljoin(str(response.url), url)
                    defragmented, frag = urllib.parse.urldefrag(url_join)

                    if (self.url_allowed(defragmented)):
                        links.add(defragmented)
                        print('Add: ' + defragmented + '\n')
        statistics = CrawlerFetchStatistic(url=response.url,
                                           next_url=None,
                                           status=response.status,
                                           exception=None,
                                           size=len(body),
                                           content_type=content_type,
                                           encoding=encoding,
                                           num_urls=len(links),
                                           num_new_urls=len(links -
                                                            self.__seen_urls))
        return statistics, links

    def url_allowed(self, url):
        if re.search(self.__exclude, url):
            return False
        parts = urllib.parse.urlparse(url)
        if (parts.scheme not in ('http', 'https')):
            return False
        return True

    def get_statistics(self):
        return self.__fetch_statistics


CrawlerFetchStatistic = namedtuple('FetchStatistic', [
    'url', 'next_url', 'status', 'exception', 'size', 'content_type',
    'encoding', 'num_urls', 'num_new_urls'
])
