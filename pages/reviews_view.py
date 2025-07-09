import dash
from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from dash import register_page, callback
import shared_data
import os
from datetime import datetime
from shared_data import TAGS_GENRES_DICT
from dash import callback_context

register_page(__name__, path="/reviews")

# Load review data for all games (CSV files in reviews_data/)
REVIEWS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reviews_data')

# Map game name to appid using shared_data (assumes df_kpis_all has 'base_game' and 'appid')
df_kpis_all = shared_data.df_kpis_all
GAME_NAME_TO_APPID = dict(zip(df_kpis_all['base_game'], df_kpis_all['appid']))

# Preload all reviews into a dict: {game: DataFrame} from Parquet files
REVIEWS = {}
for game, appid in GAME_NAME_TO_APPID.items():
    pq_path = os.path.join(REVIEWS_DIR, f"reviews_{appid}.parquet")
    if os.path.exists(pq_path):
        df = pd.read_parquet(pq_path)
        # Convert timestamp to datetime if needed
        if 'timestamp' in df:
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        elif 'date' not in df:
            df['date'] = pd.NaT
        REVIEWS[game] = df
    else:
        REVIEWS[game] = pd.DataFrame()

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

import glob

layout = html.Div([
    # Inject CSS for themed dropdown selected value using dcc.Markdown
    dcc.Markdown(
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
    ),
    dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id='review-game-dropdown',
                    options=[{'label': g, 'value': g} for g in df_kpis_all['base_game']],
                    value=None,  # Will be set by callback from store
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
                        "Back to game view",
                        id="back-to-game-btn",
                        color="info",
                        outline=False,
                        className="mb-2 float-end",
                        style={"marginTop": "8px", "marginRight": "8px"},
                        n_clicks=0,
                        href="/"
                    ),
                    className="d-flex justify-content-end align-items-start"
                )
            ], width=8)
        ]),
        dbc.Row([
            dbc.Col([
                html.H1(id='review-title', className='mt-4 mb-1'),
                html.H6(id='review-subtitle', className='mb-4 text-muted'),
            ], width=4),
            dbc.Col([
                html.Div(id='review-kpi-cards', className='d-flex flex-row flex-wrap gap-3 align-items-start mt-2')
            ], width=8)
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Checklist(
                    id='filter-public-profiles',
                    options=[{'label': 'Show only reviews from sampled public profiles', 'value': 'filter'}],
                    value=[],
                    inline=True,
                    style={'marginTop': '10px'}
                ),
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
                    html.Div(id='review-genres-tags-cards', className='d-flex flex-row flex-wrap gap-3 align-items-start'),
                    id="review-genres-tags-collapse",
                    is_open=False
                )
            ], width=4),
            dbc.Col([], width=8)
        ]),
        html.Br(), html.Br(),
        dbc.Row([
            dbc.Col([
                html.H4('Review Sentiment Over Time', className='text-center mb-3'),
                dcc.Graph(id='sentiment-over-time')
            ], width=12)
        ]),
        html.Br(), html.Br(),
        dbc.Row([
            dbc.Col([
                html.H4('Recent Reviews', className='text-center mb-3'),
                dash_table.DataTable(
                    id='reviews-table',
                    columns=[
                        {'name': 'Date', 'id': 'date'},
                        {'name': 'Recommended', 'id': 'voted_up'},
                        {'name': 'Review Text', 'id': 'review'},
                        {'name': 'Playtime (hrs)', 'id': 'playtime_forever'},
                        {'name': 'Language', 'id': 'language'}
                    ],
                    data=[],
                    sort_action='native',
                    filter_action='native',
                    page_size=20,
                    page_action='native',
                    style_table={
                        'overflowX': 'auto',
                        'border': 'none',
                    },
                    style_cell={
                        'minWidth': '120px',
                        'maxWidth': '600px',
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
                ),
                html.Div(id='no-matching-msg')
            ], width=12)
        ])
    ], fluid=True, className='px-4 pb-4')
])


from dash_bootstrap_templates import ThemeChangerAIO, template_from_url



# --- Inter-page game selection sync (read-only from store) ---
@callback(
    Output('review-game-dropdown', 'value'),
    Input('selected-game-store', 'data'),
    prevent_initial_call=False
)
def sync_review_dropdown_with_store(store_value):
    if store_value is not None:
        return store_value
    elif not df_kpis_all.empty:
        return df_kpis_all['base_game'].iloc[0]
    else:
        return None


# Restore genres/tags popout toggle as a separate callback (like in game_view.py)
@callback(
    Output("review-genres-tags-collapse", "is_open"),
    [Input("genres-tags-toggle", "n_clicks")],
    [dash.dependencies.State("review-genres-tags-collapse", "is_open")],
    prevent_initial_call=True,
    name="toggle_review_genres_tags_collapse_reviews"
)
def toggle_review_genres_tags_collapse_reviews(n, is_open):
    if n:
        return not is_open
    return is_open

