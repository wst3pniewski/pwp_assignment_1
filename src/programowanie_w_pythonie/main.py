import csv
import time
from datetime import datetime
from pathlib import Path

import requests


class CustomError(Exception):
    pass


class NotFoundError(CustomError):
    pass


class AccessDeniedError(CustomError):
    pass


def measure_time(func):
    def wrapper(*args, **kwargs):
        print(f"Measuring function **{func.__name__}**")
        start_time = time.time()
        print(f"Start time: {datetime.fromtimestamp(start_time)}")
        res = func(*args, **kwargs)
        end_time = time.time()
        print(f"End time: {datetime.fromtimestamp(end_time)}")
        print(f"Execution time: {end_time - start_time} s")
        return res

    return wrapper


def get_file(file_url: str, file_save_path: Path) -> None:
    r = requests.get(file_url)
    if r.status_code == 403:
        raise AccessDeniedError("Access to this resource is denied!")
    elif r.status_code == 404:
        raise NotFoundError("Resource not found")

    with open(file_save_path, "w", encoding="utf-8") as f:
        f.write(r.text)


class SimpleETL:
    def __init__(
        self,
        input_path: str | Path,
        delimiter: str = ",",
        has_header: bool = False,
        missing_marker: str = "-",
    ) -> None:
        self.input_path = Path(input_path)
        if self.input_path.suffix.lower() != ".csv":
            raise ValueError("Only csv files are supported!")
        self.delimiter = delimiter
        self.has_header = has_header
        self.missing_marker = missing_marker

    def extract(self):
        with open(self.input_path, encoding="utf-8") as f:
            reader = csv.DictReader(
                f,
                delimiter=self.delimiter,
                fieldnames=["id", "f1", "f2", "f3", "f4", "f5", "f6", "f7"],
            )
            yield from reader

    @measure_time
    def transform(self, seq):
        for row in seq:
            fields = {k: v for k, v in row.items() if k != "id"}
            indexes = [
                int(k.removeprefix("f"))
                for k, v in fields.items()
                if v == self.missing_marker
            ]
            values = [float(v) for k, v in fields.items() if v != self.missing_marker]
            sum_ = sum(values)
            mean = sum_ / len(values) if values else None
            yield {"id": row["id"], "sum": sum_, "mean": mean, "indexes": indexes}

    def load(self, seq, values_path: Path, missing_values_path: Path) -> None:
        if (
            values_path.suffix.lower() != ".csv"
            or missing_values_path.suffix.lower() != ".csv"
        ):
            raise ValueError("Only csv files are supported!")
        with (
            open(values_path, "w", encoding="utf-8") as values,
            open(missing_values_path, "w", encoding="utf-8") as missing_values,
        ):
            writer_values = csv.writer(values, delimiter=self.delimiter)
            writer_missing_values = csv.writer(missing_values, delimiter=self.delimiter)

            writer_values.writerow(["id", "sum", "mean"])
            writer_missing_values.writerow(["id", "missing_indexes"])

            for row in seq:
                writer_values.writerow([row["id"], row["sum"], row["mean"]])
                writer_missing_values.writerow([row["id"], row["indexes"]])


if __name__ == "__main__":
    DATA_DIR = Path("data")
    file_path = DATA_DIR / "example.csv"
    #     get_file("https://oleksandr-fedoruk.com/sggw/podyplomowe/file", file_path)
    #
    #     try:
    #         get_file("https://oleksandr-fedoruk.com/sggw/podyplomowe/403", file_path)
    #     except AccessDeniedError as e:
    #         print(e)
    #
    #     try:
    #         get_file("https://oleksandr-fedoruk.com/sggw/podyplomowe/404", file_path)
    #     except NotFoundError as e:
    #         print(e)

    etl = SimpleETL(input_path=file_path)
    etl.load(
        etl.transform(etl.extract()),
        DATA_DIR / "values.csv",
        DATA_DIR / "missing_values.csv",
    )
