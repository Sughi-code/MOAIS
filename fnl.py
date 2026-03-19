#!/usr/bin/env python3

import json
import sys
import os
import tempfile
from collections import defaultdict, Counter


class Movies:
    """Класс для работы с информацией о фильмах"""

    def __init__(self, movies_data):
        """Инициализация данными о фильмах"""
        self.movies = movies_data
        self.movie_dict = {movie['movieId']: movie for movie in self.movies}
        self.title_to_id = {movie['title']: movie['movieId'] for movie in self.movies}

    def get_all_genres(self):
        """Возвращает список уникальных жанров"""
        genres_set = set()
        for movie in self.movies:
            if 'genres' in movie and movie['genres']:
                for genre in movie['genres'].split('|'):
                    if genre and genre != '(no genres listed)':
                        genres_set.add(genre.strip())
        return sorted(genres_set)

    def display_genres(self):
        """Выводит пронумерованный список жанров"""
        genres = self.get_all_genres()
        result = []
        for idx, genre in enumerate(genres, 1):
            result.append(f"{idx}. {genre}")
        return result

    def get_top_movies_by_genre(self, genre_id, n=5):
        """
        Возвращает топ-n фильмов в указанном жанре по названию
        genre_id: номер жанра из списка (начиная с 1)
        """
        genres = self.get_all_genres()
        if genre_id < 1 or genre_id > len(genres):
            raise ValueError(f"Invalid genre ID. Must be between 1 and {len(genres)}")

        target_genre = genres[genre_id - 1]
        filtered_movies = []

        for movie in self.movies:
            if 'genres' in movie and movie['genres']:
                movie_genres = [g.strip() for g in movie['genres'].split('|')]
                if target_genre in movie_genres:
                    filtered_movies.append(movie['title'])

        # Сортируем по алфавиту для консистентности
        filtered_movies.sort()

        return filtered_movies[:n] if len(filtered_movies) >= n else filtered_movies

    def get_movie_id_by_title(self, movie_title):
        """Возвращает ID фильма по его названию"""
        movie_id = self.title_to_id.get(movie_title)
        if movie_id is None:
            raise ValueError(f"Movie '{movie_title}' not found")
        return movie_id

    def get_movie_title_by_id(self, movie_id):
        """Возвращает название фильма по его ID"""
        movie = self.movie_dict.get(movie_id)
        if movie is None:
            raise ValueError(f"Movie ID {movie_id} not found")
        return movie['title']


class User(Movies):
    """Класс пользователя, наследующий функционал работы с фильмами"""

    def __init__(self, user_id, movielens_data):
        """
        Инициализация пользователя с доступом к данным фильмов
        Наследует все методы класса Movies
        """
        super().__init__(movielens_data.movies)
        self.user_id = user_id
        self.ratings = movielens_data.user_ratings.get(user_id, [])
        self.movie_ratings = movielens_data.get_user_movie_ratings(user_id)

    def get_user_rating_count(self):
        """Возвращает количество оценок пользователя"""
        return len(self.ratings)

    def get_user_average_rating(self):
        """Возвращает средний рейтинг пользователя"""
        if not self.ratings:
            return 0.0
        return sum(self.ratings) / len(self.ratings)


