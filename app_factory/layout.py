from dash import html, dcc

from app_factory.utils.card import generate_message_card, generate_select_card, generate_header, \
    generate_image_card, generate_owner_card, generate_upload_card


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
                             dcc.Store(id='store-sensors-info'),
                            generate_message_card(),
                             html.Div(
                                 id='top-card', children=[
                                     generate_owner_card(),
                                     generate_select_card(),

                                 ]),



                            html.Div(id ='time-series-card', hidden=True),
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
                             dcc.Store(id='store-sensors-info'),
                             generate_message_card(),
                             html.Div(
                                 id='top-card', children=[
                                     generate_select_card(),
                                 ]),


                            html.Div(id ='time-series-card', hidden=True),

                         ]),
                     generate_image_card()
                 ]),

    ])
