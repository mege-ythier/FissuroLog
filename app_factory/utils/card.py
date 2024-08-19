import plotly.graph_objects as go

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

fig0 = go.Figure()
fig0.update_layout(
    # autosize=True,
    height=10,
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    showlegend=False,  # Masquer la légende
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=None),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=None),
)


def generate_options_card():
    return html.Div(
        id='options-card',
        children=[

            html.H2("période"),
            dcc.DatePickerRange(
                display_format='D M Y',
                id="date-picker-select",
                start_date=datetime.today().date() - relativedelta(years=30),
                end_date=datetime.today().date(),
                min_date_allowed=datetime(2000, 1, 1),
                max_date_allowed=datetime.today().date(),
                initial_visible_month=datetime.today().date() - relativedelta(years=2),
            ),
            html.Br(),
            html.H2("Agréger"),
            dcc.RadioItems(
                ['oui', 'non'],
                'non',
                id='aggregate-choice',
                labelStyle={'display': 'inline-block', 'marginTop': '5px'}
            ),
            html.Button(id='button-update-fig', hidden=True, title='charger les mesures'),
        ]
    )


def generate_upload_card():
    return html.Div(id="upload-file-card",
                    children=[
                        html.Div(id='upload-file-widget',
                                 children=[
                                     dcc.Upload(
                                         id='upload-file-dcc',
                                         children="Selectionner des mesures",
                                         multiple=False
                                     ),
                                     html.Button(id='button-ingest', hidden=True,
                                                 title='intégrer les mesures dans la database')]),
                        html.Div(id='upload-file-inner-card'),
                        dcc.Store(id='store-data-uploaded'),
                    ])


# boite de dialogue pour specifier le nom du capteur

left_column = html.Div(
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
        html.H5("localisation dans le réseau"),
        dcc.Textarea(
            id='textarea-lieu',
            value='',
            title='Ici tu expliques comment accéder au capteur dans le reseau',
            rows=7),

    ])

right_column = html.Div([
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
        rows=4,
    ),
    dcc.Store(id="store-sensors-info-to-ingest", data={})
])


def generate_form_card():
    return html.Div(id='sensor-card',
                    children=[
                        html.Div(id='title-sensor-card', children=[html.H2("capteur"),
                            dcc.Textarea(
                                id='dropdown-table',
                                value='',
                                # multi=False,
                                style={'maxWidth': '50px'},
                                disabled=True
                            )]),
                        html.Div(id='form-card',
                                 hidden=False,
                                 children=[left_column, right_column])])


def generate_button_card():
    return html.Div(
        id="button-card",
        children=[

            html.Button(title='Supprimer le capteur',
                        id='button-delete-table', hidden=True, ),
            html.Button(title='modifier les informations du capteur', id='button-update-sensors-info', hidden=True),

        ])


def generate_owner_card():
    return html.Div(
        id="owner-card",
        children=[
            generate_upload_card(),
            generate_button_card(),

        ])


def generate_message_card():
    return html.Div(
        id="message-card",
        children=[
            html.H3(id='fig-message'),
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
    return html.Header(
        id='header-card',
        children=[html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
                  html.H1(id='welcome-info'),
                  html.A('menu', href='/'),
                  dcc.Location(id='url', refresh=False)],
        className="header")


def generate_image_card():
    return html.Div(id='image-card', hidden=True,
                    children=[dcc.Upload(id='upload-image1-dcc', multiple=False),
                              dcc.Upload(id='upload-image2-dcc', multiple=False),
                              dcc.Upload(id='upload-image3-dcc', multiple=False)])
