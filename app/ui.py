from __future__ import annotations

import base64
import math
from datetime import datetime

import flet as ft
import httpx


API_BASE_URL = "http://127.0.0.1:8000"
PRESETS = [
    ("shackleton-rim", "Shackleton rim"),
    ("malapert-massif", "Malapert Massif"),
    ("nobile-region", "Nobile region"),
    ("apollo-11", "Apollo 11"),
    ("apollo-17", "Apollo 17"),
]
BG = "#0d1117"
PANEL = "#151b23"
PANEL_ALT = "#1c2633"
MUTED = "#8b98a9"
GREEN = "#3ddc84"
YELLOW = "#f4c95d"
BLUE = "#4da3ff"


def _metric_card(label: str, value: str, accent: str = GREEN) -> ft.Card:
    return ft.Card(
        bgcolor=PANEL,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text(label.upper(), size=11, color=MUTED),
                    ft.Text(value, size=25, weight=ft.FontWeight.BOLD, color=accent),
                ],
                spacing=5,
            ),
            padding=16,
            width=175,
        ),
    )


def _fmt(value: float | None, suffix: str = "") -> str:
    return "—" if value is None else f"{value:.1f}{suffix}"


def _timeline(payload: dict) -> ft.Control:
    series = payload["timeseries"]
    mask = payload["horizon_mask_deg"]
    cells: list[ft.Control] = []
    for sun_az, sun_el, earth_az, earth_el in zip(
        series["sun_az"],
        series["sun_el"],
        series["earth_az"],
        series["earth_el"],
    ):
        sun_visible = sun_el > mask[round(sun_az) % 360]
        earth_visible = earth_el > mask[round(earth_az) % 360]
        color = "#24313f"
        if sun_visible and earth_visible:
            color = "#82d173"
        elif sun_visible:
            color = YELLOW
        elif earth_visible:
            color = BLUE
        cells.append(ft.Container(width=4, height=22, bgcolor=color, border_radius=2))
    return ft.Row(cells, spacing=1, scroll=ft.ScrollMode.AUTO)


def _polar_point(azimuth: float, elevation: float, radius: float = 210.0) -> tuple[float, float]:
    angle = math.radians(azimuth - 90)
    distance = radius * (1 - max(0.0, min(90.0, elevation)) / 90)
    return 260 + distance * math.cos(angle), 260 + distance * math.sin(angle)


def _sky_dome_svg(payload: dict, index: int) -> str:
    series = payload["timeseries"]
    mask = payload["horizon_mask_deg"]
    sun_az, sun_el = series["sun_az"][index], series["sun_el"][index]
    earth_az, earth_el = series["earth_az"][index], series["earth_el"][index]

    def path(points: list[tuple[float, float]]) -> str:
        return " ".join(
            f"{'M' if offset == 0 else 'L'} {x:.1f} {y:.1f}"
            for offset, (x, y) in enumerate(points)
        )

    terrain_points = [_polar_point(azimuth, mask[azimuth]) for azimuth in range(0, 360, 4)]
    sun_points = [
        _polar_point(azimuth, elevation)
        for azimuth, elevation in zip(series["sun_az"], series["sun_el"])
    ]
    earth_points = [
        _polar_point(azimuth, elevation)
        for azimuth, elevation in zip(series["earth_az"], series["earth_el"])
    ]
    sun_x, sun_y = _polar_point(sun_az, sun_el)
    earth_x, earth_y = _polar_point(earth_az, earth_el)
    sun_visible = sun_el > mask[round(sun_az) % 360]
    earth_visible = earth_el > mask[round(earth_az) % 360]
    sun_color = YELLOW if sun_visible else "#6c5e35"
    earth_color = BLUE if earth_visible else "#38516d"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="560" viewBox="0 0 520 560">
