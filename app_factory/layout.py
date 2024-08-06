from dash import html, dcc

from app_factory.utils.card import generate_upload_card, generate_form_card, generate_button_card, \
    generate_message_card, generate_select_card, generate_header, \
    fig0, generate_image_card


# definition de la mise en page de l'application
owner_layout = html.Div(
    id="app-card",
    children=[
        generate_header(),
        html.Div(id='main-card',
                 children=[

                     html.Div(
                         id="left-card",
                         children=[
                             dcc.Store(id='store-map-csv'),
                             html.Div(
                                 id='top-card', children=[
                                     generate_button_card(),
                                     generate_upload_card(),
                                     generate_select_card(),
                                     generate_form_card(),
                                 ]),

                            generate_message_card(),

                            dcc.Graph(id='time-series', figure=fig0, config={'displaylogo': False}),

                            dcc.ConfirmDialog(id='confirm-throw-ingestion'),
                            dcc.ConfirmDialog(id='confirm-read-message'),
                            dcc.ConfirmDialog(id='confirm-delete-table'),
                         ]
                     ),
                     generate_image_card()
                 ]),

    ]
)


guest_layout = html.Div(
    id="app-card",
    children=[
        generate_header(),
        html.Div(id='main-card',
                 children=[

                     html.Div(
                         id='left-card',
                         children=[
                             dcc.Store(id='store-map-csv'),
                             html.Div(
                                 id='top-card', children=[
                                     generate_select_card(),
                                     generate_form_card(),
                                 ]),
                             generate_message_card(),

                            dcc.Graph(id='time-series', figure=fig0, config={'displaylogo': False}),

                         ]),
                     generate_image_card()
                 ]),

    ])
