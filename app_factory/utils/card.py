from dash import html, dcc
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json
from app_factory.utils.fig import create_map

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


options_card = html.Div(
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
                               value=[''],
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
                               value='',
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
                               value='',
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
        value=[''],
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
        value='',
        maxLength=20,
        title='exemple : voute, piedroit .....',
        rows=1
    ),
    html.H5("Longitude *"),
    dcc.Textarea(
        id='textarea-long',
        value='',
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
    dcc.Store(id="store-sensor-info-to-ingest", data={})
])

form_card = html.Div(id='form-card',
                     children=[left_column, right_column])

upload_card = html.Div(id="upload-file-card",
                       children=[
                           html.Div(id='upload-file-inner-card'),
                           dcc.Store(id='store-data-uploaded',),
                       ])

button_card = html.Div(id='button-card',
                       children=[

                           html.Button(id='button-ingest', hidden=True,
                                       title='intégrer les mesures dans la database'),
                           html.Button(title='Supprimer le capteur', id='button-delete-table', hidden=True),
                           html.Button(title='modifier les informations du capteur',
                                       id='button-update-sensors-info', hidden=True),
                       ])

owner_card = html.Div(id='owner-card', children=[
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
    form_card,
    button_card,
    upload_card,

])

message_card = html.Div(
    id="message-card",
    children=[
        html.H3(id='fig-message',
                children="Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant 👇."),
        html.H3(id='ingest-message'),
        html.H3(id="image-message"),

    ])

select_card = html.Div(
    id='select-card',
    children=[
        options_card,
        dcc.Graph(id='map',
                  config={'displaylogo': False, 'doubleClickDelay': 1000},
                  figure=create_map([], -1,48.8566,2.3522),
                  selectedData=None,
                  clickData=None
                  )
    ])

header = html.Div(
    id='header-card',
    children=[html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
              html.H1(id='welcome-info'),
              html.A('menu', href='/'),
              dcc.Location(id='url', refresh=False)])

image_card = html.Div(id='image-card', hidden=True,
                      children=[dcc.Upload(id='upload-image1-dcc', multiple=False),
                                dcc.Upload(id='upload-image2-dcc', multiple=False),
                                dcc.Upload(id='upload-image3-dcc', multiple=False)])


