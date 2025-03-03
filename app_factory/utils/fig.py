import base64
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import json
from dash import dcc, html
from sqlalchemy import text

fig0 = go.Figure()
fig0.update_layout(
    # autosize=True,
    autosize=True,
    height=10,
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,100,100,100)',
    showlegend=False,  # Masquer la légende
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=None),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=None),
)


def create_time_series_fig(df, table_name, delta_mm):
    title = f"capteur: {table_name}"

    fig = go.Figure()

    fig.add_annotation(x=0, y=1.25, xanchor='center', yanchor='top',
                       xref='paper', yref='paper', showarrow=False, align='right',
                       text=title)

    fig.add_trace(go.Scatter(y=df["mm"],
                             x=df.index,
                             name="ouverture brute",
                             yaxis="y1",
                             marker=dict(
                                 symbol='cross',
                                 size=3,
                                 color="#F0AA00",
                                 opacity=0.7),
                             )
                  )

    delta_mm = 0 if delta_mm == '' else np.float64(delta_mm)

    fig.add_trace(go.Scatter(y=df["mm"] - delta_mm,
                             x=df.index,
                             name="ouverture",
                             yaxis="y1",
                             marker=dict(
                                 symbol='cross',
                                 size=3,
                                 color="green",
                                 opacity=0.7),
                             )
                  )

    fig.add_trace(go.Scatter(y=df["celsius"],
                             x=df.index,
                             name="température",
                             yaxis="y2",
                             marker=dict(
                                 symbol='x',
                                 size=3,
                                 color="#CD5A96",
                                 opacity=0.7)
                             )
                  )

    fig.update_traces(mode='markers', showlegend=False)

    yaxis1_shift_zoom_1 = dict(
        anchor="x",
        domain=[0, 0.5],
        mirror=True,
        title="mm",
        range=[-1.1, 1.1],
        showline=True,
        side="left",
        dtick=0.5,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'
    )

    yaxis1_shift_zoom_2 = dict(
        anchor="x",
        domain=[0, 0.5],
        mirror=True,
        title="mm",
        range=[-0.51, 0.51],
        showline=True,
        side="left",
        dtick=0.25,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'
    )

    yaxis1_shift_zoom_5 = dict(
        anchor="x",
        domain=[0, 0.5],
        mirror=True,
        title="mm",
        range=[-0.205, 0.205],
        showline=True,
        side="left",
        dtick=0.1,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'
    )

    yaxis1_shift_zoom_10 = dict(
        anchor="x",
        domain=[0, 0.5],
        mirror=True,
        title="mm",
        range=[-0.11, 0.11],
        showline=True,
        side="left",
        dtick=0.05,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'
    )

    yaxis1_no_shift = dict(
        anchor="x",
        domain=[0, 0.5],
        # linecolor="#673ab7",
        mirror=True,
        title="mm",
        showline=True,
        side="left",
        tickmode="auto",
        # dtick=1,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'

    )

    fig.update_layout(
        height=390,
        autosize=True,
        margin={'l': 10, 'b': 10, 'r': 10, 't': 60},
        # plot_bgcolor='rgb(245, 250, 245)',
        plot_bgcolor='rgba(0,0,0,0)',
        # paper_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgb(245, 250, 245)',
        font={"color": "rgb(10, 0, 130)"},
        dragmode="zoom",
        hovermode="x",
        legend=dict(traceorder="reversed"),
        xaxis=dict(
            showgrid=True,
            autorange=True,
            rangeslider=dict(autorange=True),
            type="date",
            gridcolor='grey'
        ),
        yaxis1=yaxis1_no_shift,

        yaxis2=dict(
            anchor="x",
            autorange="reversed",
            domain=[0.6, 1],
            # linecolor="#E91E63",
            mirror=True,
            title="°C",
            # titlefont={"color": "#E91E63"},
            # range=[0, 50],
            showline=True,
            side="left",
            # tickfont={"color": "#E91E63"},
            tickmode="auto",
            ticks="",
            type="linear",
            zeroline=False,
            gridcolor='grey'
        )
    )

    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1d",
                         step="day",
                         stepmode="backward"),
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    fig.update_layout(
        updatemenus=[
            dict(
                type='dropdown',
                buttons=[
                    dict(label='aucun',
                         method='update',
                         args=[{'visible': [True, False, True]}, {"yaxis": yaxis1_no_shift}]),
                    dict(label='1',
                         method='update',
                         args=[{'visible': [False, True, True]}, {"yaxis": yaxis1_shift_zoom_1}]),
                    dict(label='2',
                         method='update',
                         args=[{'visible': [False, True, True]}, {"yaxis": yaxis1_shift_zoom_2}]),
                    dict(label='5',
                         method='update',
                         args=[{'visible': [False, True, True]}, {"yaxis": yaxis1_shift_zoom_5}]),
                    dict(label='10',
                         method='update',
                         args=[{'visible': [False, True, True]}, {"yaxis": yaxis1_shift_zoom_10}]),
                ],
                active=0,
                showactive=True,
                direction="down",
                x=-0.1,
                xanchor="left",
                y=0.57,
                yanchor="top",
                bgcolor="white"
            ),

            dict(
                type='dropdown',
                buttons=[
                    dict(label='point',
                         method='update',
                         args=[{'mode': ['markers', 'markers', 'markers']}]),
                    dict(label='ligne',
                         method='update',
                         args=[{'mode': ['lines+markers', 'lines+markers', 'lines+markers']}]),
                ],
                active=0,
                showactive=True,
                direction="down",
                x=-0.1,
                xanchor="left",
                y=0.1,
                yanchor="top",
                bgcolor="white"

            ),
        ],
    )

    fig.add_annotation(x=-0.1, y=0.18, xanchor='left', yanchor='top',
                       xref='paper', yref='paper', showarrow=False, align='right',
                       text="tracé")

    fig.add_annotation(x=-0.1, y=0.65, xanchor='left', yanchor='top',
                       xref='paper', yref='paper', showarrow=False, align='right',
                       text="zoom")
    return fig


