from dash import html, dcc

from app_factory.utils.card import message_card, select_card, header, image_card, owner_card


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
                            html.Div(id='time-series-card', hidden=True),
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
                            html.Div(id='time-series-card', hidden=True),

                         ]),
                     image_card
                 ]),

    ])
