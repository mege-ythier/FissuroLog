import plotly.graph_objects as go

from dash import Dash, html, dcc
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json

with open("data_ratp/traces-des-lignes-de-transport-en-commun-ratp.geojson", "r") as lines:
    ratp_dict = json.load(lines)

all_lines = ["all"]
for feature in ratp_dict['features']:
    line = feature['properties']['route_short_name']
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
    table_options = sensors_df["Table"]

    #sensors_df["Route"] = sensors_df["Reseau"] + sensors_df["Ligne"].astype(str)
    #sensors_df["Date_debut"] = pd.to_datetime(sensors_df["Date_debut"], format='mixed', dayfirst=True)
    #sensors_df["Date_fin"] = pd.to_datetime(sensors_df["Date_fin"], format='mixed', dayfirst=True)

    return html.Div(
        id='options-card',
        children=[
            dcc.Store(id='store-time-serie'),
            html.H2("Réseau"),
            dcc.Dropdown(
                options=pd.Series(["RER", "M", "T"]),
                id='dropdown-net',
                value=[],
                multi=True,
                style={'minWidth': '150px'}
            ),
            html.H2("ligne"),
            dcc.Dropdown(
                # options=pd.Series(monitored_lines).unique(),#last
                options=all_lines,
                value=[],  # last
                id='dropdown-line',
                multi=True,
                style={'minWidth': '100px'}
            ),
            html.Br(),
            html.H2("capteur"),
            dcc.Dropdown(
                options=table_options,#sensors_df["Table"],
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

            html.Br(),
            html.Button(
                id='button_update_fig', disabled=True,
                style={'background-color': 'rgb(0, 170, 145)'})

        ]
    )


def generate_upload_card():
    return html.Div(
        id="upload-card",
        children=[
            html.Button('afficher les informations du capteur',
                        id='button-show-metadata',hidden=True),
            dcc.Upload(
                id='upload-file',
                children="Télécharger des mesures",
                style={
                    # 'width': '20%',
                    # 'height': '60px',
                    'font-size': '10px',
                    'color': 'rgb(255, 255, 255)',
                    'background-color': 'rgb(10, 0, 130)',
                    # 'lineHeight': '50px',
                    # 'borderWidth': '1px',
                    # 'borderStyle': 'dashed',
                    'borderRadius': '50px',
                    'textAlign': 'center',
                    'margin': '10px',
                    'padding': '20px'
                },
                multiple=False
            ),
            html.Div(id='upload-card-inner'),
            dcc.Store(id='store-data-uploaded'),

        ])


# boite de dialogue pour specifier le nom du capteur
#def generate_ingest_children():
def generate_form_card():
    return html.Div(id='form-card',
                    hidden=True,
                    children=[
                        html.H5("type de capteur"),
                        dcc.Textarea(
                            id='textarea-sensor-model',
                            readOnly=True,
                            value=''
                        ),
                        html.H5("numero du capteur *"),
                        dcc.Textarea(
                            id='textarea-sensor-num',
                            value=''
                        ),

                        html.H5("zone du capteur *"),
                        dcc.Textarea(
                            id='textarea-zone',
                            value=''
                        ),
                        html.H5("précision sur la zone"),
                        dcc.Textarea(
                            id='textarea-lieu',
                            value=''
                        ),

                        html.H5("pk de la zone"),
                        dcc.Textarea(
                            id='textarea-pk',
                            value=''
                        ),

                        html.H5("Latitude *"),
                        dcc.Textarea(
                            id='textarea-lat',
                            value='0'
                        ),
                        html.H5("Longitude *"),
                        dcc.Textarea(
                            id='textarea-long',
                            value='0'
                        ),
                        html.H5("Date de la pose *"),
                        dcc.Textarea(
                            id='textarea-date-pose',
                            value=''
                        ),
                        html.H5("Date de la dépose"),
                        dcc.Textarea(
                            id='textarea-date-depose',
                            value=''
                        ),
                        html.H5("Ouverture à la pose"),
                        dcc.Textarea(
                            id='textarea-delta',
                            value='0'
                        ),

                        html.Br(),
                        dcc.Upload(
                            id='upload-image',
                            children="télécharger une image",
                            style={
                                'font-size': '0.83em',
                                'color': 'rgb(255, 255, 255)',
                                'background-color': 'rgb(10, 0, 130)',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                #'borderRadius': '10px',
                                'textAlign': 'center',
                                #'margin': '10px'
                                'padding': '20px'
                            },
                            multiple=False
                        ),
                        html.P("", id="text-error-upload-image"),

                        dcc.Store(id="store-metadata-to-ingest", data={}),


                    ])
