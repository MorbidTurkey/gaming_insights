import os
import pandas as pd
import dash
from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
import plotly.express as px

# === Configuration ===
MERGED_FILE = "merged_game_data.xlsx"

# External stylesheets
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
vizro_bootstrap = "https://cdn.jsdelivr.net/gh/mckinsey/vizro@main/vizro-core/src/vizro-bootstrap.min.css?v=2"

# Initialize app
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    dbc.icons.FONT_AWESOME,
    dbc_css
])

# Load merged data
if not os.path.exists(MERGED_FILE):
    raise FileNotFoundError(f"Merged data file '{MERGED_FILE}' not found.")

df_kpis_all = pd.read_excel(MERGED_FILE, sheet_name='All KPIs')
df_other_all = pd.read_excel(MERGED_FILE, sheet_name='Top Other Games')

# Prepare dropdown options
dropdown_options = [{'label': g, 'value': g} for g in df_kpis_all['base_game']]

# Theme control
theme_controls = html.Div([
    ThemeChangerAIO(aio_id="theme", custom_themes={'vizro': vizro_bootstrap})
], className="ms-auto d-flex align-items-center")

# Navbar: dropdown on left, theme toggle on right
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Select(
            id='game-dropdown',
            options=dropdown_options,
            value=dropdown_options[0]['value'] if dropdown_options else None,
            persistence=True,
            style={'width': '200px'}
        ),
        theme_controls
    ]),
    color="light", dark=False
)

# KPI parser: formats values to two decimals

def parse_kpi_row(df_kpi):
    mapping = [
        ('developer', 'Developer', str),
        ('publisher', 'Publisher', str),
        ('owners', 'Owners', lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else f"{v}"),
        ('average_forever', 'Total Avg Playtime', lambda v: f"{(v/60):.2f} hrs"),
        ('average_2weeks', '2 Week Avg Playtime', lambda v: f"{(v/60):.2f} hrs"),
        ('price', 'Price', lambda v: f"${(v/100):.2f}")
    ]
    cards = []
    for key, label, fn in mapping:
        if key in df_kpi:
            disp = fn(df_kpi[key])
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(disp, className='h5 text-center mb-1'),
                        html.Div(label, className='text-center')
                    ]),
                    style={'width': '8rem', 'height': '6rem'}
                )
            )
    return cards

# Header: title, subtitle, KPI row
def Header():
    return dbc.Container(
        dbc.Row([
            dbc.Col([
                html.H1(id='title', className='mt-4 mb-1'),
                html.H6(id='subtitle', className='mb-4 text-muted')
            ], width=4),
            dbc.Col(html.Div(id='kpi-cards', className='d-flex flex-row flex-wrap gap-3 align-items-start mt-2'), width=8)
        ]),
        fluid=True,
        className='pt-5 pb-2 px-4'
    )

# Main content: toggle + chart and table
def Content():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.RadioItems(
                    id='order-toggle',
                    options=[{'label':'Desc','value':'desc'},{'label':'Asc','value':'asc'}],
                    value='desc',
                    inline=True,
                    className='mb-2'
                ),
                dcc.Graph(id='bar-chart')
            ], width=9),
            dbc.Col([
                html.H5('All other games', className='text-center'),
                dash_table.DataTable(
                    id='table',
                    columns=[{'name':'Game','id':'Game'},{'name':'AvgHours','id':'AvgHours'}],
                    data=[],
                    sort_action='native',
                    filter_action='native',
                    page_size=10,
                    style_table={'overflowX':'auto'}
                )
            ], width=3)
        ], align='start', className='mt-4')
    ], fluid=True, className='px-4 pb-4')

# App layout
app.layout = html.Div([navbar, Header(), Content()])

# Callback to update dashboard
@app.callback(
    [
        Output('title', 'children'),
        Output('subtitle', 'children'),
        Output('kpi-cards', 'children'),
        Output('bar-chart', 'figure'),
        Output('table', 'data')
    ],
    [
        Input('game-dropdown', 'value'),
        Input(ThemeChangerAIO.ids.radio('theme'), 'value'),
        Input('order-toggle', 'value')
    ]
)
def update_dashboard(selected_game, theme_url, order):
    df_kpi = df_kpis_all[df_kpis_all['base_game']==selected_game].squeeze()
    df_other = df_other_all[df_other_all['base_game']==selected_game].squeeze()

    title = selected_game
    subtitle = f"Sample size: {int(df_kpi.get('sample_size', 0)):.2f}"
    cards = parse_kpi_row(df_kpi)

    vals = df_other.drop('base_game').apply(pd.to_numeric, errors='coerce').fillna(0)
    sorted_vals = vals.sort_values(ascending=(order=='asc')).head(10).reset_index()
    sorted_vals.columns = ['Game', 'AvgHours']
    # round AvgHours to two decimals
    sorted_vals['AvgHours'] = sorted_vals['AvgHours'].round(2)

    tpl = template_from_url(theme_url) if theme_url else 'bootstrap'
    fig = px.bar(
        sorted_vals,
        x='AvgHours', y='Game', orientation='h',
        title=f"Top 10 Other Games Owned with <b>{selected_game}</b>",
        template=tpl,
        color='Game'
    )
    fig.update_layout(
        title_x=0.5,
        xaxis_title='Avg Hours Per Owner',
        yaxis_title='Game',
        xaxis_tickformat='.2f',
        margin=dict(l=100, r=20, t=40, b=20),
        showlegend=False
    )

    table_data = sorted_vals.to_dict('records')
    return title, subtitle, cards, fig, table_data

if __name__=='__main__':
    app.run(debug=True)
