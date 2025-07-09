import dash
from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
import pandas as pd
from dash import register_page, callback
import shared_data

try:
    from dash import register_page
    register_page(__name__, path="/")
except ImportError:
    pass  # Not using Dash Pages anymore

df_kpis_all = shared_data.df_kpis_all
if hasattr(shared_data, 'df_other_all'):
    df_other_all = shared_data.df_other_all
else:
    df_other_all = pd.DataFrame()
TAGS_GENRES_DICT = shared_data.TAGS_GENRES_DICT

def parse_kpi_row(df_kpi):
    mapping = [
        ('developer', 'Developer', str),
        ('publisher', 'Publisher', str),
        ('owners', 'Owners', lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else f"{v}"),
        ('average_forever', 'Total Avg Playtime', lambda v: f"{(v/60):.2f} hrs" if v is not None else "N/A"),
        ('average_2weeks', '2 Week Avg Playtime', lambda v: f"{(v/60):.2f} hrs" if v is not None else "N/A"),
        ('price', 'Price', lambda v: f"${(v/100):.2f}" if v is not None else "N/A")
    ]
    cards = []
    for key, label, fn in mapping:
        if key in df_kpi:
            val = df_kpi[key]
            if isinstance(val, pd.Series):
                val = val.iloc[0] if not val.empty else None
            disp = fn(val)
            cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(
                            disp,
                            className='h5 text-center mb-1',
                            style={'whiteSpace': 'normal', 'wordBreak': 'break-word'}
                        ),
                        html.Div(
                            label,
                            className='text-center',
                            style={'whiteSpace': 'normal', 'wordBreak': 'break-word'}
                        )
                    ]),
                    style={'width': 'auto', 'minWidth': '8rem', 'height': '6rem', 'flex': '1 0 auto'}
                )
            )
    return cards

def genres_tags_cards(base_game):
    info = TAGS_GENRES_DICT.get(base_game, {})
    genres = info.get('genres', [])
    tags = info.get('tags', [])
    return [
        dbc.Card(
            dbc.CardBody([
                html.Div(", ".join(genres) if genres else "N/A", className='h6 text-center mb-1', style={'whiteSpace': 'normal', 'wordBreak': 'break-word'}),
                html.Div("Genres", className='text-center', style={'whiteSpace': 'normal', 'wordBreak': 'break-word'})
            ]),
            style={'width': 'auto', 'minWidth': '8rem', 'height': '6rem', 'flex': '1 0 auto'}
        ),
        dbc.Card(
            dbc.CardBody([
                html.Div(", ".join(tags) if tags else "N/A", className='h6 text-center mb-1', style={'whiteSpace': 'normal', 'wordBreak': 'break-word'}),
                html.Div("Tags", className='text-center', style={'whiteSpace': 'normal', 'wordBreak': 'break-word'})
            ]),
            style={'width': 'auto', 'minWidth': '8rem', 'height': '6rem', 'flex': '1 0 auto'}
        )
    ]

layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='game-dropdown',
                    options=[{'label': g, 'value': g} for g in df_kpis_all['base_game']] if not df_kpis_all.empty else [],
                    value=df_kpis_all['base_game'].iloc[0] if not df_kpis_all.empty else None,
                    persistence=True,
                    style={
                        'width': '350px',
                        'minWidth': '250px',
                        'backgroundColor': 'var(--bs-body-bg)',
                        'color': 'var(--bs-body-color)'
                    },
                    className='themed-dropdown'
                )
            ], width=4),
            dbc.Col([
                html.Div(
                    dbc.Button(
                        "See game reviews",
                        id="see-reviews-btn",
                        color="info",
                        outline=False,
                        className="mb-2 float-end",
                        style={"marginTop": "8px", "marginRight": "8px"},
                        n_clicks=0,
                        href="/reviews"
                    ),
                    className="d-flex justify-content-end align-items-start"
                )
            ], width=8)
        ]),
        dbc.Row([
            dbc.Col([
                html.H1(id='title', className='mt-4 mb-1'),
                html.H6(id='subtitle', className='mb-4 text-muted'),
                dbc.Button(
                    "Show/Hide Base Game Genres & Tags",
                    id="genres-tags-toggle",
                    color="secondary",
                    outline=True,
                    size="sm",
                    className="mb-2",
                    style={"whiteSpace": "normal", "wordBreak": "break-word", "maxWidth": "100%"}
                ),
                dbc.Collapse(
                    html.Div(id='genres-tags-cards', className='d-flex flex-row flex-wrap gap-3 align-items-start'),
                    id="genres-tags-collapse",
                    is_open=False
                )
            ], width=4),
            dbc.Col([
                html.Div(id='kpi-cards', className='d-flex flex-row flex-wrap gap-3 align-items-start mt-2')
            ], width=8)
        ]),
        # Section: Players also played
        html.Br(), html.Br(),
        dbc.Row([
            dbc.Col([
                html.H3(id='players-also-played-title', className='text-center mb-3'),
            ], width=12)
        ]),
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
                    page_size=15,
                    page_action='native',
                    style_table={
                        'overflowX': 'auto',
                        'border': 'none',
                    },
                    style_cell={
                        'minWidth': '120px',
                        'maxWidth': '300px',
                        'whiteSpace': 'normal',
                        'backgroundColor': 'var(--bs-body-bg)',
                        'color': 'var(--bs-body-color)'
                    },
                    style_header={
                        'fontWeight': 'bold',
                        'backgroundColor': 'var(--bs-tertiary-bg)',
                        'color': 'var(--bs-body-color)'
                    },
                    style_data={
                        'fontSize': '14px',
                        'backgroundColor': 'var(--bs-body-bg)',
                        'color': 'var(--bs-body-color)'
                    },
                    style_filter={
                        'backgroundColor': 'var(--bs-body-bg)',
                        'color': 'var(--bs-body-color)'
                    },
                    style_data_conditional=[
                        {
                            'if': {'state': 'selected'},
                            'backgroundColor': 'var(--bs-secondary-bg)',
                            'color': 'var(--bs-body-color)'
                        }
                    ]
                )
            ], width=3)
        ], align='start', className='mt-4'),
        # Section: Other Genres & Tags
        html.Br(), html.Br(),
        dbc.Row([
            dbc.Col([
                html.H3('Other Genres & Tags', className='text-center mb-3'),
            ], width=12)
        ]),
        # Combined toggle for hiding base game's genres & tags
        dbc.Row([
            dbc.Col([
                dcc.Checklist(
                    id='hide-same',
                    options=[],  # Will be set dynamically
                    value=[],
                    inline=True,
                    style={'marginBottom': '8px'}
                )
            ], width=12, style={'textAlign': 'center'})
        ]),
        dbc.Row([
            dbc.Col([
                html.H5('Genres of Other Games', className='text-center'),
                dcc.Graph(id='pie-genres', style={'height': '400px'})
            ], width=6),
            dbc.Col([
                html.H5('Tags of Other Games', className='text-center'),
                dcc.Graph(id='pie-tags', style={'height': '400px'})
            ], width=6)
        ], className='mt-4'),
    # Removed filter state stores and clear all filters button
    ], fluid=True, className='px-4 pb-4')
])


from dash.dependencies import State



# --- Inter-page game selection sync (single callback, now local only) ---
from dash import ctx
@callback(
    [Output('game-dropdown', 'value'), Output('selected-game-store', 'data')],
    [Input('selected-game-store', 'data'), Input('game-dropdown', 'value')],
    prevent_initial_call=False
)
def sync_game_dropdown_and_store(store_value, dropdown_value):
    trigger = ctx.triggered_id if hasattr(ctx, 'triggered_id') else None
    if trigger == 'selected-game-store':
        if store_value is not None:
            return store_value, dash.no_update
        elif not df_kpis_all.empty:
            return df_kpis_all['base_game'].iloc[0], dash.no_update
        else:
            return None, dash.no_update
    elif trigger == 'game-dropdown':
        return dash.no_update, dropdown_value
    else:
        if not df_kpis_all.empty:
            return df_kpis_all['base_game'].iloc[0], dash.no_update
        else:
            return None, dash.no_update

