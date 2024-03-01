import plotly.graph_objects as go
import pandas as pd
import json


# importation des metadata
def create_time_series_fig(df, table_name, delta_mm):
    title = f"table affichée: {table_name}"

    fig = go.Figure()

    fig.add_annotation(x=0, y=1.25, xanchor='center', yanchor='top',
                       xref='paper', yref='paper', showarrow=False, align='right',
                       text=title)

    fig.add_trace(go.Scatter(y=df["mm"],
                             x=df.index,
                             name="ouverture",
                             yaxis="y1",
                             marker=dict(
                                 symbol='cross',
                                 size=3,
                                 color="#F0AA00",
                                 opacity=0.7),
                             )
                  )
    fig.add_trace(go.Scatter(y=df["mm"] - delta_mm,
                             x=df.index,
                             name="ouverture relative",
                             yaxis="y1",
                             marker=dict(
                                 symbol='cross',
                                 size=3,
                                 color="green",
                                 opacity=0.7),
                             visible=False
                             )
                  )

    fig.add_trace(go.Scatter(y=df["°C"],
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

    yaxis1_shift = dict(
        anchor="x",
        domain=[0, 0.45],
        mirror=True,
        title="mm",
        range=[-1, 1],
        showline=True,
        side="left",
        dtick=0.5,
        # tickmode="array",
        # tickvals=[-delta_mm-1, -delta_mm, -delta_mm-1],
        # tickvals=[-15, -10, -5],
        # ticktext=[-5-delta_mm ,0-delta_mm, 5-delta_mm],
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'
    )

    yaxis1_no_shift = dict(
        anchor="x",
        domain=[0, 0.45],
        # linecolor="#673ab7",
        mirror=True,
        title="mm",
        # titlefont={"color": "#673ab7"},
        showline=True,
        side="left",
        # tickfont={"color": "#673ab7"},
        tickmode="auto",
        # dtick=1,
        ticks="",
        type="linear",
        zeroline=False,
        gridcolor='grey'

    )

    fig.update_layout(
        height=380,
        margin={'l': 10, 'b': 10, 'r': 10, 't': 60},
        plot_bgcolor='rgba(0,0,0,0)',
        #paper_bgcolor='rgba(0,0,0,0)',
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
            domain=[0.55, 1],
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
                # type='buttons',
                type='dropdown',
                buttons=[
                    dict(label='Mesures brutes',
                         method='update',
                         args=[{'visible': [True, False, True]}, {"yaxis": yaxis1_no_shift}]),
                    dict(label='Mesures centrées',
                         method='update',
                         args=[{'visible': [False, True, True]}, {"yaxis": yaxis1_shift}]),
                ],
                active=0,
                showactive=True,
                direction="down",
                x=-0.015,
                xanchor="right",
                y=0.52,
                yanchor="top",
                bgcolor="white"

            ),
        ],
    )
    return fig


def update_time_series_fig(start_date, end_date, table_name):
    import sqlite3
    start_date_timestamp = start_date.timestamp()
    end_date_timestamp = end_date.timestamp()

    # charger les données
    conn = sqlite3.connect('data_capteur/database.db')
    query = f"SELECT * from {table_name} WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}"
    df_from_sensor_table = pd.read_sql_query(query, conn)
    conn.close()

    # convertir le timstamps en seconde axe x
    df_from_sensor_table.unix = pd.to_datetime(df_from_sensor_table.unix, unit='s')
    df_from_sensor_table = df_from_sensor_table.set_index('unix')
    df_from_sensor_table.index.name = "Date"

    return create_time_series_fig(df_from_sensor_table, table_name)


def create_map(sensors_data):
    with open("data_ratp/traces-du-reseau-de-transport-ferre-ratp.geojson", "r") as lines:
        ratp_dict = json.load(lines)
    with open("data_ratp/couleur-ratp-carte.json", 'r') as files:
        color_dict = json.load(files)

    sensors_df = pd.DataFrame(sensors_data)
    sensors_df["Route"] = sensors_df["Reseau"] +" "+sensors_df["Ligne"].astype(str)

    routes_displayed = (sensors_df["Route"]).unique()

    fig = go.Figure()
    fig.update_layout(
        # height=600,
        autosize=True,
        margin={'l': 0, 'b': 0, 'r': 10, 't': 0},
        paper_bgcolor='rgba(245, 250, 245,1)',
        mapbox=dict(
            style='carto-positron',#'open-street-map',
            center={"lat": 48.8566, "lon": 2.3522},  # Centre de la carte
            zoom=10,  # Niveau de zoom
        ),
        legend_itemdoubleclick="toggleothers",
        legend_itemclick="toggle",
        legend_groupclick="togglegroup",
        clickmode='event+select')

    # dessiner les lignes
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
        sensor = sensors_df.iloc[i, :]
        fig.add_trace(
            go.Scattermapbox(
                name=sensor["Table"],
                mode="markers",
                lat=[sensor["Latitude"]],
                lon=[sensor["Longitude"]],
                hoverlabel=dict(bgcolor="pink", namelength=15),
                # hoverinfo='text',
                # hovertext=sensor["Zone"],
                # text=str(sensor["Ligne"]),
                customdata=[sensor],
                hovertemplate='Date de la pose: %{customdata[10]}<br>'
                              'Ouverture initiale: %{customdata[12]}<br>'
                              'Modèle: %{customdata[6]}<br>'
                              'Numéros: %{customdata[7]}<br> ',
                marker=dict(
                    size=10,
                    color='black',
                    opacity=0.7
                ),
                selected=dict(marker=dict(
                    size=20,
                    color='green',
                    opacity=1
                )),

                unselected=dict(marker=dict(
                    size=10,
                    color='black',
                    opacity=0.5
                )),

                legendgroup=sensor["Route"],
                legendgrouptitle={"font": {"color": "blue", "family": "Arial", "size": 3}, "text": "test"},
                showlegend=False,
                visible=True
                # cluster=dict(enabled=True,color="yellow",maxzoom=23,size=1)
            )
        )

    return fig