<rect width="520" height="560" rx="18" fill="{PANEL}"/>
<g font-family="Arial, sans-serif">
<circle cx="260" cy="260" r="210" fill="#111923" stroke="#718096" stroke-width="2"/>
<circle cx="260" cy="260" r="140" fill="none" stroke="#344252"/>
<circle cx="260" cy="260" r="70" fill="none" stroke="#344252"/>
<path d="{path(terrain_points)}" fill="none" stroke="#8793a3" stroke-width="3"/>
<path d="{path(sun_points)}" fill="none" stroke="{YELLOW}" stroke-opacity=".5" stroke-width="2"/>
<path d="{path(earth_points)}" fill="none" stroke="{BLUE}" stroke-opacity=".5" stroke-width="2"/>
<line x1="260" y1="42" x2="260" y2="478" stroke="#344252"/>
<line x1="42" y1="260" x2="478" y2="260" stroke="#344252"/>
<circle cx="{sun_x:.1f}" cy="{sun_y:.1f}" r="11" fill="{sun_color}" stroke="#fff" stroke-width="2"/>
<circle cx="{earth_x:.1f}" cy="{earth_y:.1f}" r="10" fill="{earth_color}" stroke="#fff" stroke-width="2"/>
<text x="260" y="27" text-anchor="middle" fill="#cbd5e1" font-size="14">N · 0°</text>
<text x="495" y="265" text-anchor="end" fill="#cbd5e1" font-size="14">E · 90°</text>
<text x="260" y="501" text-anchor="middle" fill="#cbd5e1" font-size="14">S · 180°</text>
<text x="25" y="265" fill="#cbd5e1" font-size="14">W · 270°</text>
<text x="260" y="535" text-anchor="middle" fill="#8b98a9" font-size="13">radius: zenith 90° → horizon 0°</text>
<circle cx="52" cy="555" r="6" fill="{YELLOW}"/><text x="65" y="560" fill="#cbd5e1" font-size="13">Sun</text>
<circle cx="130" cy="555" r="6" fill="{BLUE}"/><text x="143" y="560" fill="#cbd5e1" font-size="13">Earth</text>
<line x1="210" y1="555" x2="230" y2="555" stroke="#8793a3" stroke-width="3"/><text x="238" y="560" fill="#cbd5e1" font-size="13">terrain</text>
</g></svg>"""
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _sky_chart(payload: dict, index: int) -> ft.Control:
    return ft.Container(
        content=ft.Image(
            src=base64.b64decode(_sky_dome_svg(payload, index)),
            width=520,
            height=560,
        ),
        bgcolor=PANEL,
        padding=8,
        border_radius=12,
    )


def main(page: ft.Page) -> None:
    page.title = "Lunar Landing Site Navigator"
    page.bgcolor = BG
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.theme = ft.Theme(color_scheme_seed=BLUE)

    site = ft.Dropdown(
        label="Landing site",
        value="shackleton-rim",
        options=[ft.DropdownOption(key=key, text=label) for key, label in PRESETS],
        width=280,
    )
    compare_site = ft.Dropdown(
        label="Compare with",
        value="malapert-massif",
        options=[ft.DropdownOption(key=key, text=label) for key, label in PRESETS],
        width=280,
    )
    start = ft.TextField(
        label="Landing date / UTC",
        value="2026-01-01T00:00:00Z",
        width=280,
    )
    duration = ft.Slider(
        min=7,
        max=28,
        divisions=3,
        value=14,
        label="{value} days",
        active_color=BLUE,
        width=260,
    )
    duration_label = ft.Text("14 Earth days", color=MUTED)
    status = ft.Text("Ready. Choose a site and run an analysis.", color=MUTED)
    progress = ft.ProgressRing(visible=False, width=18, height=18)
    content = ft.Column(spacing=14)
    compare_content = ft.Column(spacing=14)
    analysis_payload: dict | None = None
    comparison_items: list[dict] = []

    def show_error(message: str) -> None:
        progress.visible = False
        status.value = message
        status.color = "#ff6b6b"
        page.update()

    def request_analysis(site_id: str, duration_days: int) -> dict:
        response = httpx.post(
            f"{API_BASE_URL}/api/v1/analyze-site",
            json={
                "site_id": site_id,
                "start_utc": start.value,
                "duration_days": duration_days,
                "step_minutes": 30,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def render_analysis(payload: dict) -> None:
        nonlocal analysis_payload
        analysis_payload = payload
        metrics = payload["metrics"]
        score = payload["score"]
        series_count = len(payload["timeseries"]["t"])
        time_slider = ft.Slider(
            min=0,
            max=max(0, series_count - 1),
            value=0,
            divisions=max(1, series_count - 1),
            label="Mission sample {value}",
            active_color=YELLOW,
        )
        time_label = ft.Text("T+0.0 h", color=YELLOW, size=16, weight=ft.FontWeight.BOLD)
        sky = ft.Container()
        state_label = ft.Text("", size=13, color=MUTED)

        def update_time(event: ft.ControlEvent) -> None:
            index = min(series_count - 1, max(0, round(float(event.control.value))))
            hours = index * 0.5
            time_label.value = f"T+{hours:.1f} h"
            sky.content = _sky_chart(payload, index)
            mask = payload["horizon_mask_deg"]
            sun_el = payload["timeseries"]["sun_el"][index]
            sun_az = payload["timeseries"]["sun_az"][index]
            earth_el = payload["timeseries"]["earth_el"][index]
            earth_az = payload["timeseries"]["earth_az"][index]
            state_label.value = (
                f"Sun {sun_az:.1f}° / {sun_el:.1f}° · "
                f"{'POWER VISIBLE' if sun_el > mask[round(sun_az) % 360] else 'POWER OFF'}   |   "
                f"Earth {earth_az:.1f}° / {earth_el:.1f}° · "
                f"{'COMM AVAILABLE' if earth_el > mask[round(earth_az) % 360] else 'COMM OUTAGE'}"
            )
            page.update()

        time_slider.on_change = update_time
        sky.content = _sky_chart(payload, 0)
        state_label.value = (
            f"Sun {payload['timeseries']['sun_az'][0]:.1f}° / "
            f"{payload['timeseries']['sun_el'][0]:.1f}°   |   "
            f"Earth {payload['timeseries']['earth_az'][0]:.1f}° / "
            f"{payload['timeseries']['earth_el'][0]:.1f}°"
        )
        warnings = [
            ft.Container(
                content=ft.Text(f"• {warning}", size=12, color="#d7dee8"),
                bgcolor=PANEL_ALT,
                padding=10,
                border_radius=7,
            )
            for warning in payload["warnings"]
        ]
        content.controls = [
            ft.Row(
                [
                    ft.Text(payload["site"]["name"], size=25, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Text(
                        f"{payload['data_source'].upper()} · {payload['data_quality']}",
                        color=GREEN if payload["data_source"] != "fallback" else YELLOW,
                    ),
                ]
            ),
            ft.Row(
                [
                    _metric_card("Decision score", _fmt(score["total"], "/100"), YELLOW),
                    _metric_card("Power window", _fmt(metrics["illumination_pct"], "%"), GREEN),
                    _metric_card("Comm window", _fmt(metrics["comm_pct"], "%"), BLUE),
                    _metric_card("Time to sunset", _fmt(metrics["time_to_sunset_hours"], " h"), YELLOW),
                ],
                wrap=True,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("SKY ABOVE THE HORIZON", size=12, color=MUTED),
                        sky,
                        state_label,
                        ft.Row([time_label, ft.Container(expand=True), ft.Text("Drag across mission hours", color=MUTED)]),
                        time_slider,
                    ],
                    spacing=10,
                ),
                bgcolor=PANEL_ALT,
                padding=16,
                border_radius=12,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("POWER & COMMUNICATION TIMELINE", size=12, color=MUTED),
                        _timeline(payload),
                        ft.Row(
                            [
                                ft.Text("green: both", size=11, color=GREEN),
                                ft.Text("yellow: power only", size=11, color=YELLOW),
                                ft.Text("blue: comm only", size=11, color=BLUE),
                            ],
                            spacing=18,
                        ),
                    ],
                    spacing=10,
                ),
                bgcolor=PANEL_ALT,
                padding=16,
                border_radius=12,
            ),
            ft.Text("DATA NOTES", size=12, color=MUTED),
            ft.Column(warnings, spacing=6),
        ]
        page.update()

    def analyze(_: ft.ControlEvent) -> None:
        try:
            datetime.fromisoformat(start.value.replace("Z", "+00:00"))
            duration_days = round(float(duration.value))
        except ValueError as error:
            show_error(f"Invalid request: {error}")
            return
        progress.visible = True
        status.value = "Calculating Sun, Earth and terrain visibility..."
        status.color = MUTED
        page.update()
        try:
            payload = request_analysis(site.value, duration_days)
            render_analysis(payload)
        except (httpx.HTTPError, ValueError) as error:
            show_error(f"Analysis failed: {error}")
            return
        progress.visible = False
        status.value = f"Analysis complete · {payload['site']['name']}"
        status.color = GREEN
        page.update()

    def update_duration(event: ft.ControlEvent) -> None:
        duration_label.value = f"{round(float(event.control.value))} Earth days"
        page.update()

    duration.on_change = update_duration

    def add_comparison(_: ft.ControlEvent) -> None:
        item = {
            "site_id": site.value,
            "label": next(label for key, label in PRESETS if key == site.value),
            "duration_days": round(float(duration.value)),
        }
        if item not in comparison_items:
            comparison_items.append(item)
        status.value = f"Added {item['label']} to comparison."
        status.color = BLUE
        page.update()

    def compare(_: ft.ControlEvent) -> None:
        try:
            duration_days = round(float(duration.value))
            first = request_analysis(site.value, duration_days)
            second = request_analysis(compare_site.value, duration_days)
        except (httpx.HTTPError, ValueError) as error:
            show_error(f"Comparison failed: {error}")
            return
        cards = []
        for payload in (first, second):
            cards.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(payload["site"]["name"], size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Score {_fmt(payload['score']['total'], '/100')}", size=25, color=YELLOW),
                            ft.Text(f"Power {_fmt(payload['metrics']['illumination_pct'], '%')}", color=GREEN),
                            ft.Text(f"Comm {_fmt(payload['metrics']['comm_pct'], '%')}", color=BLUE),
                            ft.Text(f"Dark interval {_fmt(payload['metrics']['longest_dark_hours'], ' h')}"),
                            ft.Text(f"Source {payload['data_source']} · terrain {payload['terrain_source']}", color=MUTED),
                        ],
                        spacing=8,
                    ),
                    bgcolor=PANEL,
                    padding=18,
                    border_radius=12,
                    expand=True,
                )
            )
        compare_content.controls = [
            ft.Text("DELAY / SITE COMPARISON", size=14, color=MUTED),
            ft.Row(cards, spacing=14),
            ft.Text(
                "This comparison changes the landing site while keeping the same UTC start and mission duration.",
                color=MUTED,
            ),
        ]
        page.update()

    mission_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("MISSION SELECTION", size=12, color=MUTED),
                ft.Text("Choose a landing scenario", size=21, weight=ft.FontWeight.BOLD),
                site,
                start,
                ft.Text("Mission duration", color=MUTED),
                duration,
                duration_label,
                ft.Button("Analyze mission", on_click=analyze),
                ft.OutlinedButton("Add to comparison", on_click=add_comparison),
                ft.Divider(),
                ft.Text("Current model", size=12, color=MUTED),
                ft.Text("Horizons + 360° terrain mask", color="#d7dee8"),
                ft.Text("NASA → cache → deterministic fallback", size=12, color=MUTED),
            ],
            spacing=12,
        ),
        bgcolor=PANEL_ALT,
        padding=18,
        border_radius=12,
        width=310,
    )

    overview = ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("LUNAR LANDING SITE NAVIGATOR", size=27, weight=ft.FontWeight.BOLD),
                            ft.Text("Rapid decision support for light, comms and terrain.", color=MUTED),
                        ],
                        spacing=4,
                    ),
                    ft.Container(expand=True),
                    progress,
                    status,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row([mission_panel, ft.Container(content=content, expand=True)], vertical_alignment=ft.CrossAxisAlignment.START),
        ],
        spacing=18,
    )
    compare_view = ft.Column(
        [
            ft.Text("COMPARE TAB", size=12, color=MUTED),
            ft.Row([compare_site, ft.Button("Run comparison", on_click=compare)]),
            compare_content,
        ],
        spacing=16,
    )
    view = ft.Column([overview], expand=True)

    def show_overview(_: ft.ControlEvent) -> None:
        view.controls = [overview]
        page.update()

    def show_compare(_: ft.ControlEvent) -> None:
        view.controls = [compare_view]
        page.update()

    navigation = ft.Row(
        [
            ft.Button("Mission dashboard", on_click=show_overview),
            ft.OutlinedButton("Compare", on_click=show_compare),
        ],
        spacing=8,
    )
    page.add(ft.Column([navigation, view], expand=True, spacing=14))


if __name__ == "__main__":
    ft.run(main)
