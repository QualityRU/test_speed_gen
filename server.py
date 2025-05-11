import asyncio
import base64
import json
import re
import time
import uuid
from collections import defaultdict
from io import BytesIO
from statistics import mean
from traceback import format_exc
from typing import AsyncGenerator

import logger
import openai
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import BaseModel
from terminaltables import AsciiTable

from config import API_KEY, PROMT

times_dict = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

session_storage = defaultdict(dict)
event_queues = defaultdict(asyncio.Queue)

client = openai.AsyncClient(api_key=API_KEY)


class SSEMessage(BaseModel):
    data: dict
    event: str = None
    id: str = None
    message: str = None


def get_image_info(image_data):
    image_bytesio = BytesIO(image_data)
    with Image.open(image_bytesio) as img:
        extension = img.format.lower()
    file_size_bytes = len(image_data)
    file_size_kb = file_size_bytes / 1024
    return extension, round(file_size_kb, 2)


def ascii_table():
    table_data = [['Filename', 'Count', 'Min', 'Max', 'Avg', 'Size']]

    for filename, values in times_dict.items():
        count = len(values)
        min_val = round(min(values), 2)
        max_val = round(max(values), 2)
        avg_val = round(mean(values), 2)
        size = f"{filename.split('_')[1]} КБ"
        table_data.append(
            [filename.upper(), count, min_val, max_val, avg_val, size]
        )

    table_data.sort(key=lambda x: x[0])
    table = AsciiTable(table_data)
    print(table.table)


async def timer(func, image_data):
    async def execute():
        return await func()

    start = time.time()
    extension, size = get_image_info(image_data)
    try:
        res = await execute()
    except openai.RateLimitError as e:
        print('Превышен лимит запросов, повтор.', e)
        await asyncio.sleep(30)
        res = await execute()
    except Exception:
        print('Ошибка, повтор.', format_exc())
        await asyncio.sleep(30)
        res = await execute()

    if 'error' in res:
        print('Превышен лимит запросов, повтор.', res)
        await asyncio.sleep(30)
        res = await execute()
    else:
        elapsed = time.time() - start
        key = f'{extension}_{size}'
        if not times_dict.get(key):
            times_dict[key] = []
        times_dict[key].append(elapsed)
        # print(f'Картинка {extension} {size} КБ обработана : {elapsed:.2f} сек')
        ascii_table()
    return res


async def send_image_to_gpt(image_data: BytesIO, prompt: str) -> str:
    try:
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        while True:
            stream = await client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': f'{prompt}'},
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
            if any(
                word in response
                for word in [
                    'Калории',
                    'Белки',
                    'Жиры',
                    'Углеводы',
                    'Хлебные единицы',
                    'ХЕ',
                    'Протеин',
                ]
            ):
                return response
            return 'None'
    except Exception as e:
        return f'Error from GPT: {str(e)}'