# Callbacks for Game View
@callback(
    Output("genres-tags-collapse", "is_open"),
    [Input("genres-tags-toggle", "n_clicks")],
    [dash.dependencies.State("genres-tags-collapse", "is_open")]
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    [
        Output('title', 'children'),
        Output('subtitle', 'children'),
        Output('kpi-cards', 'children'),
        Output('genres-tags-cards', 'children'),
        Output('players-also-played-title', 'children'),
        Output('bar-chart', 'figure'),
        Output('table', 'data'),
        Output('pie-genres', 'figure'),
        Output('pie-tags', 'figure')
    ],
    [
        Input('game-dropdown', 'value'),
        Input(ThemeChangerAIO.ids.radio('theme'), 'value'),
        Input('order-toggle', 'value'),
        Input('hide-same', 'value'),
        Input('pie-genres', 'clickData'),
        Input('bar-chart', 'clickData')
    ]
)
def update_dashboard(selected_game, theme_url, order, hide_same, genre_click, bar_click):
    selected_genre = None
    selected_bar_game = None
    # Title for the section above bar chart and table
    players_also_played_title = f"Players of {selected_game} also played:"
    df_kpi = df_kpis_all[df_kpis_all['base_game']==selected_game].squeeze()
    df_other = df_other_all[df_other_all['base_game']==selected_game].squeeze()

    title = selected_game
    # Defensive: handle sample_size as scalar, Series, or missing
    sample_size = df_kpi.get('sample_size', 0)
    if isinstance(sample_size, pd.Series):
        # If Series, take first value or 0
        sample_size = sample_size.iloc[0] if not sample_size.empty else 0
    try:
        sample_size_val = int(float(sample_size))
    except Exception:
        sample_size_val = 0
    # Choose Bootstrap text color class based on sample size
    if sample_size_val < 100:
        sample_color = 'text-danger'  # red
    elif sample_size_val < 500:
        sample_color = 'text-warning'  # orange/yellow
    else:
        sample_color = 'text-success'  # green
    subtitle = html.Span(f"Sample size of public profiles: {sample_size_val:.2f}", className=sample_color)
    cards = parse_kpi_row(df_kpi)
    genres_tags = genres_tags_cards(selected_game)

    vals = df_other.drop('base_game', errors='ignore').apply(pd.to_numeric, errors='coerce').fillna(0)
    # For bar chart: top 10
    all_other_games_df = vals.reset_index()
    all_other_games_df.columns = ['Game', 'AvgHours']
    all_other_games_df['AvgHours'] = all_other_games_df['AvgHours'].round(2)

    sorted_vals = all_other_games_df.sort_values('AvgHours', ascending=(order=='asc')).head(10)

    # Add genres column for hover
    def get_genres(game):
        info = TAGS_GENRES_DICT.get(game, {})
        genres = info.get('genres', [])
        return ", ".join(genres) if genres else "N/A"
    sorted_vals['Genres'] = sorted_vals['Game'].apply(get_genres)

    tpl = template_from_url(theme_url) if theme_url else 'bootstrap'
    # Use default plotly colors
    fig = px.bar(
        sorted_vals,
        x='AvgHours', y='Game', orientation='h',
        title=f"Top 10 Other Games Owned with <b>{selected_game}</b>",
        template=tpl,
        color='Game',
        custom_data=['Game', 'AvgHours', 'Genres']
    )
    fig.update_traces(
        hovertemplate="<b>Game name:</b> %{customdata[0]}<br>"
                      "<b>AvgHours played:</b> %{customdata[1]:.2f}<br>"
                      "<b>Genres:</b> %{customdata[2]}<extra></extra>"
    )
    fig.update_layout(
        title_x=0.5,
        xaxis_title=f'Avg Hours played Per {selected_game} Owner',
        yaxis_title='Game',
        xaxis_tickformat='.2f',
        margin=dict(l=100, r=20, t=40, b=20),
        showlegend=False
    )

    # For table: ALL other games, paginated, searchable
    table_data = all_other_games_df.sort_values('AvgHours', ascending=(order=='asc')).to_dict('records')

    # --- Pie chart data for genres/tags based on hours ---
    all_other_games = [g for g in df_other.index if g != 'base_game']
    if selected_bar_game:
        all_other_games = [selected_bar_game] if selected_bar_game in all_other_games else []
    genre_hours = {}
    tag_hours = {}
    for g in all_other_games:
        hours = pd.to_numeric(df_other.get(g, 0), errors='coerce')
        info = TAGS_GENRES_DICT.get(g, {})
        for genre in info.get('genres', []):
            genre_hours[genre] = genre_hours.get(genre, 0) + hours
        for tag in info.get('tags', []):
            tag_hours[tag] = tag_hours.get(tag, 0) + hours

    filtered_games = all_other_games
    if selected_genre:
        filtered_games = [g for g in all_other_games if selected_genre in TAGS_GENRES_DICT.get(g, {}).get('genres', [])]
        # Recompute tag_hours for filtered games
        tag_hours = {}
        for g in filtered_games:
            hours = pd.to_numeric(df_other.get(g, 0), errors='coerce')
            info = TAGS_GENRES_DICT.get(g, {})
            for tag in info.get('tags', []):
                tag_hours[tag] = tag_hours.get(tag, 0) + hours

    base_info = TAGS_GENRES_DICT.get(selected_game, {})
    base_genres = set(base_info.get('genres', []))
    base_tags = set(base_info.get('tags', []))

    # Hide genres/tags if toggled
    if 'hide' in (hide_same or []):
        genre_hours = {k: v for k, v in genre_hours.items() if k not in base_genres}
        tag_hours = {k: v for k, v in tag_hours.items() if k not in base_tags}

    # Only show top 15 for readability, round to 2 decimals
    genre_items = sorted(genre_hours.items(), key=lambda x: x[1], reverse=True)[:15]
    tag_items = sorted(tag_hours.items(), key=lambda x: x[1], reverse=True)[:15]
    # Filter out values less than 1% of the total
    genre_total = sum([c for _, c in genre_items]) or 1
    tag_total = sum([c for _, c in tag_items]) or 1
    genre_items = [(g, c) for g, c in genre_items if (c / genre_total) >= 0.01]
    tag_items = [(t, c) for t, c in tag_items if (c / tag_total) >= 0.01]
    genre_labels = [g for g, _ in genre_items]
    genre_values = [round(c, 2) for _, c in genre_items]
    tag_labels = [t for t, _ in tag_items]
    tag_values = [round(c, 2) for _, c in tag_items]
    pie_genres_fig = px.pie(
        names=genre_labels,
        values=genre_values,
        title="Genres Breakdown (All Other Games, by Hours)",
        template=tpl
    )
    pie_genres_fig.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))
    pie_genres_fig.update_traces(
        hovertemplate="<b>Genre:</b> %{label}<br>"
                      "<b>Total Hours played:</b> %{value}<extra></extra>",
        marker_line_width=1,
        marker_line_color='#888'
    )

    pie_tags_fig = px.pie(
        names=tag_labels,
        values=tag_values,
        title="Tags Breakdown (All Other Games, by Hours)",
        template=tpl
    )
    pie_tags_fig.update_layout(title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))
    pie_tags_fig.update_traces(
        hovertemplate="<b>Tag:</b> %{label}<br>"
                      "<b>Total Hours played:</b> %{value}<extra></extra>"
    )

    return title, subtitle, cards, genres_tags, players_also_played_title, fig, table_data, pie_genres_fig, pie_tags_fig

