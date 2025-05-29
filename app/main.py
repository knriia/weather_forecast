"""
Главный модуль
"""

import asyncio
from typing import Any
from datetime import datetime

from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas
import openmeteo_requests
from collections import defaultdict

from consts import (
    URL_FOR_API_OPEN_METEO,
    DAILY_PARAMS,
    DATE_ISO_FORMAT,
    WEATHER_INTERPRETATION_CODES,
)
from functions import get_default_template_data, get_coordinates, get_user_id


app = FastAPI()
templates = Jinja2Templates(directory='templates')
app.mount('/static', StaticFiles(directory='static'), name='static')

search_history = defaultdict(list)
city_stats = defaultdict(int)


@app.post('/', response_class=HTMLResponse)
async def get_weather(request: Request, city_name: str = Form(...), forecast_days: int = Form(...)):
    """
    Возвращает таблицу с прогнозом погоды на указанное количество дней
    :param request: Результат запроса
    :param city_name: Название населенного пункта
    :param forecast_days: Количество дней для прогноза
    :return: Таблица с прогнозом погоды на указанное количествой дней
    """

    user_id = get_user_id(request)

    search_entry = {
        'city': city_name,
        'days': forecast_days,
        'timestamp': datetime.now().isoformat()
    }
    search_history[user_id].append(search_entry)
    city_stats[city_name.lower()] += 1

    latitude, longitude, display_name = await get_coordinates(city_name=city_name)
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'forecast_days': forecast_days,
        'daily': DAILY_PARAMS,
    }
    om = openmeteo_requests.AsyncClient()
    responses = await om.weather_api(URL_FOR_API_OPEN_METEO, params=params)
    daily = responses[0].Daily()
    dates = pandas.date_range(
        start=pandas.to_datetime(daily.Time(), unit='s'),
        end=pandas.to_datetime(daily.TimeEnd(), unit='s'),
        freq=pandas.Timedelta(daily.Interval(), unit='s'),
        inclusive='left'
    ).tolist()

    daily_data = {'date': [date.date().strftime(DATE_ISO_FORMAT) for date in dates]}

    for count in range(0, daily.VariablesLength()):
        daily_data[DAILY_PARAMS[count]] = daily.Variables(count).ValuesAsNumpy().tolist()

    daily_data['weather_code'] = [
        WEATHER_INTERPRETATION_CODES[int(weather_code)] for weather_code in daily_data['weather_code']
    ]

    weather_data = pandas.DataFrame(data=daily_data).to_dict(orient='records')
    return templates.TemplateResponse(
        'weather.html', {
            'request': request,
            'weather_data': weather_data,
            'display_name': display_name,
            'city_name': city_name,
            'forecast_days': forecast_days,
            'history': search_history.get(user_id, [])
        }
    )


@app.get('/api/stats')
async def get_stats() -> dict[str, Any]:
    """
    API для получения статистики по городам

    :return: Словарь со статистикой посика
    """
    return {
        'total_searches': sum(city_stats.values()),
        'cities': dict(city_stats),
        'most_popular': max(city_stats.items(), key=lambda x: x[1], default=None)
    }

@app.get('/api/user/history')
async def get_user_history(request: Request) -> dict[str, Any]:
    """
    API для получения истории пользователя

    :param request: Рещультат запроса
    :return: Словарь с данными о пользователе
    """

    user_id = get_user_id(request)
    return {
        'user_id': user_id,
        'history': search_history.get(user_id, [])
    }


@app.get('/', response_class=HTMLResponse)
async def main(request: Request) -> HTMLResponse:
    """
    Главная функция

    :param: Результат запроса
    :return: Результат ответа
    """
    user_id = get_user_id(request)
    response = templates.TemplateResponse(
        'weather.html',
        {
            'request': request,
            'history': search_history.get(user_id, [])
        } | get_default_template_data()
    )
    response.set_cookie(key='user_id', value=user_id)
    return response


if __name__ == '__main__':
    asyncio.run(main())
