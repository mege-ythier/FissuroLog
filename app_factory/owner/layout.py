
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, callback, State

from flask_login import current_user, login_required, logout_user, login_manager, login_user


from app_factory.card_module import generate_options_card, generate_time_series_card, generate_upload_card, fig0, \
    generate_form_card, generate_button_card, generate_message_card

from app_factory.fig_module import create_time_series_fig, create_map
import pandas as pd
from app_factory import db

#importer la tables des capteurs
# sensors_df = pd.read_sql('select * from sensors_tb',con=db.engine)
# sensors_df["Date_pose"]=sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
# sensors_df["Date_depose"]=sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')
# sensors_list=sensors_df.to_dict('records')

    # definition de la mise en page de l'application
layout = html.Div(
        id="app-container",
        children=[
            html.Header(
                id='app-container-header',
                children=[html.Img(src='/static/dist/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
                          html.H1(f'Bienvenue Fissuro logger', id='welcome-info')
                          ,dcc.Location(id='url', refresh=False)],
                className="header"),

            html.Div(
                id="app-container-inner",
                children=[

                    dcc.Store(id='store-map-csv'),
                    

                    html.Div(
                        id='data-card', children=[
                            generate_button_card(),
                            generate_upload_card(),
                            html.Div(
                                id='select-data-card',
                                children=[
                                    generate_options_card(),
                                    dcc.Graph(id='map',
                                              config={'displaylogo': False, 'doubleClickDelay': 1000},
                                              figure=create_map([])),
                                ]),

                            generate_form_card(),

                        ]
                    ),
                    generate_message_card(),
                    generate_time_series_card(),

                    html.Div(id='ingest-info'),
                    dcc.ConfirmDialog(
                        id='confirm-throw-ingestion'
                    ),

                    dcc.ConfirmDialog(
                        id='confirm-read-message'
                    ),
                    dcc.ConfirmDialog(
                        id='confirm-delete-table'
                    ),

                ]
            )
        ]
    )