def create_map(sensors_json: list[dict], sensor_index, lat , lon):
    with open("./app_factory/static/json/traces-du-reseau-de-transport-ferre-ratp.geojson", "r") as lines:
        ratp_dict = json.load(lines)
    with open("./app_factory/static/json/couleur-ratp-carte.json", 'r') as files:
        color_dict = json.load(files)

    fig = go.Figure()
    fig.update_layout(
        # height=600,
        autosize=True,
        margin={'l': 0, 'b': 0, 'r': 10, 't': 0},
        paper_bgcolor='rgba(245, 250, 245,1)',
        mapbox=dict(
            style='carto-positron',  # 'open-street-map',
            center={"lat":lat, "lon":lon},  # Centre de la carte
            zoom=11.5,  # Niveau de zoom
        ),
        legend_itemdoubleclick="toggleothers",
        legend_itemclick="toggle",
        legend_groupclick="togglegroup",
        clickmode='event+select')

    # dessiner les lignes
    if sensors_json == []:
        fig.add_trace(go.Scattermapbox())
    else:
        sensors_df = pd.DataFrame(sensors_json)
        sensors_df["Route"] = sensors_df["Reseau"] + " " + sensors_df["Ligne"].astype(str)
        sensors_df = sensors_df.fillna('')
        routes_displayed = (sensors_df["Route"]).unique()
        routes_drawn = []
        for feature in ratp_dict['features']:
            geometry = feature.get('geometry')
            if geometry:
                route = feature['properties']['res_com']
                coordinates = feature['geometry']['coordinates']
                for i in range(len(coordinates)):
                    lon, lat = zip(*coordinates[i])
                    fig.add_trace(
                        go.Scattermapbox(
                            mode="lines",
                            lon=lon,
                            lat=lat,
                            line=dict(width=3, color=color_dict[route]),
                            name=route,
                            hoverinfo='text',
                            hovertext=route,
                            showlegend=False,
                            customdata=[route] * len(lon),
                            legendgroup=route,
                            visible='legendonly',
                        )
                    )
                    if route in routes_displayed:
                        fig.update_traces(selector=dict(name=route), patch=dict(visible=True))

                    if route not in routes_drawn:
                        fig.update_traces(selector=dict(name=route), patch=dict(showlegend=True))
                    routes_drawn.append(route)

        # dessiner les capteurs
        for i in range(sensors_df.shape[0]):
            # remplacer les valeurs vides
            sensor = sensors_df.iloc[i, :]
            fig.add_trace(
                go.Scattermapbox(
                    name="",
                    # name=sensor["Table"],
                    mode="markers",
                    lat=[sensor["Latitude"]],
                    lon=[sensor["Longitude"]],
                    hoverlabel=dict(bgcolor="black", font=dict(color="white"), namelength=15),
                    customdata=[sensor],
                    hovertemplate='Fissuromètre <b>%{customdata[0]} </b><br><br>'
                                  'Modèle: %{customdata[2]}<br>'
                                  'Date de la pose: %{customdata[10]}<br>'
                                  'Ouverture initiale: %{customdata[12]} mm<br>'
                                  'Dernière collecte: %{customdata[14]} <br>'
                                  'Structure:%{customdata[5]}<br>'
                                  'pk:%{customdata[7]}<br>'
                                  'Localisation:%{customdata[6]}<br>'

                    ,
                    marker=dict(
                        size=10,
                        color='black',
                        opacity=0.3
                    ),
                    selected=dict(marker=dict(
                        size=20,
                        color='green',
                        opacity=1
                    )),

                    unselected=dict(marker=dict(
                        size=10,
                        color='black',
                        opacity=0.3
                    )),
                    selectedpoints=[0] if i == sensor_index else [],

                    legendgroup=sensor["Route"],
                    legendgrouptitle={"font": {"color": "blue", "family": "Arial", "size": 3}, "text": "test"},
                    showlegend=False,
                    visible=True
                    # cluster=dict(enabled=True,color="yellow",maxzoom=23,size=1)
                )
            )

    return fig

