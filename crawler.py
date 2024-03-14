import aiohttp

from bs4 import BeautifulSoup


class Crawler:

    def __init__(self, arg_url):
        self.__arg_url = arg_url

    async def main(self):
        async with aiohttp.ClientSession() as client:
            rawText = await self.fetch(client)
            document = BeautifulSoup(rawText, "lxml")
            for a in document.find_all('a'):
                print(a, "\n")

    async def fetch(self, client):
        async with client.get(self.__arg_url) as response:
            print('<', response.status, '>')
            assert response.status == 200
            return await response.text()