@callback(
    [
        Output('review-title', 'children'),
        Output('review-subtitle', 'children'),
        Output('review-kpi-cards', 'children'),
        Output('review-genres-tags-cards', 'children'),
        Output('sentiment-over-time', 'figure'),
        Output('reviews-table', 'data'),
        Output('no-matching-msg', 'children')
    ],
    [
        Input('review-game-dropdown', 'value'),
        Input(ThemeChangerAIO.ids.radio('theme'), 'value'),
        Input('filter-public-profiles', 'value')
    ],
    name="update_review_dashboard_reviews"
)
def update_review_dashboard_reviews(selected_game, theme_url, filter_opts):
    ctx = callback_context
    # Genres & Tags popout (same as game_view)
    def genres_tags_cards_reviews(base_game):
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
    genres_tags = genres_tags_cards_reviews(selected_game)
    df_kpi = df_kpis_all[df_kpis_all['base_game'] == selected_game].squeeze()
    title = selected_game
    sample_size = df_kpi.get('sample_size', 0)
    try:
        sample_size_val = int(float(sample_size))
    except Exception:
        sample_size_val = 0
    if sample_size_val < 100:
        sample_color = 'text-danger'
    elif sample_size_val < 500:
        sample_color = 'text-warning'
    else:
        sample_color = 'text-success'
    subtitle = html.Span(f"Sample size of public profiles: {sample_size_val:.2f}", className=sample_color)
    cards = parse_kpi_row(df_kpi)
    df_reviews = REVIEWS.get(selected_game, pd.DataFrame())
    no_matching_msg = ""
    if 'filter' in (filter_opts or []):
        # Try to load steamids from the per-game analysis file (parquet or xlsx)
        safe_name = selected_game.replace(' ', '_').replace('/', '_')
        analysis_parquet = os.path.join(os.path.dirname(__file__), '..', 'game_data', f'{safe_name}_analysis.parquet')
        steamids = set()
        if os.path.exists(analysis_parquet):
            try:
                df_sample = pd.read_parquet(analysis_parquet)
                if 'steamid' in df_sample.columns:
                    steamids = set(df_sample['steamid'].astype(str))
            except Exception:
                pass
        if steamids:
            df_reviews = df_reviews[df_reviews['steamid'].astype(str).isin(steamids)]
            if df_reviews.empty:
                no_matching_msg = dbc.Alert("No reviews from sampled public profiles found for this game.", color="warning", className="mt-2")
        else:
            no_matching_msg = dbc.Alert("No sampled public profile steamids found for this game.", color="warning", className="mt-2")
    # Theme/template logic (match game_view.py)
    template = template_from_url(theme_url) if theme_url else 'bootstrap'
    # Sentiment over time
    if not df_reviews.empty:
        df_reviews['date'] = pd.to_datetime(df_reviews['date'], errors='coerce')
        df_reviews = df_reviews.sort_values('date')
        df_reviews['voted_up'] = df_reviews['voted_up'].astype(bool)
        df_reviews['date_only'] = df_reviews['date'].dt.date
        sentiment_daily = df_reviews.groupby(['date_only', 'voted_up']).size().unstack(fill_value=0)
        sentiment_daily = sentiment_daily.rename(columns={True: 'Recommended', False: 'Not Recommended'})
        fig = px.line(
            sentiment_daily,
            x=sentiment_daily.index,
            y=['Recommended', 'Not Recommended'],
            labels={'value': 'Review Count', 'date_only': 'Date'},
            color_discrete_map={
                'Recommended': '#198754',  # Bootstrap success
                'Not Recommended': '#dc3545'  # Bootstrap danger
            },
            template=template
        )
        fig.update_layout(
            title='',
            xaxis_title='Date',
            yaxis_title='Review Count',
            legend_title='Sentiment',
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
    else:
        fig = px.line(title='No review data available', template=template)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
    if not df_reviews.empty:
        # Deduplicate reviews by recommendationid if present, else by steamid+date+review
        if 'recommendationid' in df_reviews.columns:
            df_reviews = df_reviews.drop_duplicates(subset=['recommendationid'])
        else:
            df_reviews = df_reviews.drop_duplicates(subset=[c for c in ['steamid', 'date', 'review'] if c in df_reviews.columns])
        table_data = df_reviews[['date', 'voted_up', 'review', 'playtime_forever', 'language']].copy()
        # Explicitly cast columns to object dtype before assigning string values to avoid FutureWarning
        table_data = table_data.astype({'voted_up': object, 'date': object, 'playtime_forever': object})
        table_data['voted_up'] = table_data['voted_up'].map({True: 'Yes', False: 'No'}).astype(str)
        table_data['date'] = table_data['date'].astype(str)
        table_data['playtime_forever'] = (table_data['playtime_forever'].astype(float) / 60).round(2).astype(str)
        table_data = table_data.sort_values('date', ascending=False).to_dict('records')
    else:
        table_data = []
    return title, subtitle, cards, genres_tags, fig, table_data, no_matching_msg