def query_time_series(db, sensor_id, start_date, end_date, aggregate):
    start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
    end_date_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()
    query = ""
    df = pd.DataFrame()
    if aggregate =="brute":
        query = text(f"""
        SELECT *
        FROM F{sensor_id}
        WHERE  unix > {start_date_timestamp} and unix < {end_date_timestamp}
        """)
        df = pd.read_sql(query, con=db.engine)
        df['Date'] = pd.to_datetime(df['unix'], unit='s')
        df = df.drop('unix', axis=1)

    if aggregate == "1jour":
        if db.engine.name == 'sqlite':
            query = text(f"""
                      SELECT date(unix, 'unixepoch') AS Date, mm, celsius
                      FROM F{sensor_id}
                      WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                      GROUP BY Date
                      ORDER BY Date
                  """)

        if db.engine.name == 'mysql':
            query = text(
                f"""
                      SELECT DATE_FORMAT(FROM_UNIXTIME(unix), '%Y-%m-%d') AS Date, AVG(mm) AS mm, AVG(celsius) AS celsius
                      FROM F{sensor_id}
                      WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                      GROUP BY Date
                      ORDER BY Date
                  """)
        df = pd.read_sql(query, con=db.engine)

    if aggregate == "1h":
        if db.engine.name == 'sqlite':
            query = text(f"""
                SELECT  strftime('%Y-%m-%d %H:00:00', datetime(unix,'unixepoch')) AS Date, mm, celsius
                FROM F{sensor_id}
                WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                GROUP BY Date
                ORDER BY Date
            """)
        if db.engine.name == 'mysql':
            query = text(
                f"""
                SELECT DATE_FORMAT(FROM_UNIXTIME(unix), '%Y-%m-%d %H:00:00') AS Date, AVG(mm) AS mm, AVG(celsius) AS celsius
                FROM F{sensor_id}
                WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                GROUP BY Date
                ORDER BY Date
            """)

        df = pd.read_sql(query, con=db.engine)
    df = df.set_index('Date')
    return df


def query_images_and_create_image_card(db, sensor_id, card_id, role):
    try:
        query = f"""
                    SELECT data
                    FROM sensors_image_tb
                    WHERE sensor_id ='{sensor_id}' AND card_id={card_id}
                    ORDER BY id DESC
                    LIMIT 1
                    """
        image_from_database = db.session.execute(text(query)).scalar()
        image_encoded = base64.b64encode(image_from_database).decode('utf-8')

    except:
        if role == 'owner':
            return html.H4("Click pour ajouter une image")

    else:
        return html.Img(src=f"data:image/png;base64,{image_encoded}")
