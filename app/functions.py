"""
Вспомогательные функции
"""
from fastapi import Request, HTTPException
import httpx
import uuid

from consts import (
    HEADERS_FOR_NOMINATIM,
    CITY_PARAMS,
    URL_FOR_NOMINATIM,
)


def get_default_template_data():
    """Возвращает данные по умолчанию для шаблона"""
    return {
        'display_name': '',
        'weather_data': [],
        'city_name': '',
        'forecast_days': ''
    }


async def get_coordinates(city_name: str) -> tuple[float, float, str] | None:
    """
    По названию города находит координаты этого города
    :param city_name: Название города
    :return: Координаты города
    """
    CITY_PARAMS['q'] = city_name
    async with httpx.AsyncClient() as client:
        response = await client.get(URL_FOR_NOMINATIM, params=CITY_PARAMS, headers=HEADERS_FOR_NOMINATIM)

    if response.status_code == 200:
        data = response.json()
        if data:
            first_element = data[0]
            return first_element['lat'], first_element['lon'], first_element['display_name']

        else:
            raise ValueError(f'Город "{city_name}" не найден.')

    else:
        raise HTTPException(status_code=response.status_code, detail='Ошибка запроса')


def get_user_id(request: Request) -> uuid:
    """
    Получаем или создаем идентификатор пользователя

    :param request: Результат запроса
    :return: id пользователя
    """
    if not request.cookies.get('user_id'):
        user_id = str(uuid.uuid4())
    else:
        user_id = request.cookies.get('user_id')
    return user_id
