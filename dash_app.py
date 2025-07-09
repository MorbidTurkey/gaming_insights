import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeChangerAIO
import plotly.express as px
import shared_data

# External stylesheets
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    dbc.icons.FONT_AWESOME,
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
]

# Enable Dash Pages
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    use_pages=True,
    suppress_callback_exceptions=True
)

# App layout with Dash Pages navigation and global theme changer
app.layout = html.Div([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dcc.Link("Game View", href="/", className="nav-link")),
            html.Div(ThemeChangerAIO(aio_id="theme"), className="ms-auto d-flex align-items-center px-2")
        ],
        brand="Steam Game Analytics",
        color="primary",
        dark=True,
        className="mb-4"
    ),
    dcc.Store(id="theme-store"),
    dcc.Store(id="selected-game-store", storage_type="session"),
    dash.page_container
])

print("Registered callbacks:")
for k, v in app.callback_map.items():
    print(f"{k}: {v['outputs']}")

if __name__ == '__main__':
    app.run(debug=True)
