from dash import html, dcc

from app_factory.utils.card import generate_options_card, generate_time_series_card, generate_upload_card, \
    generate_form_card, generate_button_card, generate_message_card
from app_factory.utils.fig import create_map

# definition de la mise en page de l'application
owner_layout = html.Div(
    id="app-container",
    children=[
        html.Header(
            id='app-container-header',
            children=[html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
                      html.H1(id='welcome-info'),
                      dcc.Location(id='url', refresh=False)],
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
                                          figure=create_map([], -1)),
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

guest_layout = html.Div(
    id="app-container",
    children=[
        html.Header(
            id='app-container-header',
            children=[
                html.Img(src='/static/img/logo_ratp_infra_pour_dash.png', width='15%', style={'float': 'right'}),
                html.H1(id='welcome-info'),
                dcc.Location(id='url', refresh=False)],
            className="header"),

        html.Div(
            id="app-container-inner",
            children=[
                dcc.Store(id='store-map-csv'),

                html.Div(
                    id='data-card', children=[
                        html.Div(
                            id='select-data-card',
                            children=[
                                generate_options_card(),
                                dcc.Graph(id='map',
                                          config={'displaylogo': False, 'doubleClickDelay': 1000},
                                          figure=create_map([], -1)
                                          )
                            ]),

                        generate_form_card(),

                    ]
                ),
                generate_message_card(),
                generate_time_series_card(),

            ]
        )
    ]
)
