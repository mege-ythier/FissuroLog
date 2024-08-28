import base64

from dash import html, dcc
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json

from flask_login import current_user
from sqlalchemy import text

from app_factory.utils.fig import create_map, create_time_series_fig

with open("./data_ratp/traces-du-reseau-de-transport-ferre-ratp.geojson", "r") as lines:
    ratp_dict = json.load(lines)

all_lines = ["all"]
for feature in ratp_dict['features']:
    route = feature['properties']['res_com']
    if len(route.split(" ")) == 2:
        line = route.split(" ")[1]
    else:
        line = route
    all_lines.append(line)


def generate_options_card():
    return html.Div(
        id='options-card',
        children=[

            html.Div(className='options_card_children', children=[

                html.H2("période"),
                dcc.DatePickerRange(
                    display_format='D M Y',
                    id="date-picker-select",
                    start_date=datetime.today().date() - relativedelta(years=30),
                    end_date=datetime.today().date(),
                    min_date_allowed=datetime(2000, 1, 1),
                    max_date_allowed=datetime.today().date(),
                    initial_visible_month=datetime.today().date() - relativedelta(years=2),
                )]),
            html.Div(className='options_card_children', children=[
                html.H2("fréquence"),
                dcc.RadioItems(
                    ['basse', 'brute'],
                    'brute',
                    id='aggregate-choice',
                    labelStyle={'display': 'inline-block'}
                )]),
            html.Button(id='button-update-fig', hidden=True, title='charger les mesures'),
        ]
    )


left_column = html.Div(id='left_colum_form',
    children=[
        html.H5("Réseau"),
        dcc.Dropdown(
            options=pd.Series(["RER", "METRO", "TRAM"]),
            id='dropdown-net',
            value=[],
            multi=True,
            style={'minWidth': '100px'}
        ),

        html.H5("type de capteur"),
        dcc.Textarea(
            id='textarea-model',
            disabled=True,
            value='',
            rows=1
        ),
        html.H5("Date de la pose *"),
        dcc.Textarea(
            id='textarea-date-pose',
            value='01/01/2000',
            rows=1
        ),
        html.H5("Ouverture à la pose"),
        dcc.Textarea(
            id='textarea-delta',
            value='',
            rows=1
        ),

        html.H5("Latitude *"),
        dcc.Textarea(
            id='textarea-lat',
            value='48.86461089629031',
            rows=1
        ),
        html.H5("Date de la collecte"),
        dcc.Textarea(
            id='textarea-date-collecte',
            value='',
            title='Ici tu renseignes la date de la dernière collecte des mesures',
            rows=1),
        html.H5("localisation dans le réseau"),
        dcc.Textarea(
            id='textarea-lieu',
            value='',
            title='Ici tu expliques comment accéder au capteur dans le reseau',
            rows=6),

    ])

right_column = html.Div(id='right_colum_form', children=[

    html.H5("ligne"),
    dcc.Dropdown(
        options=all_lines,
        value=[],
        id='dropdown-line',
        multi=True,
        style={'minWidth': '100px'}
    ),
    html.H5("numero du capteur"),
    dcc.Textarea(
        id='textarea-num',
        value='',
        rows=1
    ),
    html.H5("Date de la dépose"),
    dcc.Textarea(
        id='textarea-date-depose',
        value='',
        rows=1
    ),
    html.H5("localisation dans l'ouvrage *"),
    dcc.Textarea(
        id='textarea-zone',
        value='test',
        maxLength=20,
        title='exemple : voute, piedroit .....',
        rows=1
    ),
    html.H5("Longitude *"),
    dcc.Textarea(
        id='textarea-long',
        value='2.3300408349807364',
        rows=1
    ),

    html.H5("pk"),
    dcc.Textarea(
        id='textarea-pk',
        value='',
        rows=1,
    ),

    html.H5("commentaires"),
    dcc.Textarea(
        id='textarea-divers',
        value='',
        rows=6,
    ),
    dcc.Store(id="store-sensors-info-to-ingest", data={})
])


def generate_form_card():
    return html.Div(id='form-card',
                    # hidden=False,
                    children=[left_column, right_column])


def generate_upload_card():
    return html.Div(id="upload-file-card",
                    children=[

                        html.Div(id='upload-file-inner-card'),
                        dcc.Store(id='store-data-uploaded'),
                    ])


