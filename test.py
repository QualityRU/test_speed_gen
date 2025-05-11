import asyncio
import base64
import os
import time
from io import BytesIO
from statistics import mean

import aiofiles
from openai import AsyncClient, RateLimitError
from terminaltables import AsciiTable


class GPT:
    def __init__(self, token: str, promt: str):
        self.promt = promt
        self.token = token
        self.client = AsyncClient(api_key=self.token)

    async def request(self, image: BytesIO):
        image_base64 = base64.b64encode(image.getvalue()).decode('utf-8')
        while True:
            stream = await self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': f'{self.promt}'},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{image_base64}'
                                },
                            },
                        ],
                    }
                ],
            )
            response = ''
            for choice in stream.choices:
                response += choice.message.content
            return response

    async def timer(self, byte_stream, file_path):
        start = time.time()
        try:
            res = await self.request(byte_stream)
        except RateLimitError:
            print('Превышен лимит запросов, повтор.')
            await asyncio.sleep(30)
            res = await self.timer(byte_stream, file_path)
        except Exception:
            await asyncio.sleep(30)
            res = await self.timer(byte_stream, file_path)

        if res:
            elapsed = time.time() - start
            if not times_dict.get(file_path):
                times_dict[file_path] = []
            times_dict[file_path].append(elapsed)
            print(f'Картинка {file_path} обработана : {elapsed:.2f} сек')


async def process_file(gpt, file_path):
    async with aiofiles.open(file_path, mode='rb') as f:
        content = await f.read()
        byte_stream = BytesIO(content)
        for i in range(RUNS):
            await gpt.timer(byte_stream, file_path)


async def main():
    async with aiofiles.open('token.txt', 'r', encoding='utf-8') as f:
        token = await f.read()
    async with aiofiles.open('promt.txt', 'r', encoding='utf-8') as f:
        promt = await f.read()

    gpt = GPT(token, promt)

    tasks = []
    for filename in os.listdir('img'):
        file_path = os.path.join('img', filename)
        tasks.append(process_file(gpt, file_path))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    RUNS = 10
    times_dict = {}
    table_data = [['Filename', 'Count', 'Min', 'Max', 'Avg', 'Size']]

    asyncio.run(main())

    for filename, values in times_dict.items():
        name = filename.replace('img/', '').upper()
        size_kb = f'{round(os.path.getsize(filename) / 1024, 2)} КБ'
        count = len(values)
        min_val = round(min(values), 2)
        max_val = round(max(values), 2)
        avg_val = round(mean(values), 2)
        table_data.append([name, count, min_val, max_val, avg_val, size_kb])

    table_data.sort(key=lambda x: x[0])
    table = AsciiTable(table_data)
    print(table.table)