async def sub_request(message, lang='en'):

    content = [
        {
            'role': 'system',
            'content': 'You are a helpful assistant. Please format the response in the following JSON template.',
        },
        {'role': 'user', 'content': message},
        {
            'role': 'user',
            'content': """
                Please extract the relevant data from the text and format it in this JSON structure:
                
                {
                    "dish_name": <value>,
                    "calories": <value>,
                    "proteins": <value>.0,
                    "proteins_percent": <value>,
                    "fats": <value>,
                    "fats_percent": <value>,
                    "carbohydrates": <value>,
                    "carbohydrates_percent": <value>,
                    "bread_units": <value>,
                    "total_weight": <value>,
                    "glycemic_index": <value>,
                    "protein_bje": <value>,
                    "fats_bje": <value>,
                    "calories_bje": <value>,
                    "bje_units": <value>
                }
                Language for key content dish_name: 
            """
            + f' {lang}',
        },
    ]

    response_json = None
    for _ in range(5):
        stream = await client.chat.completions.create(
            model='gpt-4o-mini', messages=content
        )

        response = ''
        for choice in stream.choices:
            response += choice.message.content
        try:
            json_pattern = re.compile(r'\{(?:[^{}]|(?R))*\}')
        except:
            json_pattern = re.compile(r'```json\s*({.*?})\s*```', re.DOTALL)

        # Find JSON-like text
        match = json_pattern.search(response)
        if match:
            try:
                json_text = match.group(1)
            except:
                json_text = match.group(0)
            try:
                # Attempt to parse the JSON
                response_json = json.loads(json_text)
                break
            except json.JSONDecodeError:
                # Handle error if the extracted text is not valid JSON
                try:
                    response_json = json.loads(response)
                    break
                except:
                    logger.info(
                        'Extracted text is not valid JSON: ' + json_text
                    )
        else:
            try:
                response_json = json.loads(response)
                break
            except:
                # Handle case where no JSON was found
                logger.info('No JSON found in the response: ' + response)
    if response_json:
        response_json = {
            key: str(val) if val is not None else val
            for key, val in response_json.items()
        }
        # await db_con.add_user_diarys(user_id, user_date, response_json, path_to_photo=path_to_photo)
        try:
            float(response_json['bje_units'])
        except:
            response_json['bje_units'] = '0'
        return response_json


@app.get('/create-session/', tags=['Session Management'])
async def create_session():
    session_id = str(uuid.uuid4())
    session_storage[session_id] = {'status': 'created'}
    return {'session_id': session_id}


@app.get('/stream-events/', include_in_schema=False)
async def stream_events(session_id: str):
    if session_id not in session_storage:
        raise HTTPException(status_code=404, detail='Session not found')

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = event_queues[session_id]

        while True:
            message = await queue.get()

            yield f'id: {message.id}\n' if message.id else ''
            yield f'data: {json.dumps(message.data)}\n\n'

            if message.event == 'processing_complete':
                break

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    )


async def process_image_background_task(image_data: bytes, session_id: str):
    try:
        session_storage[session_id].update(
            {
                'status': 'processing',
                'image_size': len(image_data),
            }
        )

        for i in range(1, 6):
            await asyncio.sleep(1)

            message = SSEMessage(
                data={
                    'progress': i * 20,
                    'status': 'processing',
                    'step': f'step_{i}',
                },
                event='progress_update',
                id=str(uuid.uuid4()),
                message=f'Processing step {i}/5 completed',
            )
            await event_queues[session_id].put(message)

        # chatgpt_result = await timer(send_image_to_gpt(image_data, PROMT), image_data)
        tasks = [
            timer(lambda: send_image_to_gpt(image_data, PROMT), image_data)
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)
        chatgpt_result = next(
            (
                res
                for res in results
                if res
                and isinstance(res, str)
                and 'Error' not in res
                and res != 'None'
            ),
            None,
        )
        if not chatgpt_result:
            raise Exception("GPT didn't return a valid result.")
        chatgpt_json = await sub_request(chatgpt_result)

        final_message = SSEMessage(
            data={
                'progress': 100,
                'status': 'complete',
                'result': 'image_processed_successfully',
                'gpt_analysis': chatgpt_json,
            },
            event='processing_complete',
            id=str(uuid.uuid4()),
        )
        await event_queues[session_id].put(final_message)

    except Exception as e:
        print(e)
        # error_message = SSEMessage(
        #     data={'error': str(e), 'status': 'error'},
        #     event='processing_error',
        #     id=str(uuid.uuid4()),
        # )
        # await event_queues[session_id].put(error_message)


@app.post('/upload-image/', tags=['Image Processing'])
async def upload_image(image: UploadFile, session_id: str):
    if session_id not in session_storage:
        raise HTTPException(status_code=404, detail='Session not found')

    try:
        image_data = await image.read()

        if not image_data:
            raise HTTPException(status_code=400, detail='Empty file provided')

        asyncio.create_task(
            process_image_background_task(image_data, session_id)
        )

        return {'status': 'processing_started', 'session_id': session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
