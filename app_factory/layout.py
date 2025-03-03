import dash_daq as daq
import pandas as pd
from dash import html, dcc
from app_factory.utils.card import message_card, select_card, header, image_card, owner_card
from app_factory.utils.meteo_graph import draw_ratp_map
from datetime import datetime
from dateutil.relativedelta import relativedelta

# definition de la mise en page de l'application
owner_layout = html.Div(
    id="app-card",
    children=[
        header,
        html.Div(id='main-card',
                 children=[

                     html.Div(
                         id="left-card",
                         children=[
                            dcc.Store(id='store-sensors-info'),
                            message_card,
                            html.Div(id='top-card', children=[owner_card, select_card]),
                            dcc.Loading(type="circle", id='time-series-card'),
                            dcc.ConfirmDialog(id='confirm-throw-ingestion'),
                            dcc.ConfirmDialog(id='confirm-read-message'),
                            dcc.ConfirmDialog(id='confirm-delete-table'),
                         ]
                     ),
                     image_card
                 ]),

    ]
)


guest_layout = html.Div(
    id="app-card",
    children=[
        header,
        html.Div(id='main-card',
                 children=[

                     html.Div(
                         id='left-card',
                         children=[
                            dcc.Store(id='store-sensors-info'),
                            message_card,
                            html.Div(id='top-card', children=[select_card]),
                            dcc.Loading(type="circle", id='time-series-card'),

                         ]),
                     image_card
                 ]),

    ])

info_stations = pd.read_csv('app_factory/assets/meteo/info_stations.csv', sep=';', index_col="Id_station")
id_stations = [92073001, 78481001, 94042001, 93050001, 94068001, 91027002, 91275001, 78640001, 77468001, 95088001,
                   95527001, 75106001, 75107005, 75110001, 75114001, 75114007, 75116008, 75114001]


meteo_header = html.Div(
    id='header-app',
    children=[
        html.Div(id="logo-header-app",children =[

                html.A(html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='20%'), href='/')]),
        html.H1(id='welcome-info'),

        daq.ToggleSwitch(
            id="toggle-switch",
            value=True,
            label=["historique","temps reel"],
            color="#FFC300",
            style={"color": "#FFC300"}
        ),

        dcc.Location(id='url', refresh=False)])




meteo_options = html.Div(
    id='meteo-options',
    children=[
        dcc.DatePickerRange(
             display_format='D M Y',
             id="date-picker",
             start_date=datetime.today().date() - relativedelta(days=2),
             end_date=datetime.today().date() - relativedelta(days=1),
             min_date_allowed=datetime.today().date() - relativedelta(days=8),
             max_date_allowed=datetime.today().date() - relativedelta(days=1),
             initial_visible_month=datetime.today().date() - relativedelta(days=8),

         ),
        dcc.Checklist(
             options=[{'label': row['Nom_usuel'], 'value': index} for index, row in info_stations.iterrows() if
                      index in id_stations],
             value=[92073001],
             id='checklist-stations',
             style={'minWidth': '100px', 'overflow': 'auto'}
         ),


        html.Button(id="load-button")],

    )


left_meteo_app = html.Div(id='left-meteo-app',style={'display': 'none'},
                        children=[
                            html.Button(
                                id="hamburger-button",
                                n_clicks=1,
                                children=html.Div(
                                    children=[html.Div(className="hamburger-button-cross")],
                                    className="hamburger-button-menu"
                                ),
                                style={'display': 'block'}),
                            meteo_options])



meteo_layout = html.Div(
    id="meteo-app",
    children=[
        meteo_header,

        html.Div(id='main-meteo-app',

                 children=[

                     html.Div(id='right-meteo-app',
                              children=[
                                dcc.Store(id='store-meteo'),
                                dcc.Store(id='store-climato'),

                                dcc.Loading(type="circle", id='loading-store',children=[
                                                dcc.Graph(id='map', figure=draw_ratp_map(),
                                                            config={'displaylogo': False, 'doubleClickDelay': 1000,'scrollZoom': True})]),

                                html.Div( id='one-station-output'),
                                dcc.Loading(type="circle", id='all-stations-output'),


                                            ]),
                    left_meteo_app,





]),


])

