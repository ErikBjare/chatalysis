"""
Based on: https://stackoverflow.com/a/32492179/965332
"""

import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple

import click

from .main import _load_all_messages
from .util import _calendar


@click.command()
@click.argument("glob")
def main(glob: str) -> None:
    data = _load_data(glob)
    if not data:
        raise Exception("No conversations matched glob")
    plot(data)


def plot(data: Dict[dt.date, float]) -> None:
    fig, ax = plt.subplots(figsize=(6, 10))

    dates = list(data.keys())
    _calendar_heatmap(ax, dates, list(data.values()))
    plt.show()


def _load_data(glob: str) -> Dict[dt.date, float]:
    msgs = _load_all_messages(glob)
    d = _calendar(msgs)
    # FIXME: the `k.year == 2018` thing is just set because the plotting doesn't
    #        support crossing year-boundaries without weirdness.
    return {k: len(v) for k, v in d.items() if k.year == 2020}


def _calendar_array(
    dates: List[dt.date], data: List[float]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    yl, wl, dl = zip(*[d.isocalendar() for d in dates])
    w: np.ndarray = np.array(wl) - min(wl)
    d: np.ndarray = np.array(dl) - 1
    wi = max(w) + 1

    # y = np.array(yl) - min(yl)
    # wi = max(y) * 53 + max(w) + 1

    calendar: np.ndarray = np.nan * np.zeros((wi, 7))
    calendar[w, d] = data
    return w, d, calendar


def _calendar_heatmap(ax: plt.Axes, dates: List[dt.date], data: List[float]):
    i, j, calendar = _calendar_array(dates, data)
    im = ax.imshow(calendar.T, interpolation="none", cmap="YlGn")
    _label_days(ax, dates, i, j, calendar)
    _label_months(ax, dates, i, j, calendar)
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


def _label_days(ax: plt.Axes, dates: List[dt.date], i, j, calendar) -> None:
    ni, nj = calendar.shape
    day_of_month = np.nan * np.zeros((ni, 7))
    day_of_month[i, j] = [d.day for d in dates]

    for (i, j), day in np.ndenumerate(day_of_month):
        if np.isfinite(day):
            ax.text(
                i,
                j,
                f"{_date_nth(int(day))}\n{int(calendar[i, j])}",
                ha="center",
                va="center",
            )

    ax.set(yticks=np.arange(7), yticklabels=["M", "T", "W", "R", "F", "S", "S"])
    ax.yaxis.tick_left()


def _label_months(ax: plt.Axes, dates: List[dt.date], i, j, calendar) -> None:
    month_labels = np.array(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )
    months = np.array([d.year * 100 + d.month for d in dates])
    uniq_months = sorted(set(months))
    ticks = [i[months == m].mean() for m in uniq_months]
    labels = [
        (f"{m // 100}\n" if (m % 100) == 1 else "") + month_labels[(m % 100) - 1]
        for m in uniq_months
    ]
    ax.set(xticks=ticks)
    ax.set_xticklabels(labels, rotation=90)


if __name__ == "__main__":
    main()
