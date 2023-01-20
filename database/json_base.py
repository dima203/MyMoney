from pathlib import Path
import json


class JSONBase:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def load(self) -> dict:
        try:
            return json.load(self.path.open())
        except FileNotFoundError:
            json.dump({}, self.path.open('w'))
            return json.load(self.path.open())

    def save(self, data: dict) -> None:
        json.dump(data, self.path.open("w"), indent=2)
