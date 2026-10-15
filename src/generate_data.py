"""
Генерация синтетических данных мобильного приложения интернет-магазина «ShopFlow».

Данные вымышленные, но устроены как реальные продуктовые логи:
  * users.csv     — пользователи (дата регистрации, платформа, канал привлечения)
  * events.csv    — события в приложении (app_open, view_product, add_to_cart,
                    checkout, purchase) с суммой покупки
  * ab_groups.csv — распределение новых пользователей по группам A/B-теста
                    нового экрана оформления заказа

В данные специально заложены «жизненные» особенности, которые нужно найти
в анализе: дубликаты событий, пропуски в платформе, сбой 2025-08-03,
разный retention по каналам и платформам, эффект в A/B-тесте.

Запуск:  python src/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_USERS = 12_000
START = pd.Timestamp("2025-07-01")
END = pd.Timestamp("2025-09-30")             # последний день наблюдений
AB_START = pd.Timestamp("2025-08-15")        # период набора в тест
AB_END = pd.Timestamp("2025-09-14")
OUTAGE_DAY = pd.Timestamp("2025-08-03")      # сбой: событий почти нет

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

rng = np.random.default_rng(SEED)


def make_users() -> pd.DataFrame:
    days = (END - START).days + 1
    # регистраций становится чуть больше со временем (растущий продукт)
    weights = np.linspace(1.0, 1.6, days)
    reg_day = rng.choice(days, size=N_USERS, p=weights / weights.sum())
    reg_time = (START + pd.to_timedelta(reg_day, unit="D")
                + pd.to_timedelta(rng.integers(0, 86_400, N_USERS), unit="s"))

    users = pd.DataFrame({
        "user_id": np.arange(100_001, 100_001 + N_USERS),
        "registration_time": reg_time,
        "platform": rng.choice(["android", "ios", "web"], N_USERS, p=[0.48, 0.37, 0.15]),
        "source": rng.choice(["organic", "ads", "referral"], N_USERS, p=[0.45, 0.40, 0.15]),
        "city": rng.choice(["Москва", "Санкт-Петербург", "Казань", "Екатеринбург",
                            "Новосибирск", "Другой"], N_USERS,
                           p=[0.30, 0.15, 0.08, 0.08, 0.07, 0.32]),
    })
    return users.sort_values("registration_time").reset_index(drop=True)


def make_ab_groups(users: pd.DataFrame) -> pd.DataFrame:
    mask = users["registration_time"].between(AB_START, AB_END + pd.Timedelta(days=1),
                                              inclusive="left")
    ab = users.loc[mask, ["user_id"]].copy()
    ab["ab_group"] = rng.choice(["A", "B"], len(ab))
    return ab.reset_index(drop=True)


def daily_return_prob(row) -> float:
    """Базовая вероятность вернуться в приложение в конкретный день."""
    p = 0.11
    p *= {"organic": 1.15, "ads": 0.70, "referral": 1.30}[row.source]
    p *= {"android": 0.85, "ios": 1.10, "web": 0.95}[row.platform]
    return p


def make_events(users: pd.DataFrame, ab: pd.DataFrame) -> pd.DataFrame:
    group_of = dict(zip(ab["user_id"], ab["ab_group"]))
    rows = []

    for u in users.itertuples(index=False):
        group = group_of.get(u.user_id)
        base_p = daily_return_prob(u)
        user_value = rng.lognormal(0, 0.35)           # «щедрость» пользователя
        last_day = (END - u.registration_time.normalize()).days

        for d in range(0, last_day + 1):
            if d == 0:
                active = True
            else:
                # retention затухает со временем: быстро в первую неделю, потом медленнее
                p = base_p * (0.55 * np.exp(-d / 4) + 0.45 * np.exp(-d / 60))
                p = min(p * 2.2, 0.9)
                active = rng.random() < p
            if not active:
                continue

            day = u.registration_time.normalize() + pd.Timedelta(days=d)
            if day == OUTAGE_DAY and rng.random() < 0.85:
                continue                                # сбой логирования

            t = (u.registration_time if d == 0
                 else day + pd.Timedelta(seconds=int(rng.integers(7 * 3600, 23 * 3600))))
            rows.append((u.user_id, t, "app_open", np.nan))

            n_views = rng.poisson(3) + 1
            for _ in range(n_views):
                t += pd.Timedelta(seconds=int(rng.integers(10, 120)))
                rows.append((u.user_id, t, "view_product", np.nan))

            if rng.random() > 0.32:
                continue
            t += pd.Timedelta(seconds=int(rng.integers(20, 300)))
            rows.append((u.user_id, t, "add_to_cart", np.nan))

            if rng.random() > 0.55:
                continue
            t += pd.Timedelta(seconds=int(rng.integers(20, 300)))
            rows.append((u.user_id, t, "checkout", np.nan))

            # в группе B новый экран оформления: выше доля оплат после checkout
            p_buy = 0.58
            if group == "B":
                p_buy = 0.66
            if rng.random() > p_buy:
                continue
            t += pd.Timedelta(seconds=int(rng.integers(30, 400)))
            revenue = round(float(rng.gamma(2.2, 900) * user_value), 2)
            rows.append((u.user_id, t, "purchase", revenue))

    ev = pd.DataFrame(rows, columns=["user_id", "event_time", "event_type", "revenue"])
    ev = ev[ev["event_time"] < END + pd.Timedelta(days=1)]

    # «грязь», как в реальных логах: ~0.7% дублей событий
    dup = ev.sample(frac=0.007, random_state=SEED)
    ev = pd.concat([ev, dup]).sort_values(["event_time", "user_id"]).reset_index(drop=True)
    ev.insert(0, "event_id", np.arange(1, len(ev) + 1))
    ev["event_time"] = ev["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return ev


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    users = make_users()
    ab = make_ab_groups(users)
    events = make_events(users, ab)

    # пропуски в платформе у ~2% пользователей (старая версия трекинга)
    users.loc[users.sample(frac=0.02, random_state=SEED).index, "platform"] = np.nan
    users["registration_time"] = users["registration_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    users.to_csv(DATA_DIR / "users.csv", index=False)
    ab.to_csv(DATA_DIR / "ab_groups.csv", index=False)
    events.to_csv(DATA_DIR / "events.csv", index=False)
    print(f"users: {len(users):,}  ab_groups: {len(ab):,}  events: {len(events):,}")


if __name__ == "__main__":
    main()
