"""
Based on: https://stackoverflow.com/a/32492179/965332
"""

import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple

from main import _parse_messages, _calendar


def plot(data: Dict[dt.date, float]) -> None:
    fig, ax = plt.subplots(figsize=(6, 10))

    dates = list(data.keys())
    calendar_heatmap(ax, dates, list(data.values()))
    plt.show()


def main() -> None:
    data = _load_data()
    plot(data)


def _load_data() -> Dict[dt.date, float]:
    msgs = _parse_messages('*ekla*')
    d = _calendar(msgs)
    return {k: len(v) for k, v in d.items()}


def calendar_array(dates: List[dt.date], data: List[float]) -> Tuple[np.array, np.array, np.array]:
    i, j = zip(*[d.isocalendar()[1:] for d in dates])
    i = np.array(i) - min(i)
    j = np.array(j) - 1
    ni = max(i) + 1

    calendar = np.nan * np.zeros((ni, 7))
    calendar[i, j] = data
    return i, j, calendar


def calendar_heatmap(ax: plt.Axes, dates: List[dt.date], data: List[float]):
    i, j, calendar = calendar_array(dates, data)
    im = ax.imshow(calendar, interpolation='none', cmap='YlGn')
    label_days(ax, dates, i, j, calendar)
    label_months(ax, dates, i, j, calendar)
    ax.figure.colorbar(im)


def _date_nth(n: int) -> str:
    if n == 1:
        return "1st"
    elif n == 2:
        return "2nd"
    elif n == 3:
        return "3rd"
    else:
        return f"{n}th"


def label_days(ax: plt.Axes, dates: List[dt.date], i, j, calendar) -> None:
    ni, nj = calendar.shape
    day_of_month = np.nan * np.zeros((ni, 7))
    day_of_month[i, j] = [d.day for d in dates]

    for (i, j), day in np.ndenumerate(day_of_month):
        if np.isfinite(day):
            ax.text(j, i, f"{_date_nth(int(day))}\n{int(calendar[i, j])}", ha='center', va='center')

    ax.set(xticks=np.arange(7),
           xticklabels=['M', 'T', 'W', 'R', 'F', 'S', 'S'])
    ax.xaxis.tick_top()


def label_months(ax: plt.Axes, dates: List[dt.date], i, j, calendar) -> None:
    month_labels = np.array(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
                             'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    months = np.array([d.month for d in dates])
    uniq_months = sorted(set(months))
    print(j, type(j))
    yticks = [i[months == m].mean() for m in uniq_months]
    labels = [month_labels[m - 1] for m in uniq_months]
    ax.set(yticks=yticks)
    ax.set_yticklabels(labels, rotation=90)


if __name__ == "__main__":
    main()
