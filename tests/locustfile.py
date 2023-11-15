from locust import HttpUser, task
from random import randint


class HelloWorldUser(HttpUser):
    @task
    def hello_world(self):
        self.client.get(
            f"http://localhost:8000/split_compare/?user_id_1={randint(1, 1000)}&user_id_2=219&event_id=1&competition_date=2023-09-09")
