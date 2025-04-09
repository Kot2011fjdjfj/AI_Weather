import os
import json
import openmeteo_requests
from gigachat import GigaChat
import requests_cache
from retry_requests import retry
from geopy.geocoders import Nominatim
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import requests

# конфиги и апи ключ
CACHE_DIR = os.path.expanduser('~/.cache')
CACHE_PATH = os.path.join(CACHE_DIR, 'weather_cache')
SETTINGS_PATH = os.path.join(CACHE_DIR, 'settings.json')
GIGA_CREDENTIALS = " ключ GIGA"

# Создаем папку для  погоды и нейросети
os.makedirs(CACHE_DIR, exist_ok=True)

# Для запросов к OpenMeteo
cache_session = requests_cache.CachedSession(CACHE_PATH, expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Установка системной темы по умолчанию
ctk.set_appearance_mode("system")  # По умолчанию системная тема
ctk.set_default_color_theme("blue")  #  тема

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1300x700")
        self.root.title("AI Weather")
        self.current_city = ""
        self.forecast_days = 7  # По умолчанию прогноз на 7 дней
        self.theme = "system"  # По умолчанию системная тема
        self.hourly_data = None  # Для хранения  данных
        self.load_settings()  # Загружаем настройки
        self.setup_ui()

    def load_settings(self):
        """Загружает настройки из файла, если он существует."""
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r") as f:
                settings = json.load(f)
                self.forecast_days = settings.get("forecast_days", 7)
                self.theme = settings.get("theme", "system")
                ctk.set_appearance_mode(self.theme)

    def save_settings(self):
        """Сохраняет текущие настройки в файл."""
        settings = {
            "forecast_days": self.forecast_days,
            "theme": self.theme
        }
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f)

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Боковая панель для вкладок
        self.sidebar = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nswe")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Кнопка для перехода на вкладку "Город"
        self.button_city = ctk.CTkButton(
            self.sidebar,
            text="Город",
            command=lambda: self.show_tab("Город"),
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )
        self.button_city.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Для группировки вкладок, связанных с погодой
        self.weather_tabs_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.weather_tabs_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Кнопка для раскрытия/сворачивания вкладок погоды
        self.button_weather_group = ctk.CTkButton(
            self.weather_tabs_frame,
            text="Погода ▼",
            command=self.toggle_weather_tabs,
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )
        self.button_weather_group.pack(fill="x", pady=(0, 5))

        # Кнопки для переключения между вкладками погоды 
        self.button_weather = ctk.CTkButton(
            self.weather_tabs_frame,
            text="Текущая погода",
            command=lambda: self.show_tab("Погода"),
            font=("Arial", 14, "bold"),
            state="disabled",
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )
        self.button_forecast = ctk.CTkButton(
            self.weather_tabs_frame,
            text=f"Прогноз на {self.forecast_days} дней",
            command=lambda: self.show_tab("Прогноз на 7 дней"),
            font=("Arial", 14, "bold"),
            state="disabled",
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )
        self.button_hourly = ctk.CTkButton(
            self.weather_tabs_frame,
            text="Почасовой прогноз",
            command=lambda: self.show_tab("Почасовые Погодные Переменные"),
            font=("Arial", 14, "bold"),
            state="disabled",
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )

        # Кнопка для перехода на вкладку "Настройки"
        self.button_settings = ctk.CTkButton(
            self.sidebar,
            text="Настройки",
            command=lambda: self.show_tab("Настройки"),
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=180,
            height=40
        )
        self.button_settings.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Вкладка "Город"
        self.frame_city = ctk.CTkFrame(self.root)
        self.frame_city.grid(row=1, column=1, sticky="nsew")
        self.frame_city.grid_rowconfigure(0, weight=1)
        self.frame_city.grid_columnconfigure(0, weight=1)

        self.scrollable_frame_city = ctk.CTkScrollableFrame(self.frame_city)
        self.scrollable_frame_city.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.scrollable_frame_city.grid_rowconfigure(0, weight=1)
        self.scrollable_frame_city.grid_columnconfigure(0, weight=1)

        self.label_title_city = ctk.CTkLabel(self.scrollable_frame_city, text="Введите город", font=("Arial", 24, "bold"))
        self.label_title_city.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Поле для ввода города
        self.city_name_entry = ctk.CTkEntry(self.scrollable_frame_city, placeholder_text="Введите название города", font=("Arial", 16))
        self.city_name_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Кнопка "Установить город" (изначально неактивна)
        self.button_set_city = ctk.CTkButton(
            self.scrollable_frame_city,
            text="Установить город",
            command=self.set_city,
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            corner_radius=10,
            width=200,
            height=40,
            state="disabled"  # Кнопка изначально неактивна
        )
        self.button_set_city.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Сообщение о необходимости ввода города
        self.label_city_message = ctk.CTkLabel(
            self.scrollable_frame_city,
            text="Пожалуйста, введите город, чтобы получить доступ к другим вкладкам.",
            font=("Arial", 14),
            text_color="gray"
        )
        self.label_city_message.grid(row=3, column=0, padx=10, pady=10, sticky="w")

        # Привязка события к полю ввода города
        self.city_name_entry.bind("<KeyRelease>", self.check_city_input)

        # Вкладка "Погода"
        self.frame_weather = ctk.CTkFrame(self.root)
        self.frame_weather.grid(row=1, column=1, sticky="nsew")
        self.frame_weather.grid_rowconfigure(0, weight=1)
        self.frame_weather.grid_columnconfigure(0, weight=1)

        self.scrollable_frame_weather = ctk.CTkScrollableFrame(self.frame_weather)
        self.scrollable_frame_weather.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.scrollable_frame_weather.grid_rowconfigure(0, weight=1)
        self.scrollable_frame_weather.grid_columnconfigure(0, weight=1)

        self.label_title_weather = ctk.CTkLabel(self.scrollable_frame_weather, text="Текущая погода", font=("Arial", 24, "bold"))
        self.label_title_weather.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Фрейм для отображения текущей погоды
        self.frame_current_weather = ctk.CTkFrame(self.scrollable_frame_weather, corner_radius=10)
        self.frame_current_weather.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.label_temperature = ctk.CTkLabel(self.frame_current_weather, text="🌡️ Текущая температура: --°C", font=("Arial", 16, "bold"))
        self.label_temperature.pack(padx=10, pady=5, anchor="w")

        self.label_feels_like = ctk.CTkLabel(self.frame_current_weather, text="🌡️ Температура по ощущениям: --°C", font=("Arial", 16, "bold"))
        self.label_feels_like.pack(padx=10, pady=5, anchor="w")

        self.label_humidity = ctk.CTkLabel(self.frame_current_weather, text="💧 Относительная влажность: --%", font=("Arial", 16, "bold"))
        self.label_humidity.pack(padx=10, pady=5, anchor="w")

        self.label_precipitation = ctk.CTkLabel(self.frame_current_weather, text="🌧️ Текущие осадки: -- мм", font=("Arial", 16, "bold"))
        self.label_precipitation.pack(padx=10, pady=5, anchor="w")

        self.label_wind = ctk.CTkLabel(self.frame_current_weather, text="💨 Скорость ветра: -- м/с", font=("Arial", 16, "bold"))
        self.label_wind.pack(padx=10, pady=5, anchor="w")

        self.label_wind_direction = ctk.CTkLabel(self.frame_current_weather, text="🧭 Направление ветра: --", font=("Arial", 16, "bold"))
        self.label_wind_direction.pack(padx=10, pady=5, anchor="w")

        self.label_cloudcover = ctk.CTkLabel(self.frame_current_weather, text="☁️ Общий уровень облачности: --%", font=("Arial", 16, "bold"))
        self.label_cloudcover.pack(padx=10, pady=5, anchor="w")

        self.label_weathercode = ctk.CTkLabel(self.frame_current_weather, text="🌤️ Погодный код: --", font=("Arial", 16, "bold"))
        self.label_weathercode.pack(padx=10, pady=5, anchor="w")

        # Оценка комфорта погоды
        self.label_comfort = ctk.CTkLabel(self.frame_current_weather, text="🌟 Оценка комфорта: --/10", font=("Arial", 16, "bold"))
        self.label_comfort.pack(padx=10, pady=5, anchor="w")

        # Фрейм для рекомендации от AI
        self.frame_recommendation = ctk.CTkFrame(self.scrollable_frame_weather, corner_radius=10)
        self.frame_recommendation.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.label_recommendation = ctk.CTkLabel(self.frame_recommendation, text="Рекомендация от Нейросети: --", font=("Arial", 16, "bold"), wraplength=700)
        self.label_recommendation.pack(padx=10, pady=10, anchor="w")

        # Вкладка "Прогноз на 7 дней"
        self.frame_forecast_tab = ctk.CTkFrame(self.root)
        self.frame_forecast_tab.grid(row=1, column=1, sticky="nsew")
        self.frame_forecast_tab.grid_rowconfigure(1, weight=1)
        self.frame_forecast_tab.grid_columnconfigure(0, weight=1)

        self.label_title_7_days = ctk.CTkLabel(self.frame_forecast_tab, text=f"Прогноз на {self.forecast_days} дней", font=("Arial", 24, "bold"))
        self.label_title_7_days.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.frame_forecast_and_chart = ctk.CTkFrame(self.frame_forecast_tab)
        self.frame_forecast_and_chart.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.frame_forecast_and_chart.grid_rowconfigure(0, weight=1)
        self.frame_forecast_and_chart.grid_columnconfigure(0, weight=1)
        self.frame_forecast_and_chart.grid_columnconfigure(1, weight=1)

        self.frame_forecast = ctk.CTkScrollableFrame(self.frame_forecast_and_chart, height=200)
        self.frame_forecast.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        self.frame_chart = ctk.CTkScrollableFrame(self.frame_forecast_and_chart)
        self.frame_chart.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        # Вкладка "Почасовой прогноз"
        self.frame_hourly_tab = ctk.CTkFrame(self.root)
        self.frame_hourly_tab.grid(row=1, column=1, sticky="nsew")
        self.frame_hourly_tab.grid_rowconfigure(1, weight=1)
        self.frame_hourly_tab.grid_columnconfigure(0, weight=1)

        self.label_title_hourly = ctk.CTkLabel(self.frame_hourly_tab, text="Почасовой Прогноз", font=("Arial", 24, "bold"))
        self.label_title_hourly.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.frame_hourly_and_chart = ctk.CTkFrame(self.frame_hourly_tab)
        self.frame_hourly_and_chart.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.frame_hourly_and_chart.grid_rowconfigure(0, weight=1)
        self.frame_hourly_and_chart.grid_columnconfigure(0, weight=1)
        self.frame_hourly_and_chart.grid_columnconfigure(1, weight=1)

        self.frame_hourly = ctk.CTkScrollableFrame(self.frame_hourly_and_chart, height=200)
        self.frame_hourly.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        self.frame_hourly_chart = ctk.CTkScrollableFrame(self.frame_hourly_and_chart)
        self.frame_hourly_chart.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

        # Вкладка "Настройки"
        self.frame_settings = ctk.CTkFrame(self.root)
        self.frame_settings.grid(row=1, column=1, sticky="nsew")
        self.frame_settings.grid_rowconfigure(0, weight=1)
        self.frame_settings.grid_columnconfigure(0, weight=1)

        self.scrollable_frame_settings = ctk.CTkScrollableFrame(self.frame_settings)
        self.scrollable_frame_settings.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.scrollable_frame_settings.grid_rowconfigure(0, weight=1)
        self.scrollable_frame_settings.grid_columnconfigure(0, weight=1)

        self.label_title_settings = ctk.CTkLabel(self.scrollable_frame_settings, text="Настройки", font=("Arial", 24, "bold"))
        self.label_title_settings.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.label_theme = ctk.CTkLabel(self.scrollable_frame_settings, text="Тема:", font=("Arial", 16, "bold"))
        self.label_theme.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.theme_var = ctk.StringVar(value=self.theme)  # По умолчанию системная тема
        self.optionmenu_theme = ctk.CTkOptionMenu(
            self.scrollable_frame_settings,
            values=["system", "light", "dark"],
            command=self.change_theme,
            variable=self.theme_var,
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            button_color="#4CAF50",
            button_hover_color="#45a049",
            text_color="white"
        )
        self.optionmenu_theme.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Добавляем выбор длительности прогноза
        self.label_forecast_days = ctk.CTkLabel(self.scrollable_frame_settings, text="Длительность прогноза:", font=("Arial", 16, "bold"))
        self.label_forecast_days.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.forecast_days_var = ctk.StringVar(value=str(self.forecast_days))  # По умолчанию 7 дней
        self.optionmenu_forecast_days = ctk.CTkOptionMenu(
            self.scrollable_frame_settings,
            values=["7", "10", "16"],
            command=self.change_forecast_days,
            variable=self.forecast_days_var,
            font=("Arial", 16, "bold"),
            fg_color="#4CAF50",
            button_color="#4CAF50",
            button_hover_color="#45a049",
            text_color="white"
        )
        self.optionmenu_forecast_days.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        # Сообщения об ошибках
        self.label_no_city = ctk.CTkLabel(self.frame_forecast_tab, text="Пожалуйста, введите город для отображения данных.", font=("Arial", 14), text_color="gray")
        self.label_no_city_hourly = ctk.CTkLabel(self.frame_hourly_tab, text="Пожалуйста, введите город для отображения данных.", font=("Arial", 14), text_color="gray")

        # Показываем вкладку "Город" по умолчанию
        self.show_tab("Город")

    def toggle_weather_tabs(self):
        """Раскрывает или сворачивает вкладки, связанные с погодой."""
        if self.button_weather.winfo_ismapped():
            self.button_weather.pack_forget()
            self.button_forecast.pack_forget()
            self.button_hourly.pack_forget()
            self.button_weather_group.configure(text="Погода ▶")
        else:
            self.button_weather.pack(fill="x", pady=(0, 5))
            self.button_forecast.pack(fill="x", pady=(0, 5))
            self.button_hourly.pack(fill="x", pady=(0, 5))
            self.button_weather_group.configure(text="Погода ▼")

    def change_theme(self, choice):
        """Изменяет тему приложения."""
        self.theme = choice
        ctk.set_appearance_mode(choice)
        self.save_settings()  # Сохраняем настройки

    def change_forecast_days(self, choice):
        """Изменяет длительность прогноза."""
        self.forecast_days = int(choice)
        self.button_forecast.configure(text=f"Прогноз на {self.forecast_days} дней")
        self.label_title_7_days.configure(text=f"Прогноз на {self.forecast_days} дней в городе {self.current_city}")
        self.save_settings()  # Сохраняем настройки
        self.update_7_day_weather()

    def check_city_input(self, event=None):
        """Проверяет, есть ли текст в поле ввода города, и активирует/деактивирует кнопку."""
        if self.city_name_entry.get().strip():
            self.button_set_city.configure(state="normal")  # Активируем кнопку
        else:
            self.button_set_city.configure(state="disabled")  # Деактивируем кнопку

    def set_city(self):
        """Устанавливает город и активирует кнопки."""
        city_name = self.city_name_entry.get()
        if city_name:
            self.current_city = city_name
            self.update_weather_data()
            self.button_weather.configure(state="normal")
            self.button_forecast.configure(state="normal")
            self.button_hourly.configure(state="normal")
            self.label_city_message.grid_remove()
            self.show_tab("Погода")
            # Обновляем заголовки вкладок с городом
            self.label_title_weather.configure(text=f"Текущая погода в городе {self.current_city}")
            self.label_title_7_days.configure(text=f"Прогноз на {self.forecast_days} дней в городе {self.current_city}")
            self.label_title_hourly.configure(text=f"Почасовой прогноз в городе {self.current_city}")

    def update_weather_data(self):
        """Обновляет данные о погоде и прогнозе."""
        if self.current_city:
            self.get_weather_and_chat()
            self.update_7_day_weather()
            self.update_hourly_weather()

    def get_coordinates_from_city(self, city_name):
        """Получает координаты города по его названию."""
        geolocator = Nominatim(user_agent="weather_app")
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            raise ValueError(f"Не удалось найти город {city_name}")

    def get_wind_direction(self, degrees):
        """Преобразует градусы в направление ветра."""
        directions = [
            "Север", "Северо-северо-восток", "Северо-восток", "Востоко-северо-восток",
            "Восток", "Востоко-юго-восток", "Юго-восток", "Юго-юго-восток",
            "Юг", "Юго-юго-запад", "Юго-запад", "Западо-юго-запад",
            "Запад", "Западо-северо-запад", "Северо-запад", "Северо-северо-запад"
        ]
        index = round(degrees / 22.5) % 16
        return directions[index]

    def get_weather_and_chat(self):
        """Получает данные о погоде и рекомендации от Нейросети."""
        try:
            latitude, longitude = self.get_coordinates_from_city(self.current_city)
            print(f"Город: {self.current_city}, Широта: {latitude}, Долгота: {longitude}")

            # Запрашиваем данные о погоде
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "windspeed_10m", "winddirection_10m", "cloudcover", "weathercode"],
                "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "cloudcover", "windspeed_10m", "visibility", "weathercode", "soil_temperature_0cm", "soil_temperature_6cm", "soil_temperature_18cm", "soil_temperature_54cm"],
                "daily": ["weathercode", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "precipitation_sum", "precipitation_probability_max", "windspeed_10m_max", "winddirection_10m_dominant", "sunrise", "sunset", "uv_index_max"],
                "forecast_days": self.forecast_days
            }
            responses = openmeteo.weather_api(url, params=params)

            response = responses[0]
            current = response.Current()
            current_temperature_2m = current.Variables(0).Value()
            current_relative_humidity_2m = current.Variables(1).Value()
            current_apparent_temperature = current.Variables(2).Value()
            current_precipitation = current.Variables(3).Value()
            current_windspeed = current.Variables(4).Value()
            current_winddirection = current.Variables(5).Value()
            current_cloudcover = current.Variables(6).Value()
            current_weathercode = current.Variables(7).Value()

            # Преобразуем направление ветра в текстовый формат
            wind_direction = self.get_wind_direction(current_winddirection)

            # Обновляем интерфейс
            self.label_temperature.configure(text=f"🌡️ Текущая температура: {int(current_temperature_2m)}°C")
            self.label_feels_like.configure(text=f"🌡️ Температура по ощущениям: {int(current_apparent_temperature)}°C")
            self.label_humidity.configure(text=f"💧 Относительная влажность: {int(current_relative_humidity_2m)}%")
            self.label_precipitation.configure(text=f"🌧️ Текущие осадки: {int(current_precipitation)} мм")
            self.label_wind.configure(text=f"💨 Скорость ветра: {int(current_windspeed)} м/с")
            self.label_wind_direction.configure(text=f"🧭 Направление ветра: {wind_direction}")
            self.label_cloudcover.configure(text=f"☁️ Общий уровень облачности: {int(current_cloudcover)}%")
            self.label_weathercode.configure(text=f"🌤️ Погодный код: {self.get_weathercode_description(current_weathercode)}")

            # Используем GigaChat для получения оценки комфорта погоды
            with GigaChat(credentials=GIGA_CREDENTIALS, verify_ssl_certs=False) as giga:
                weather_info = f"Текущие осадки: {int(current_precipitation)} мм, Текущая температура: {int(current_temperature_2m)}°C, Температура по ощущениям: {int(current_apparent_temperature)}°C, Текущая относительная влажность воздуха: {int(current_relative_humidity_2m)}%, Скорость ветра: {int(current_windspeed)} м/с, Направление ветра: {wind_direction}, Общий уровень облачности: {int(current_cloudcover)}%"
                response = giga.chat(f"Оцени комфорт погоды от 1 до 10, где 1 - ужасно, 10 - отлично. Ответ должен содержать только число. Погода: {weather_info}")
                comfort_score = response.choices[0].message.content
                self.label_comfort.configure(text=f"🌟 Оценка комфорта от Нейросети: {comfort_score}/10")

                # Получаем рекомендацию от AI
                response = giga.chat(f"Как одеться по погоде: {weather_info}")
                giga_response = response.choices[0].message.content
                print(giga_response)
                self.label_recommendation.configure(text=f"Рекомендация от Нейросети: {giga_response}")

        except ValueError as e:
            print(e)

    def get_7_day_weather_data(self, city_name):
        """Получает данные о погоде на 7 дней."""
        try:
            latitude, longitude = self.get_coordinates_from_city(city_name)
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max,winddirection_10m_dominant,sunrise,sunset,uv_index_max&timezone=auto&forecast_days={self.forecast_days}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка при запросе: {response.status_code}")
                return None
        except ValueError as e:
            print(e)
            return None

    def get_hourly_weather_data(self, city_name):
        """Получает почасовые данные о погоде."""
        try:
            latitude, longitude = self.get_coordinates_from_city(city_name)
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relative_humidity_2m,precipitation,cloudcover,windspeed_10m,visibility,weathercode,soil_temperature_0cm,soil_temperature_6cm,soil_temperature_18cm,soil_temperature_54cm&timezone=auto&forecast_days=7"
            response = requests.get(url)
            if response.status_code == 200:
                self.hourly_data = response.json()  # Сохраняем данные для дальнейшего использования
                return self.hourly_data
            else:
                print(f"Ошибка при запросе: {response.status_code}")
                return None
        except ValueError as e:
            print(e)
            return None

    def show_weather_forecast(self, data, frame):
        """Отображает текстовый прогноз погоды."""
        for widget in frame.winfo_children():
            widget.destroy()

        daily = data.get('daily', {})
        times = daily.get('time', [])
        temp_max = daily.get('temperature_2m_max', [])
        temp_min = daily.get('temperature_2m_min', [])
        apparent_temp_max = daily.get('apparent_temperature_max', [])
        apparent_temp_min = daily.get('apparent_temperature_min', [])
        precipitation = daily.get('precipitation_sum', [])
        precipitation_probability = daily.get('precipitation_probability_max', [])
        windspeed = daily.get('windspeed_10m_max', [])
        winddirection = daily.get('winddirection_10m_dominant', [])
        sunrise = daily.get('sunrise', [])
        sunset = daily.get('sunset', [])
        uv_index = daily.get('uv_index_max', [])
        weathercode = daily.get('weathercode', [])

        for i in range(len(times)):
            day_frame = ctk.CTkFrame(frame, corner_radius=10)
            day_frame.pack(fill="x", padx=5, pady=5)

            label_day = ctk.CTkLabel(day_frame, text=times[i], font=("Arial", 16, "bold"))
            label_day.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            label_temp = ctk.CTkLabel(day_frame, text=f"🌡️ Макс.: {temp_max[i]}°C, Мин.: {temp_min[i]}°C", font=("Arial", 14))
            label_temp.grid(row=1, column=0, padx=10, pady=2, sticky="w")

            label_apparent_temp = ctk.CTkLabel(day_frame, text=f"🌡️ Макс. по ощущениям: {apparent_temp_max[i]}°C, Мин. по ощущениям: {apparent_temp_min[i]}°C", font=("Arial", 14))
            label_apparent_temp.grid(row=2, column=0, padx=10, pady=2, sticky="w")

            label_precip = ctk.CTkLabel(day_frame, text=f"🌧️ Осадки: {precipitation[i]} мм", font=("Arial", 14))
            label_precip.grid(row=3, column=0, padx=10, pady=2, sticky="w")

            label_precip_prob = ctk.CTkLabel(day_frame, text=f"🌧️ Вероятность осадков: {precipitation_probability[i]}%", font=("Arial", 14))
            label_precip_prob.grid(row=4, column=0, padx=10, pady=2, sticky="w")

            label_wind = ctk.CTkLabel(day_frame, text=f"💨 Ветер: {windspeed[i]} м/с", font=("Arial", 14))
            label_wind.grid(row=5, column=0, padx=10, pady=2, sticky="w")

            label_wind_direction = ctk.CTkLabel(day_frame, text=f"🧭 Преобладающее направление ветра: {self.get_wind_direction(winddirection[i])}", font=("Arial", 14))
            label_wind_direction.grid(row=6, column=0, padx=10, pady=2, sticky="w")

            label_sunrise = ctk.CTkLabel(day_frame, text=f"🌅 Восход: {sunrise[i]}", font=("Arial", 14))
            label_sunrise.grid(row=7, column=0, padx=10, pady=2, sticky="w")

            label_sunset = ctk.CTkLabel(day_frame, text=f"🌇 Закат: {sunset[i]}", font=("Arial", 14))
            label_sunset.grid(row=8, column=0, padx=10, pady=2, sticky="w")

            label_daylight = ctk.CTkLabel(day_frame, text=f"🌞 Продолжительность светового дня: {self.calculate_daylight_duration(sunrise[i], sunset[i])}", font=("Arial", 14))
            label_daylight.grid(row=9, column=0, padx=10, pady=2, sticky="w")

            label_uv_index = ctk.CTkLabel(day_frame, text=f"☀️ УФ индекс: {uv_index[i]}", font=("Arial", 14))
            label_uv_index.grid(row=10, column=0, padx=10, pady=2, sticky="w")

            label_weathercode = ctk.CTkLabel(day_frame, text=f"🌤️ Погодный код: {self.get_weathercode_description(weathercode[i])}", font=("Arial", 14))
            label_weathercode.grid(row=11, column=0, padx=10, pady=2, sticky="w")

    def calculate_daylight_duration(self, sunrise, sunset):
        """Вычисляет продолжительность светового дня."""
        from datetime import datetime
        sunrise_time = datetime.strptime(sunrise, "%Y-%m-%dT%H:%M")
        sunset_time = datetime.strptime(sunset, "%Y-%m-%dT%H:%M")
        daylight_duration = sunset_time - sunrise_time
        return str(daylight_duration)

    def get_weathercode_description(self, code):
        """Возвращает описание погодного кода на русском."""
        weathercode_descriptions = {
            0: "Ясно",
            1: "Преимущественно ясно",
            2: "Переменная облачность",
            3: "Пасмурно",
            45: "Туман",
            48: "Туман с инеем",
            51: "Морось: легкая",
            53: "Морось: умеренная",
            55: "Морось: сильная",
            56: "Ледяная морось: легкая",
            57: "Ледяная морось: сильная",
            61: "Дождь: легкий",
            63: "Дождь: умеренный",
            65: "Дождь: сильный",
            66: "Ледяной дождь: легкий",
            67: "Ледяной дождь: сильный",
            71: "Снег: легкий",
            73: "Снег: умеренный",
            75: "Снег: сильный",
            77: "Снежные зерна",
            80: "Ливень: легкий",
            81: "Ливень: умеренный",
            82: "Ливень: сильный",
            85: "Снегопад: легкий",
            86: "Снегопад: сильный",
            95: "Гроза: легкая или умеренная",
            96: "Гроза с градом: легкая",
            99: "Гроза с градом: сильная"
        }
        return weathercode_descriptions.get(code, "Неизвестно")

    def plot_weather(self, data, frame):
        """Строит диаграмму прогноза погоды."""
        for widget in frame.winfo_children():
            widget.destroy()

        daily = data.get('daily', {})
        times = daily.get('time', [])
        temp_max = daily.get('temperature_2m_max', [])
        temp_min = daily.get('temperature_2m_min', [])
        apparent_temp_max = daily.get('apparent_temperature_max', [])
        apparent_temp_min = daily.get('apparent_temperature_min', [])
        precipitation = daily.get('precipitation_sum', [])
        precipitation_probability = daily.get('precipitation_probability_max', [])
        windspeed = daily.get('windspeed_10m_max', [])
        uv_index = daily.get('uv_index_max', [])

        # График температуры
        fig_temp, ax_temp = plt.subplots(figsize=(8, 4))
        ax_temp.plot(times, temp_max, label='Макс. температура (°C)', color='red')
        ax_temp.plot(times, temp_min, label='Мин. температура (°C)', color='blue')
        ax_temp.set_title('Температура')
        ax_temp.set_xticks(times)
        ax_temp.set_xticklabels(times, rotation=45)
        ax_temp.legend()
        plt.tight_layout()

        canvas_temp = FigureCanvasTkAgg(fig_temp, master=frame)
        canvas_temp.draw()
        canvas_temp.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График температуры по ощущениям
        fig_apparent_temp, ax_apparent_temp = plt.subplots(figsize=(8, 4))
        ax_apparent_temp.plot(times, apparent_temp_max, label='Макс. температура по ощущениям (°C)', color='orange')
        ax_apparent_temp.plot(times, apparent_temp_min, label='Мин. температура по ощущениям (°C)', color='purple')
        ax_apparent_temp.set_title('Температура по ощущениям')
        ax_apparent_temp.set_xticks(times)
        ax_apparent_temp.set_xticklabels(times, rotation=45)
        ax_apparent_temp.legend()
        plt.tight_layout()

        canvas_apparent_temp = FigureCanvasTkAgg(fig_apparent_temp, master=frame)
        canvas_apparent_temp.draw()
        canvas_apparent_temp.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График осадков
        fig_precip, ax_precip = plt.subplots(figsize=(8, 4))
        ax_precip.bar(times, precipitation, label='Осадки (мм)', color='green')
        ax_precip.set_title('Осадки')
        ax_precip.set_xticks(times)
        ax_precip.set_xticklabels(times, rotation=45)
        ax_precip.legend()
        plt.tight_layout()

        canvas_precip = FigureCanvasTkAgg(fig_precip, master=frame)
        canvas_precip.draw()
        canvas_precip.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График вероятности осадков
        fig_precip_prob, ax_precip_prob = plt.subplots(figsize=(8, 4))
        ax_precip_prob.bar(times, precipitation_probability, label='Вероятность осадков (%)', color='blue')
        ax_precip_prob.set_title('Вероятность осадков')
        ax_precip_prob.set_xticks(times)
        ax_precip_prob.set_xticklabels(times, rotation=45)
        ax_precip_prob.legend()
        plt.tight_layout()

        canvas_precip_prob = FigureCanvasTkAgg(fig_precip_prob, master=frame)
        canvas_precip_prob.draw()
        canvas_precip_prob.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График скорости ветра
        fig_wind, ax_wind = plt.subplots(figsize=(8, 4))
        ax_wind.plot(times, windspeed, label='Скорость ветра (м/с)', color='orange')
        ax_wind.set_title('Скорость ветра')
        ax_wind.set_xticks(times)
        ax_wind.set_xticklabels(times, rotation=45)
        ax_wind.legend()
        plt.tight_layout()

        canvas_wind = FigureCanvasTkAgg(fig_wind, master=frame)
        canvas_wind.draw()
        canvas_wind.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График УФ индекса
        fig_uv_index, ax_uv_index = plt.subplots(figsize=(8, 4))
        ax_uv_index.plot(times, uv_index, label='УФ индекс', color='purple')
        ax_uv_index.set_title('УФ индекс')
        ax_uv_index.set_xticks(times)
        ax_uv_index.set_xticklabels(times, rotation=45)
        ax_uv_index.legend()
        plt.tight_layout()

        canvas_uv_index = FigureCanvasTkAgg(fig_uv_index, master=frame)
        canvas_uv_index.draw()
        canvas_uv_index.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

    def show_hourly_weather_forecast(self, data, frame):
        """Отображает текстовый почасовой прогноз погоды."""
        for widget in frame.winfo_children():
            widget.destroy()

        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        temperature = hourly.get('temperature_2m', [])
        humidity = hourly.get('relative_humidity_2m', [])
        precipitation = hourly.get('precipitation', [])
        windspeed = hourly.get('windspeed_10m', [])
        visibility = hourly.get('visibility', [])
        weathercode = hourly.get('weathercode', [])
        soil_temperature_0cm = hourly.get('soil_temperature_0cm', [])
        soil_temperature_6cm = hourly.get('soil_temperature_6cm', [])
        soil_temperature_18cm = hourly.get('soil_temperature_18cm', [])
        soil_temperature_54cm = hourly.get('soil_temperature_54cm', [])

        # Отображаем данные через каждые 2 часа
        for i in range(0, len(times), 2):
            hour_frame = ctk.CTkFrame(frame, corner_radius=10)
            hour_frame.pack(fill="x", padx=5, pady=5)

            label_time = ctk.CTkLabel(hour_frame, text=times[i], font=("Arial", 16, "bold"))
            label_time.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            label_temp = ctk.CTkLabel(hour_frame, text=f"🌡️ Температура: {temperature[i]}°C", font=("Arial", 14))
            label_temp.grid(row=1, column=0, padx=10, pady=2, sticky="w")

            label_humidity = ctk.CTkLabel(hour_frame, text=f"💧 Влажность: {humidity[i]}%", font=("Arial", 14))
            label_humidity.grid(row=2, column=0, padx=10, pady=2, sticky="w")

            label_precip = ctk.CTkLabel(hour_frame, text=f"🌧️ Осадки: {precipitation[i]} мм", font=("Arial", 14))
            label_precip.grid(row=3, column=0, padx=10, pady=2, sticky="w")

            label_wind = ctk.CTkLabel(hour_frame, text=f"💨 Ветер: {windspeed[i]} м/с", font=("Arial", 14))
            label_wind.grid(row=4, column=0, padx=10, pady=2, sticky="w")

            label_visibility = ctk.CTkLabel(hour_frame, text=f"👁️ Видимость: {visibility[i]} м", font=("Arial", 14))
            label_visibility.grid(row=5, column=0, padx=10, pady=2, sticky="w")

            label_weathercode = ctk.CTkLabel(hour_frame, text=f"🌤️ Погодный код: {self.get_weathercode_description(weathercode[i])}", font=("Arial", 14))
            label_weathercode.grid(row=6, column=0, padx=10, pady=2, sticky="w")

            label_soil_temp_0cm = ctk.CTkLabel(hour_frame, text=f"🌱 Температура почвы (0 см): {soil_temperature_0cm[i]}°C", font=("Arial", 14))
            label_soil_temp_0cm.grid(row=7, column=0, padx=10, pady=2, sticky="w")

            label_soil_temp_6cm = ctk.CTkLabel(hour_frame, text=f"🌱 Температура почвы (6 см): {soil_temperature_6cm[i]}°C", font=("Arial", 14))
            label_soil_temp_6cm.grid(row=8, column=0, padx=10, pady=2, sticky="w")

            label_soil_temp_18cm = ctk.CTkLabel(hour_frame, text=f"🌱 Температура почвы (18 см): {soil_temperature_18cm[i]}°C", font=("Arial", 14))
            label_soil_temp_18cm.grid(row=9, column=0, padx=10, pady=2, sticky="w")

            label_soil_temp_54cm = ctk.CTkLabel(hour_frame, text=f"🌱 Температура почвы (54 см): {soil_temperature_54cm[i]}°C", font=("Arial", 14))
            label_soil_temp_54cm.grid(row=10, column=0, padx=10, pady=2, sticky="w")

    def plot_hourly_weather(self, data, frame):
        """Строит диаграмму почасового прогноза."""
        for widget in frame.winfo_children():
            widget.destroy()

        hourly = data.get('hourly', {})
        times = hourly.get('time', [])
        temperature = hourly.get('temperature_2m', [])
        humidity = hourly.get('relative_humidity_2m', [])
        precipitation = hourly.get('precipitation', [])
        windspeed = hourly.get('windspeed_10m', [])
        visibility = hourly.get('visibility', [])
        soil_temperature_0cm = hourly.get('soil_temperature_0cm', [])
        soil_temperature_6cm = hourly.get('soil_temperature_6cm', [])
        soil_temperature_18cm = hourly.get('soil_temperature_18cm', [])
        soil_temperature_54cm = hourly.get('soil_temperature_54cm', [])

        # График температуры
        fig_temp, ax_temp = plt.subplots(figsize=(8, 4))
        ax_temp.plot(times, temperature, label='Температура (°C)', color='red')
        ax_temp.set_title('Температура')
        ax_temp.set_xticks(times[::24])
        ax_temp.set_xticklabels(times[::24], rotation=45)
        ax_temp.legend()
        plt.tight_layout()

        canvas_temp = FigureCanvasTkAgg(fig_temp, master=frame)
        canvas_temp.draw()
        canvas_temp.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График влажности
        fig_humidity, ax_humidity = plt.subplots(figsize=(8, 4))
        ax_humidity.plot(times, humidity, label='Влажность (%)', color='blue')
        ax_humidity.set_title('Влажность')
        ax_humidity.set_xticks(times[::24])
        ax_humidity.set_xticklabels(times[::24], rotation=45)
        ax_humidity.legend()
        plt.tight_layout()

        canvas_humidity = FigureCanvasTkAgg(fig_humidity, master=frame)
        canvas_humidity.draw()
        canvas_humidity.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График осадков
        fig_precip, ax_precip = plt.subplots(figsize=(8, 4))
        ax_precip.bar(times, precipitation, label='Осадки (мм)', color='green')
        ax_precip.set_title('Осадки')
        ax_precip.set_xticks(times[::24])
        ax_precip.set_xticklabels(times[::24], rotation=45)
        ax_precip.legend()
        plt.tight_layout()

        canvas_precip = FigureCanvasTkAgg(fig_precip, master=frame)
        canvas_precip.draw()
        canvas_precip.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График скорости ветра
        fig_wind, ax_wind = plt.subplots(figsize=(8, 4))
        ax_wind.plot(times, windspeed, label='Скорость ветра (м/с)', color='orange')
        ax_wind.set_title('Скорость ветра')
        ax_wind.set_xticks(times[::24])
        ax_wind.set_xticklabels(times[::24], rotation=45)
        ax_wind.legend()
        plt.tight_layout()

        canvas_wind = FigureCanvasTkAgg(fig_wind, master=frame)
        canvas_wind.draw()
        canvas_wind.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График видимости
        fig_visibility, ax_visibility = plt.subplots(figsize=(8, 4))
        ax_visibility.plot(times, visibility, label='Видимость (м)', color='purple')
        ax_visibility.set_title('Видимость')
        ax_visibility.set_xticks(times[::24])
        ax_visibility.set_xticklabels(times[::24], rotation=45)
        ax_visibility.legend()
        plt.tight_layout()

        canvas_visibility = FigureCanvasTkAgg(fig_visibility, master=frame)
        canvas_visibility.draw()
        canvas_visibility.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График температуры почвы на глубине 0 см
        fig_soil_temp_0cm, ax_soil_temp_0cm = plt.subplots(figsize=(8, 4))
        ax_soil_temp_0cm.plot(times, soil_temperature_0cm, label='Температура почвы (0 см)', color='brown')
        ax_soil_temp_0cm.set_title('Температура почвы (0 см)')
        ax_soil_temp_0cm.set_xticks(times[::24])
        ax_soil_temp_0cm.set_xticklabels(times[::24], rotation=45)
        ax_soil_temp_0cm.legend()
        plt.tight_layout()

        canvas_soil_temp_0cm = FigureCanvasTkAgg(fig_soil_temp_0cm, master=frame)
        canvas_soil_temp_0cm.draw()
        canvas_soil_temp_0cm.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График температуры почвы на глубине 6 см
        fig_soil_temp_6cm, ax_soil_temp_6cm = plt.subplots(figsize=(8, 4))
        ax_soil_temp_6cm.plot(times, soil_temperature_6cm, label='Температура почвы (6 см)', color='purple')
        ax_soil_temp_6cm.set_title('Температура почвы (6 см)')
        ax_soil_temp_6cm.set_xticks(times[::24])
        ax_soil_temp_6cm.set_xticklabels(times[::24], rotation=45)
        ax_soil_temp_6cm.legend()
        plt.tight_layout()

        canvas_soil_temp_6cm = FigureCanvasTkAgg(fig_soil_temp_6cm, master=frame)
        canvas_soil_temp_6cm.draw()
        canvas_soil_temp_6cm.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График температуры почвы на глубине 18 см
        fig_soil_temp_18cm, ax_soil_temp_18cm = plt.subplots(figsize=(8, 4))
        ax_soil_temp_18cm.plot(times, soil_temperature_18cm, label='Температура почвы (18 см)', color='brown')
        ax_soil_temp_18cm.set_title('Температура почвы (18 см)')
        ax_soil_temp_18cm.set_xticks(times[::24])
        ax_soil_temp_18cm.set_xticklabels(times[::24], rotation=45)
        ax_soil_temp_18cm.legend()
        plt.tight_layout()

        canvas_soil_temp_18cm = FigureCanvasTkAgg(fig_soil_temp_18cm, master=frame)
        canvas_soil_temp_18cm.draw()
        canvas_soil_temp_18cm.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

        # График температуры почвы на глубине 54 см
        fig_soil_temp_54cm, ax_soil_temp_54cm = plt.subplots(figsize=(8, 4))
        ax_soil_temp_54cm.plot(times, soil_temperature_54cm, label='Температура почвы (54 см)', color='purple')
        ax_soil_temp_54cm.set_title('Температура почвы (54 см)')
        ax_soil_temp_54cm.set_xticks(times[::24])
        ax_soil_temp_54cm.set_xticklabels(times[::24], rotation=45)
        ax_soil_temp_54cm.legend()
        plt.tight_layout()

        canvas_soil_temp_54cm = FigureCanvasTkAgg(fig_soil_temp_54cm, master=frame)
        canvas_soil_temp_54cm.draw()
        canvas_soil_temp_54cm.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

    def update_7_day_weather(self):
        """Обновляет данные и отображает прогноз на 7 дней."""
        if self.current_city:
            data = self.get_7_day_weather_data(self.current_city)
            if data:
                self.show_weather_forecast(data, self.frame_forecast)
                self.plot_weather(data, self.frame_chart)
                self.label_no_city.grid_remove()
            else:
                self.label_no_city.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        else:
            self.label_no_city.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    def update_hourly_weather(self):
        """Обновляет данные и отображает почасовой прогноз."""
        if self.current_city:
            if self.hourly_data is None:
                self.hourly_data = self.get_hourly_weather_data(self.current_city)
            if self.hourly_data:
                self.show_hourly_weather_forecast(self.hourly_data, self.frame_hourly)
                self.plot_hourly_weather(self.hourly_data, self.frame_hourly_chart)
                self.label_no_city_hourly.grid_remove()
            else:
                self.label_no_city_hourly.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        else:
            self.label_no_city_hourly.grid(row=3, column=0, padx=10, pady=5, sticky="w")

    def show_tab(self, tab_name):
        """Переключает между вкладками."""
        if tab_name == "Город":
            self.frame_city.grid(row=1, column=1, sticky="nsew")
            self.frame_weather.grid_remove()
            self.frame_forecast_tab.grid_remove()
            self.frame_hourly_tab.grid_remove()
            self.frame_settings.grid_remove()
        elif tab_name == "Погода":
            self.frame_weather.grid(row=1, column=1, sticky="nsew")
            self.frame_city.grid_remove()
            self.frame_forecast_tab.grid_remove()
            self.frame_hourly_tab.grid_remove()
            self.frame_settings.grid_remove()
        elif tab_name == "Прогноз на 7 дней":
            self.frame_forecast_tab.grid(row=1, column=1, sticky="nsew")
            self.frame_city.grid_remove()
            self.frame_weather.grid_remove()
            self.frame_hourly_tab.grid_remove()
            self.frame_settings.grid_remove()
        elif tab_name == "Почасовые Погодные Переменные":
            self.frame_hourly_tab.grid(row=1, column=1, sticky="nsew")
            self.frame_city.grid_remove()
            self.frame_weather.grid_remove()
            self.frame_forecast_tab.grid_remove()
            self.frame_settings.grid_remove()
        elif tab_name == "Настройки":
            self.frame_settings.grid(row=1, column=1, sticky="nsew")
            self.frame_city.grid_remove()
            self.frame_weather.grid_remove()
            self.frame_forecast_tab.grid_remove()
            self.frame_hourly_tab.grid_remove()

    def on_closing(self):
        """Завершает приложение при закрытии окна."""
        print("Приложение закрыто")
        os._exit(0)

# Запуск приложения
if __name__ == "__main__":
    app = ctk.CTk()
    weather_app = WeatherApp(app)
    app.protocol("WM_DELETE_WINDOW", weather_app.on_closing)
    app.mainloop()
