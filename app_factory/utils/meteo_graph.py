import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


def draw_ratp_map():
    with open("./app_factory/static/json/traces-du-reseau-de-transport-ferre-ratp.geojson", "r") as lines:
        ratp_dict = json.load(lines)
    with open("./app_factory/static/json/couleur-ratp-carte.json", 'r') as files:
        color_dict = json.load(files)

    fig = go.Figure()
    fig.update_layout(
        autosize=True,
        height=500,
        margin={'l': 0, 'b': 0, 'r': 10, 't': 0},
        paper_bgcolor='rgba(245, 250, 245,1)',
        mapbox={'style': 'carto-positron', 'center': {"lat": 48.8566, "lon": 2.3522}, 'zoom': 11.5},
        legend_itemdoubleclick="toggleothers",
        legend_itemclick="toggle",
        legend_groupclick="togglegroup",
        clickmode='event+select'

    )

    routes_drawn = []
    for feature in ratp_dict['features']:
        geometry = feature.get('geometry')
        if geometry:
            route = feature['properties']['res_com']
            coordinates = feature['geometry']['coordinates']
            network = route.split(" ")[0]
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
                        visible=False if network == 'TRAM' else True
                    )
                )
                if route not in routes_drawn:
                    fig.update_traces(selector=dict(name=route), patch=dict(showlegend=True))
                routes_drawn.append(route)

    return fig


# dessiner les capteurs

def add_stations_to_map(fig, df):
    info_stations = pd.read_csv('app_factory/assets/meteo/info_stations.csv', sep=';', index_col="Id_station")

    date_on_map = str(df['paris_time'].max()).split("+")[0]

    data_stations = df.set_index('paris_time').groupby('id_station').sum()
    data_stations.index = data_stations.index.astype(int)
    data_stations = pd.merge(right=data_stations, left=info_stations, how='inner', left_index=True, right_index=True)

    if "rr_per" in data_stations.columns: data_stations.rename(columns={'rr_per': 'RR1'}, inplace=True)

    fig.update_layout(
        title={
            'text': f"Sources : public-api.meteofrance.fr le {date_on_map}",
            'y': 0.05,
            'x': 0,
            'xanchor': 'left',
            'yanchor': 'bottom'
        }
    )

    fig.add_trace(
        go.Scattermapbox(
            name="station météo",
            mode="markers",
            lat=data_stations["Latitude"],
            lon=data_stations["Longitude"],
            customdata=data_stations.index,
            hoverlabel=dict(bgcolor="black", font=dict(color="white"), namelength=15),
            hovertemplate=[(
                               'station météo: <b>{}</b><br>'
                               'cumul des précipitations téléchargées: {}mm<br>'
                               '<extra></extra>'
                           ).format(info_stations.loc[int(id), "Nom_usuel"],
                                    "" if np.isnan(data_stations.loc[id, "RR1"]) else round(
                                        data_stations.loc[id, "RR1"]))
                           for id in data_stations.index],

            marker=dict(
                size=[0 if (np.isnan(x)) else 20 for x in data_stations.cum_6h],
                color=data_stations['RR1'],
                colorscale='icefire',
                opacity=0.3,
                showscale=True,
                cmin=0,
                cmax=60,
                colorbar=dict(
                    title="Echelle <br>précipitation",  # Titre de la color bar
                    len=0.5,  # Longueur de la barre
                    tickmode="array",
                    tickvals=[0, 5, 20, 50],  # Valeurs spécifiques sur la barre
                    ticktext=['0', '5mm', '20mm', '50mm'],
                    y=0.8,
                    x=0,
                    xanchor="left",
                    yanchor="top",

                ),
            ),
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=0.8)),

            showlegend=True,
            visible=True,

        )

    )

    return fig


def draw_cum_6h_vs_time_for_each_stations(df):
    stations_data = pd.read_csv('app_factory/assets/meteo/info_stations.csv', sep=';', index_col="Id_station")
    if df.index.name == 'id_station': df.reset_index()
    df["name_station"] = df["id_station"].apply(lambda x: stations_data.loc[int(x), "Nom_usuel"])

    fig = px.line(df.sort_values('paris_time'), x="paris_time", y="cum_6h",
                  labels={'cum_6h': ''},
                  color="name_station", facet_col="name_station", facet_col_wrap=3,
                  facet_row_spacing=0.1, height=800,
                  title="Cumul des précipitations sur 6 heures")

    fig.update_layout(
        yaxis=dict(title="mm"),
        xaxis=dict(title="date"),
    )

    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(showlegend=False)

    return fig


def draw_cum_6h_vs_time_for_all_stations(df):
    info_stations = pd.read_csv('app_factory/assets/meteo/info_stations.csv', sep=';', index_col="Id_station")
    if df.index.name == 'id_station': df.reset_index()
    df["name_station"] = df["id_station"].apply(lambda x: info_stations.loc[int(x), "Nom_usuel"])

    fig = px.line(df.sort_values('paris_time'), x="paris_time", y="cum_6h",
                  color="name_station", labels={'name_station': 'station'},
                  # height=200,
                  title="Cumul des précipitations sur 6 heures")

    fig.add_hline(y=50, line_dash="dot",
                  annotation_text="Visite talus",
                  annotation_position="bottom right")

    fig.update_layout(
        yaxis=dict(title="mm"),
        xaxis=dict(title="date"),
    )

    fig.for_each_yaxis(lambda a: a.update(range=[0, 60]))

    return fig