def generate_button_card():
    return html.Div(id='button-card',
                    children=[

                        html.Button(id='button-ingest', hidden=True,
                                    title='intégrer les mesures dans la database'),
                        html.Button(title='Supprimer le capteur', id='button-delete-table', hidden=True),
                        html.Button(title='modifier les informations du capteur',
                                    id='button-update-sensors-info', hidden=True),
                    ])


def generate_owner_card():
    return html.Div(id='owner-card', children=[
        html.Div(id='title-form-card', children=[
            html.Div(className='options_card_children', children=[
                html.H2("capteur"),
                dcc.Textarea(
                    id='dropdown-table',
                    value='',
                    style={'maxWidth': '50px'},
                    disabled=True,
                    draggable=False
                ), ]),
            dcc.Upload(
                id='upload-file-dcc',
                children="Selectionner des mesures",
                multiple=False
            ),
        ]),
        generate_form_card(),
        generate_button_card(),
        generate_upload_card(),

    ])


def generate_message_card():
    return html.Div(
        id="message-card",
        children=[
            html.H3(id='fig-message',
                    children="Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant 👇."),
            html.H3(id='ingest-message'),
            html.H3(id="image-message"),

        ])


def generate_select_card():
    return html.Div(
        id='select-card',
        children=[
            generate_options_card(),
            dcc.Graph(id='map',
                      config={'displaylogo': False, 'doubleClickDelay': 1000},
                      figure=create_map([], -1),
                      selectedData=None,
                      clickData=None

                      )
        ])


def generate_header():
    return html.Div(
        id='header-card',
        children=[html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
                  html.H1(id='welcome-info'),
                  html.A('menu', href='/'),
                  dcc.Location(id='url', refresh=False)])


def generate_image_card():
    return html.Div(id='image-card', hidden=True,
                    children=[dcc.Upload(id='upload-image1-dcc', multiple=False),
                              dcc.Upload(id='upload-image2-dcc', multiple=False),
                              dcc.Upload(id='upload-image3-dcc', multiple=False)])


def query_time_series_and_create_fig_card(db, sensor_id, start_date, end_date, aggregate, delta):
    start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
    end_date_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()
    query = ""

    if aggregate == "brute":
        query = text(f"""
        SELECT *
        FROM F{sensor_id}
        WHERE  unix > {start_date_timestamp} and unix < {end_date_timestamp}
        """)
        df = pd.read_sql(query, con=db.engine)
        df['Date'] = pd.to_datetime(df['unix'], unit='s')
        df.drop('unix', axis=1)

    else:
        if db.engine.name == 'sqlite':
            query = text(f"""
                SELECT  strftime('%Y-%m-%d %H:00:00', datetime(unix,'unixepoch')) AS Date, mm, celsius
                FROM F{sensor_id}
                WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                GROUP BY Date
                ORDER BY Date
            """)
        if db.engine.name == 'mysql':
            query = text(
                f"""
                SELECT DATE_FORMAT(FROM_UNIXTIME(unix), '%Y-%m-%d %H:00:00') AS Date, AVG(mm) AS mm, AVG(celsius) AS celsius
                FROM F{sensor_id}
                WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                GROUP BY Date
                ORDER BY Date
            """)

        df = pd.read_sql(query, con=db.engine)

    df = df.set_index('Date')
    size_on_memory = df.memory_usage(index=True, deep=False).sum()

    fig_message = "Données trop volumineuses pour être affichées 😢.  Modifies les options 🖊️."
    children = []

    if size_on_memory <= 200000:
        fig = create_time_series_fig(df, sensor_id, delta)
        children = [dcc.Graph(id='time-series', figure=fig, config={'displaylogo': False})]

        fig_message = [f"Le capteur F{sensor_id} est sélectionné 😎. Ses mesures sont affichées sur le graphe 👇."]

        if current_user.role == "owner":
            fig_message = fig_message + [ "Tu peux ajouter de nouvelles mesures à ce capteur, le supprimer, "
                                          "ou modifier ces caractéristiques 👈."]

    return children, fig_message


def query_images_and_create_image_card(db, sensor_id, card_id, role):
    try:
        query = f"""
                    SELECT data
                    FROM sensors_image_tb
                    WHERE sensor_id ='{sensor_id}' AND card_id={card_id}
                    ORDER BY id DESC
                    LIMIT 1
                    """
        image_from_database = db.session.execute(text(query)).scalar()
        image_encoded = base64.b64encode(image_from_database).decode('utf-8')

    except:
        if role == 'owner':
            return html.H4("Click pour ajouter une image")

    else:
        return html.Img(src=f"data:image/png;base64,{image_encoded}")
