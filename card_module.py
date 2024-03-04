import plotly.graph_objects as go

from dash import Dash, html, dcc
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json

with open("data_ratp/traces-du-reseau-de-transport-ferre-ratp.geojson", "r") as lines:
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


def generate_time_series_card():
    return html.Div(
        id='time-series-card',
        children=[dcc.Graph(id='graph-time-series', figure=fig0, config={'displaylogo': False})],
    )


def generate_map_card(fig):
    return html.Div(
        id="map-card",
        children=[
            dcc.Graph(id='map',
                      config={'displaylogo': False, 'doubleClickDelay': 1000},
                      figure=fig)]
    )


def generate_options_card(data):
    sensors_df = pd.DataFrame(data)

    return html.Div(
        id='options-card',
        children=[
            dcc.Store(id='store-time-serie'),
            html.H2("Réseau"),
            dcc.Dropdown(
                options=pd.Series(["RER", "METRO", "TRAM"]),
                id='dropdown-net',
                value=[],
                multi=True,
                style={'minWidth': '100px'}
            ),
            html.H2("ligne"),
            dcc.Dropdown(
                options=all_lines,
                value=[],
                id='dropdown-line',
                multi=True,
                style={'minWidth': '100px'}
            ),
            html.Br(),
            html.H2("capteur"),
            dcc.Dropdown(
                options=sensors_df["Table"],
                id='dropdown-table',
                multi=False,
                style={'minWidth': '200px'}
            ),
            html.H2("période"),
            dcc.DatePickerRange(
                display_format='D M Y',
                id="date-picker-select",
                start_date=datetime.today().date() - relativedelta(years=5),
                end_date=datetime.today().date(),
                min_date_allowed=datetime(2020, 1, 1),
                max_date_allowed=datetime.today().date(),
                initial_visible_month=datetime.today().date() - relativedelta(years=3),
                style={'padding': '0px 0px 0px 0px', 'margin': '0px'}
            ),
            html.Br(),
            html.H2("Agréger"),
            dcc.RadioItems(
                ['oui', 'non'],
                'non',
                id='aggregate-choice',
                labelStyle={'display': 'inline-block', 'marginTop': '5px'}
            ),
        ]
    )


def generate_upload_card():
    return html.Div(
        id="upload-card",
        children=[
            dcc.Upload(
                id='upload-file-dcc',
                children="Télécharger des mesures",
                multiple=False
            ),
            html.Div(id='upload-card-inner'),
            dcc.Store(id='store-data-uploaded'),
        ])


# boite de dialogue pour specifier le nom du capteur

def generate_form_card():
    return html.Div(id='form-card',
                    hidden=False,
                    children=[
                        html.Div(
                            id='form-card-column-left', children=[

                                html.H5("type de capteur"),
                                dcc.Textarea(
                                    id='textarea-model',
                                    disabled=True,
                                    value=''
                                ),
                                html.H5("Date de la pose *"),
                                dcc.Textarea(
                                    id='textarea-date-pose',
                                    value=''
                                ),
                                html.H5("Ouverture à la pose"),
                                dcc.Textarea(
                                    id='textarea-delta',
                                    value=''
                                ),
                                html.H5("précision sur la zone"),
                                dcc.Textarea(
                                    id='textarea-lieu',
                                    value=''
                                ),

                                html.H5("Latitude *"),
                                dcc.Textarea(
                                    id='textarea-lat',
                                    value=''
                                ),

                                dcc.Upload(
                                    id='upload-image-dcc',
                                    children="télécharger une image",
                                    multiple=False
                                ),
                            ]),
                        html.Div([
                            html.H5("numero du capteur *"),
                            dcc.Textarea(
                                id='textarea-num',
                                value=''
                            ),
                            html.H5("Date de la dépose"),
                            dcc.Textarea(
                                id='textarea-date-depose',
                                value=''
                            ),
                            html.H5("zone du capteur *"),
                            dcc.Textarea(
                                id='textarea-zone',
                                value=''
                            ),

                            html.H5("pk de la zone*"),
                            dcc.Textarea(
                                id='textarea-pk',
                                value=''
                            ),

                            html.H5("Longitude *"),
                            dcc.Textarea(
                                id='textarea-long',
                                value=''
                            ),

                            html.Br(),

                            html.P("", id="text-error-upload-image"),
                        ]),
                        dcc.Store(id="store-metadata-to-ingest", data={}),
                    ])


def generate_button_card():
    return html.Div(
        id="button-card",
        children=[
            html.Button(id='button-ingest', hidden=True, title='intégrer les mesures dans la database'),
            html.Button(title='Supprimer le capteur',
                        id='button-delete-table', hidden=True, ),
            html.Button(title='modifier les informations du capteur', id='button-update-metadata', hidden=True),

        ])


def generate_message_card():
    return html.Div(
        id="message-card",
        children=[
            dcc.Markdown(
                id='ingest-card-message',
                children="Dans le bloc du haut, indique la ligne et le réseau de ton nouveau capteur ou sélectionne un capteur existant.",
            ),

        ])