class MovieLensData:
    """Основной класс для анализа данных MovieLens с объединенными данными"""

    def __init__(self, movies_path, ratings_path, tags_path, links_path):
        """
        Конструктор объединяет данные из всех источников в единое поле self.merged_data
        """
        # Загрузка фильмов
        with open(movies_path, 'r', encoding='utf-8') as f:
            self.movies = json.load(f)

        # Создание индекса фильмов
        self.movie_dict = {movie['movieId']: movie for movie in self.movies}
        self.title_to_id = {movie['title']: movie['movieId'] for movie in self.movies}

        # Загрузка и объединение рейтингов с фильмами
        with open(ratings_path, 'r', encoding='utf-8') as f:
            ratings_data = json.load(f)

        # Агрегация рейтингов
        self.movie_ratings = defaultdict(list)
        self.user_ratings = defaultdict(list)
        self.rating_records = []

        for rating in ratings_data:
            movie_id = rating['movieId']
            user_id = rating['userId']
            rating_value = float(rating['rating'])

            self.movie_ratings[movie_id].append(rating_value)
            self.user_ratings[user_id].append(rating_value)
            self.rating_records.append(rating)

        # Загрузка и объединение тегов
        with open(tags_path, 'r', encoding='utf-8') as f:
            tags_data = json.load(f)

        self.movie_tags = defaultdict(list)
        for tag in tags_data:
            movie_id = tag['movieId']
            tag_text = tag['tag'].strip().lower()
            if tag_text:
                self.movie_tags[movie_id].append(tag_text)

        # Загрузка и объединение ссылок с фильмами
        with open(links_path, 'r', encoding='utf-8') as f:
            links_data = json.load(f)

        self.link_dict = {link['movieId']: link for link in links_data}

        # Формирование единого поля с объединенными данными (требование задания)
        self.merged_data = self._create_merged_data()

    def _create_merged_data(self):
        """Создает единое поле с объединенными данными из всех источников"""
        merged = {}
        for movie_id, movie in self.movie_dict.items():
            merged[movie_id] = {
                'movieId': movie_id,
                'title': movie.get('title', ''),
                'genres': movie.get('genres', ''),
                'ratings': self.movie_ratings.get(movie_id, []),
                'tags': self.movie_tags.get(movie_id, []),
                'links': self.link_dict.get(movie_id, {})
            }
        return merged

    def _calculate_median(self, values):
        """Расчет медианы без использования внешних библиотек"""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        else:
            return float(sorted_vals[n // 2])

    def top_by_ratings(self, n=5, stat='mean'):
        """
        Возвращает топ-n фильмов по рейтингу
        stat: 'mean' (среднее) или 'median' (медиана)
        Возвращает список кортежей: (название фильма, значение статистики, количество оценок)
        """
        movie_stats = []

        for movie_id, ratings in self.movie_ratings.items():
            if not ratings:
                continue

            if stat == 'mean':
                stat_value = sum(ratings) / len(ratings)
            elif stat == 'median':
                stat_value = self._calculate_median(ratings)
            else:
                raise ValueError(f"Unsupported statistic: {stat}. Use 'mean' or 'median'")

            count = len(ratings)
            movie_title = self.movie_dict[movie_id].get('title', f"Movie {movie_id}")
            movie_stats.append((movie_title, stat_value, count))

        # Сортировка: по статистике (убывание), затем по количеству оценок (убывание)
        movie_stats.sort(key=lambda x: (-x[1], -x[2]))

        return movie_stats[:n]

    def get_worst_rated_movies(self, n=5):
        """
        Возвращает топ-n фильмов с худшими рейтингами (по среднему значению)
        Возвращает список кортежей: (название фильма, средний рейтинг, количество оценок)
        """
        movie_stats = []

        for movie_id, ratings in self.movie_ratings.items():
            if not ratings:
                continue

            avg_rating = sum(ratings) / len(ratings)
            count = len(ratings)
            movie_title = self.movie_dict[movie_id].get('title', f"Movie {movie_id}")
            movie_stats.append((movie_title, avg_rating, count))

        # Сортировка: по рейтингу (возрастание), затем по количеству оценок (убывание)
        movie_stats.sort(key=lambda x: (x[1], -x[2]))

        return movie_stats[:n]

    def get_most_active_users(self, n=5):
        """
        Возвращает топ-n пользователей по количеству оценок
        Возвращает список кортежей: (user_id, количество оценок)
        """
        user_activity = [(user_id, len(ratings)) for user_id, ratings in self.user_ratings.items()]
        user_activity.sort(key=lambda x: x[1], reverse=True)
        return user_activity[:n]

    def get_user_movie_ratings(self, user_id):
        """Возвращает словарь {название_фильма: рейтинг} для пользователя"""
        user_movie_ratings = {}
        for rating in self.rating_records:
            if rating['userId'] == user_id:
                movie_id = rating['movieId']
                movie_title = self.movie_dict.get(movie_id, {}).get('title', f"Movie {movie_id}")
                user_movie_ratings[movie_title] = float(rating['rating'])
        return user_movie_ratings

    def get_tags_for_movie(self, movie_title):
        """Возвращает список уникальных тегов для фильма по его названию"""
        movie_id = self.title_to_id.get(movie_title)
        if movie_id is None:
            raise ValueError(f"Movie '{movie_title}' not found")

        tags = self.movie_tags.get(movie_id, [])
        return list(set(tags))

    def get_popular_tags(self, n=10):
        """Возвращает топ-n популярных тегов по всем фильмам"""
        all_tags = []
        for tags_list in self.movie_tags.values():
            all_tags.extend(tags_list)

        tag_counter = Counter(all_tags)
        return tag_counter.most_common(n)

    def get_IMDb(self, movie_title):
        """
        Возвращает ссылку на фильм на IMDb по названию фильма
        Обрабатывает исключения для несуществующих фильмов
        """
        try:
            movie_id = self.title_to_id.get(movie_title)
            if movie_id is None:
                raise ValueError(f"Movie '{movie_title}' not found")

            link_info = self.link_dict.get(movie_id)
            if not link_info or 'imdbId' not in link_info:
                raise ValueError(f"No IMDb link found for movie '{movie_title}'")

            imdb_id = str(link_info['imdbId']).zfill(7)  # Форматирование ID до 7 цифр
            return f"https://www.imdb.com/title/tt{imdb_id}/"  # ИСПРАВЛЕНО: убраны пробелы!

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Failed to get IMDb link for '{movie_title}': {e}")


class Tests:
    """Класс для тестирования функционала с использованием PyTest"""

    @staticmethod
    def create_test_data():
        """Создает минимальный набор тестовых данных во временных файлах"""
        movies = [
            {"movieId": 1, "title": "Inception", "genres": "Sci-Fi|Action"},
            {"movieId": 2, "title": "The Godfather", "genres": "Crime|Drama"},
            {"movieId": 3, "title": "Pulp Fiction", "genres": "Crime|Drama"},
            {"movieId": 4, "title": "The Dark Knight", "genres": "Action|Crime"},
            {"movieId": 5, "title": "Forrest Gump", "genres": "Drama|Romance"}
        ]

        ratings = [
            {"userId": 1, "movieId": 1, "rating": 5.0, "timestamp": 1234567890},
            {"userId": 1, "movieId": 2, "rating": 4.5, "timestamp": 1234567891},
            {"userId": 1, "movieId": 3, "rating": 4.0, "timestamp": 1234567892},
            {"userId": 2, "movieId": 1, "rating": 5.0, "timestamp": 1234567893},
            {"userId": 2, "movieId": 4, "rating": 4.5, "timestamp": 1234567894},
            {"userId": 3, "movieId": 5, "rating": 5.0, "timestamp": 1234567895},
            {"userId": 3, "movieId": 2, "rating": 4.0, "timestamp": 1234567896},
            {"userId": 4, "movieId": 3, "rating": 3.5, "timestamp": 1234567897},
            {"userId": 4, "movieId": 4, "rating": 4.0, "timestamp": 1234567898},
            {"userId": 5, "movieId": 5, "rating": 4.5, "timestamp": 1234567899}
        ]

        tags = [
            {"userId": 1, "movieId": 1, "tag": "mind-bending", "timestamp": 1234567890},
            {"userId": 1, "movieId": 1, "tag": "amazing", "timestamp": 1234567891},
            {"userId": 2, "movieId": 2, "tag": "classic", "timestamp": 1234567892},
            {"userId": 2, "movieId": 2, "tag": "masterpiece", "timestamp": 1234567893},
            {"userId": 3, "movieId": 3, "tag": "dialogue", "timestamp": 1234567894}
        ]

        links = [
            {"movieId": 1, "imdbId": 1375666, "tmdbId": 27205},
            {"movieId": 2, "imdbId": 238, "tmdbId": 238},
            {"movieId": 3, "imdbId": 110912, "tmdbId": 680},
            {"movieId": 4, "imdbId": 13434, "tmdbId": 155},
            {"movieId": 5, "imdbId": 10884, "tmdbId": 13}
        ]

        # Создаем временную директорию для тестовых файлов
        temp_dir = tempfile.mkdtemp()

        movies_path = os.path.join(temp_dir, 'movies.json')
        ratings_path = os.path.join(temp_dir, 'ratings.json')
        tags_path = os.path.join(temp_dir, 'tags.json')
        links_path = os.path.join(temp_dir, 'links.json')

        with open(movies_path, 'w', encoding='utf-8') as f:
            json.dump(movies, f)

        with open(ratings_path, 'w', encoding='utf-8') as f:
            json.dump(ratings, f)

        with open(tags_path, 'w', encoding='utf-8') as f:
            json.dump(tags, f)

        with open(links_path, 'w', encoding='utf-8') as f:
            json.dump(links, f)

        return movies_path, ratings_path, tags_path, links_path, temp_dir

    # ===== ТЕСТЫ ДЛЯ КЛАССА MOVIES =====

    def test_movies_get_all_genres_returns_list(self):
        """Проверка: get_all_genres возвращает список"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        genres = movies.get_all_genres()

        assert isinstance(genres, list), "get_all_genres must return a list"

    def test_movies_get_all_genres_elements_are_strings(self):
        """Проверка: элементы get_all_genres являются строками"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        genres = movies.get_all_genres()

        assert all(isinstance(g, str) for g in genres), "All genres must be strings"

    def test_movies_get_all_genres_is_sorted(self):
        """Проверка: get_all_genres возвращает отсортированный список"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        genres = movies.get_all_genres()

        assert genres == sorted(genres), "Genres must be sorted alphabetically"

    def test_movies_display_genres_returns_list_of_strings(self):
        """Проверка: display_genres возвращает список строк"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        genre_lines = movies.display_genres()

        assert isinstance(genre_lines, list), "display_genres must return a list"
        assert all(isinstance(line, str) for line in genre_lines), "All lines must be strings"

    def test_movies_get_top_movies_by_genre_returns_list(self):
        """Проверка: get_top_movies_by_genre возвращает список"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        drama_movies = movies.get_top_movies_by_genre(2, 5)  # Drama - жанр №2

        assert isinstance(drama_movies, list), "get_top_movies_by_genre must return a list"

    def test_movies_get_top_movies_by_genre_elements_are_strings(self):
        """Проверка: элементы get_top_movies_by_genre являются строками (названиями)"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        drama_movies = movies.get_top_movies_by_genre(2, 5)

        assert all(isinstance(title, str) for title in drama_movies), "All items must be strings (movie titles)"

    def test_movies_get_top_movies_by_genre_is_sorted(self):
        """Проверка: get_top_movies_by_genre возвращает отсортированный по алфавиту список"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        drama_movies = movies.get_top_movies_by_genre(2, 5)

        assert drama_movies == sorted(drama_movies), "Movies must be sorted alphabetically"

    def test_movies_get_movie_id_by_title_returns_int(self):
        """Проверка: get_movie_id_by_title возвращает целое число"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        movie_id = movies.get_movie_id_by_title("Inception")

        assert isinstance(movie_id, int), "get_movie_id_by_title must return an integer"

    def test_movies_get_movie_title_by_id_returns_string(self):
        """Проверка: get_movie_title_by_id возвращает строку"""
        movies_path, _, _, _, temp_dir = self.create_test_data()
        with open(movies_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        movies = Movies(movies_data)
        title = movies.get_movie_title_by_id(1)

        assert isinstance(title, str), "get_movie_title_by_id must return a string"

    # ===== ТЕСТЫ ДЛЯ КЛАССА USER =====

    def test_user_get_user_rating_count_returns_int(self):
        """Проверка: get_user_rating_count возвращает целое число"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        user = User(1, movielens)
        count = user.get_user_rating_count()

        assert isinstance(count, int), "get_user_rating_count must return an integer"
        assert count >= 0, "Rating count must be non-negative"

    def test_user_get_user_average_rating_returns_float(self):
        """Проверка: get_user_average_rating возвращает число с плавающей точкой"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        user = User(1, movielens)
        avg_rating = user.get_user_average_rating()

        assert isinstance(avg_rating, float), "get_user_average_rating must return a float"

    # ===== ТЕСТЫ ДЛЯ КЛАССА MOVIELENSDATA =====

    def test_movielens_top_by_ratings_returns_list(self):
        """Проверка: top_by_ratings возвращает список"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        top_movies = movielens.top_by_ratings(n=3, stat='mean')

        assert isinstance(top_movies, list), "top_by_ratings must return a list"

    def test_movielens_top_by_ratings_elements_are_tuples(self):
        """Проверка: элементы top_by_ratings являются кортежами"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        top_movies = movielens.top_by_ratings(n=3, stat='mean')

        assert all(isinstance(item, tuple) for item in top_movies), "All items must be tuples"
        assert all(len(item) == 3 for item in top_movies), "Each tuple must have 3 elements"

    def test_movielens_top_by_ratings_tuple_types(self):
        """Проверка: типы элементов кортежей top_by_ratings (str, float, int)"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        top_movies = movielens.top_by_ratings(n=3, stat='mean')

        for title, rating, count in top_movies:
            assert isinstance(title, str), "First element must be a string (movie title)"
            assert isinstance(rating, float), "Second element must be a float (rating)"
            assert isinstance(count, int), "Third element must be an integer (count)"

    def test_movielens_top_by_ratings_sorted_descending(self):
        """Проверка: top_by_ratings отсортирован по убыванию рейтинга"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        top_movies = movielens.top_by_ratings(n=5, stat='mean')

        if len(top_movies) > 1:
            for i in range(len(top_movies) - 1):
                assert top_movies[i][1] >= top_movies[i + 1][1], \
                    f"Movies must be sorted by rating descending: {top_movies[i][1]} >= {top_movies[i + 1][1]}"

    def test_movielens_get_worst_rated_movies_returns_list(self):
        """Проверка: get_worst_rated_movies возвращает список"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        worst_movies = movielens.get_worst_rated_movies(n=3)

        assert isinstance(worst_movies, list), "get_worst_rated_movies must return a list"

    def test_movielens_get_worst_rated_movies_sorted_ascending(self):
        """Проверка: get_worst_rated_movies отсортирован по возрастанию рейтинга"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        worst_movies = movielens.get_worst_rated_movies(n=5)

        if len(worst_movies) > 1:
            for i in range(len(worst_movies) - 1):
                assert worst_movies[i][1] <= worst_movies[i + 1][1], \
                    f"Movies must be sorted by rating ascending: {worst_movies[i][1]} <= {worst_movies[i + 1][1]}"

    def test_movielens_get_most_active_users_returns_list(self):
        """Проверка: get_most_active_users возвращает список"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        active_users = movielens.get_most_active_users(n=3)

        assert isinstance(active_users, list), "get_most_active_users must return a list"

    def test_movielens_get_most_active_users_elements_are_tuples(self):
        """Проверка: элементы get_most_active_users являются кортежами (int, int)"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        active_users = movielens.get_most_active_users(n=3)

        assert all(isinstance(item, tuple) for item in active_users), "All items must be tuples"
        assert all(len(item) == 2 for item in active_users), "Each tuple must have 2 elements"

        for user_id, count in active_users:
            assert isinstance(user_id, int), "First element must be an integer (user_id)"
            assert isinstance(count, int), "Second element must be an integer (count)"

    def test_movielens_get_most_active_users_sorted_descending(self):
        """Проверка: get_most_active_users отсортирован по убыванию активности"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        active_users = movielens.get_most_active_users(n=5)

        if len(active_users) > 1:
            for i in range(len(active_users) - 1):
                assert active_users[i][1] >= active_users[i + 1][1], \
                    f"Users must be sorted by activity descending: {active_users[i][1]} >= {active_users[i + 1][1]}"

    def test_movielens_get_user_movie_ratings_returns_dict(self):
        """Проверка: get_user_movie_ratings возвращает словарь {str: float}"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        user_ratings = movielens.get_user_movie_ratings(1)

        assert isinstance(user_ratings, dict), "get_user_movie_ratings must return a dictionary"
        assert all(isinstance(key, str) for key in user_ratings.keys()), "All keys must be strings (movie titles)"
        assert all(isinstance(value, float) for value in user_ratings.values()), "All values must be floats (ratings)"

    def test_movielens_get_tags_for_movie_returns_list(self):
        """Проверка: get_tags_for_movie возвращает список"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        tags = movielens.get_tags_for_movie("Inception")

        assert isinstance(tags, list), "get_tags_for_movie must return a list"

    def test_movielens_get_tags_for_movie_elements_are_strings(self):
        """Проверка: элементы get_tags_for_movie являются строками"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        tags = movielens.get_tags_for_movie("Inception")

        assert all(isinstance(tag, str) for tag in tags), "All tags must be strings"

    def test_movielens_get_popular_tags_returns_list(self):
        """Проверка: get_popular_tags возвращает список"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        popular_tags = movielens.get_popular_tags(n=3)

        assert isinstance(popular_tags, list), "get_popular_tags must return a list"

    def test_movielens_get_popular_tags_elements_are_tuples(self):
        """Проверка: элементы get_popular_tags являются кортежами (str, int)"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        popular_tags = movielens.get_popular_tags(n=3)

        assert all(isinstance(item, tuple) for item in popular_tags), "All items must be tuples"
        assert all(len(item) == 2 for item in popular_tags), "Each tuple must have 2 elements"

        for tag, count in popular_tags:
            assert isinstance(tag, str), "First element must be a string (tag)"
            assert isinstance(count, int), "Second element must be an integer (count)"

    def test_movielens_get_popular_tags_sorted_descending(self):
        """Проверка: get_popular_tags отсортирован по убыванию частоты"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        popular_tags = movielens.get_popular_tags(n=5)

        if len(popular_tags) > 1:
            for i in range(len(popular_tags) - 1):
                assert popular_tags[i][1] >= popular_tags[i + 1][1], \
                    f"Tags must be sorted by frequency descending: {popular_tags[i][1]} >= {popular_tags[i + 1][1]}"

    def test_movielens_get_IMDb_returns_valid_url(self):
        """Проверка: get_IMDb возвращает корректную строку URL без пробелов"""
        movies_path, ratings_path, tags_path, links_path, temp_dir = self.create_test_data()
        movielens = MovieLensData(movies_path, ratings_path, tags_path, links_path)

        imdb_url = movielens.get_IMDb("Inception")

        assert isinstance(imdb_url, str), "get_IMDb must return a string"
        assert imdb_url.startswith("https://www.imdb.com/title/tt"), "URL must start with IMDb base"
        assert "tt " not in imdb_url, "CRITICAL: URL must not contain spaces after 'tt'"  # Критическая проверка!
        assert imdb_url.endswith("/"), "URL must end with a slash"
        assert len(imdb_url) > 30, "URL must have reasonable length"


def main():
    """
    Создание отчета с использованием всех методов классов
    """
    try:
        # Инициализация единого объекта с объединенными данными
        movielens = MovieLensData(
            'movies.json',
            'ratings.json',
            'tags.json',
            'links.json'
        )

        # Инициализация объекта фильмов для наследования
        movies = Movies(movielens.movies)

        print("=" * 70)
        print("MOVIELENS DATA ANALYSIS REPORT")
        print("=" * 70)

        # 1. Вывод списка жанров (метод display_genres)
        print("\n1. Доступные жанры:")
        for genre_line in movies.display_genres():
            print(f"   {genre_line}")

        # 2. Топ-5 фильмов по среднему рейтингу (метод top_by_ratings с stat='mean')
        print("\n2. Топ-5 фильмов с лучшими средними рейтингами:")
        top_movies_mean = movielens.top_by_ratings(n=5, stat='mean')
        for idx, (title, avg_rating, count) in enumerate(top_movies_mean, 1):
            print(f"   {idx}. {title}")
            print(f"      Средний рейтинг: {avg_rating:.2f} ({count} оценок)")

        # 3. Топ-5 фильмов по медиане рейтинга (метод top_by_ratings с stat='median')
        print("\n3. Топ-5 фильмов по медиане рейтинга:")
        top_movies_median = movielens.top_by_ratings(n=5, stat='median')
        for idx, (title, median_rating, count) in enumerate(top_movies_median, 1):
            print(f"   {idx}. {title}")
            print(f"      Медиана рейтинга: {median_rating:.2f} ({count} оценок)")

        # 4. Топ-5 фильмов с худшими рейтингами (метод get_worst_rated_movies)
        print("\n4. Топ-5 фильмов с худшими рейтингами:")
        worst_movies = movielens.get_worst_rated_movies(n=5)
        for idx, (title, avg_rating, count) in enumerate(worst_movies, 1):
            print(f"   {idx}. {title}")
            print(f"      Средний рейтинг: {avg_rating:.2f} ({count} оценок)")

        # 5. Топ-5 самых активных пользователей (метод get_most_active_users)
        print("\n5. Топ-5 самых активных пользователей:")
        active_users = movielens.get_most_active_users(n=5)
        for idx, (user_id, count) in enumerate(active_users, 1):
            print(f"   {idx}. Пользователь {user_id} - {count} оценок")

            # Создание объекта User для демонстрации наследования
            if idx == 1:  # Для первого пользователя создаем объект User
                user_obj = User(user_id, movielens)
                avg_user_rating = user_obj.get_user_average_rating()
                rating_count = user_obj.get_user_rating_count()
                print(f"      Количество оценок: {rating_count}")
                print(f"      Средний рейтинг: {avg_user_rating:.2f}")

        # 6. Фильмы в жанре (метод get_top_movies_by_genre)
        print("\n6. Топ-5 фильмов в жанре 'Drama' (жанр №2):")
        drama_movies = movies.get_top_movies_by_genre(2, 5)
        for idx, title in enumerate(drama_movies, 1):
            print(f"   {idx}. {title}")

        # 7. Теги для фильма (метод get_tags_for_movie)
        if top_movies_mean:
            sample_movie = top_movies_mean[0][0]
            print(f"\n7. Теги для фильма '{sample_movie}':")
            tags = movielens.get_tags_for_movie(sample_movie)
            if tags:
                for idx, tag in enumerate(tags[:5], 1):  # Первые 5 тегов
                    print(f"   {idx}. {tag}")
            else:
                print("   Нет тегов")

        # 8. Популярные теги (метод get_popular_tags)
        print("\n8. Топ-5 самых популярных тегов:")
        popular_tags = movielens.get_popular_tags(n=5)
        for idx, (tag, count) in enumerate(popular_tags, 1):
            print(f"   {idx}. {tag} ({count} раз)")

        # 9. Ссылка на IMDb (метод get_IMDb) - ИСПРАВЛЕНО: без пробелов
        if top_movies_mean:
            first_movie = top_movies_mean[0][0]
            print(f"\n9. Ссылка на IMDb для '{first_movie}':")
            try:
                imdb_link = movielens.get_IMDb(first_movie)
                print(f"   {imdb_link}")
                # Дополнительная проверка отсутствия пробелов в продакшен-режиме
                if "tt " in imdb_link:
                    print("   WARNING: URL contains spaces! This is a critical error.", file=sys.stderr)
                    sys.exit(1)
            except ValueError as e:
                print(f"   Ошибка: {e}")

        # 10. Демонстрация наследования: создание объекта User и вызов унаследованных методов
        print("\n10. Демонстрация наследования (класс User наследует от Movies):")
        if active_users:
            top_user_id = active_users[0][0]
            user_demo = User(top_user_id, movielens)
            # Вызов унаследованных методов
            genres = user_demo.get_all_genres()
            print(f"    Количество жанров в системе: {len(genres)}")
            print(f"    Примеры жанров: {', '.join(genres[:3])}")
            # Получение ID фильма через унаследованный метод
            movie_id = user_demo.get_movie_id_by_title(top_movies_mean[0][0])
            print(f"    ID фильма '{top_movies_mean[0][0]}': {movie_id}")

        # 11. Демонстрация получения рейтингов пользователя (метод get_user_movie_ratings)
        print("\n11. Рейтинги пользователя 1 по фильмам:")
        user_ratings = movielens.get_user_movie_ratings(1)
        for idx, (title, rating) in enumerate(list(user_ratings.items())[:5], 1):
            print(f"    {idx}. {title}: {rating:.1f}")

        print("\n" + "=" * 70)
        print("АНАЛИЗ ЗАВЕРШЕН УСПЕШНО")
        print("=" * 70)
        print("\nДля запуска тестов выполните: pytest movielens_analysis.py::Tests -v")

    except FileNotFoundError as e:
        print(f"Ошибка: не найден файл данных - {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Ошибка валидации данных: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка при выполнении анализа: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()