# Dynamically update the label of the hide-same toggle based on selected game
@callback(
    Output('hide-same', 'options'),
    [Input('game-dropdown', 'value')],
    prevent_initial_call=False
)
def update_hide_same_label(selected_game):
    if not selected_game:
        label = "Hide selected game genres & tags"
    else:
        label = f"Hide {selected_game} genres & tags"
    return [{'label': label, 'value': 'hide'}]


# Inject CSS for themed dropdown selected value and menu using dcc.Markdown
from dash import dcc
layout.children.insert(0, dcc.Markdown(
    '''
    <style>
    .themed-dropdown .Select-control,
    .themed-dropdown .Select__control,
    .themed-dropdown .Select-menu,
    .themed-dropdown .Select__menu,
    .themed-dropdown .Select-menu-outer,
    .themed-dropdown .Select__menu-list,
    .themed-dropdown .Select-value,
    .themed-dropdown .Select__single-value,
    .themed-dropdown .Select-value-label,
    .themed-dropdown .Select__option,
    .themed-dropdown .Select__option--is-focused,
    .themed-dropdown .Select__option--is-selected {
        background-color: var(--bs-body-bg, #212529) !important;
        color: var(--bs-body-color, #fff) !important;
    }
    </style>
    ''',
    dangerously_allow_html=True
))
