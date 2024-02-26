import base64
import sqlite3
from datetime import datetime
import re
import os

import numpy
from dash import Dash, html, dcc, Input, Output, callback, State
from dash.exceptions import PreventUpdate
import pandas as pd

from card_module import generate_options_card, generate_map_card, generate_time_series_card, generate_upload_card, fig0, \
    generate_form_card
from ingest_module import save_in_database
from ingest_module import parse_file_and_update_ingest_card
from fig_module import create_time_series_fig, create_map

app = Dash(__name__, suppress_callback_exceptions=True, prevent_initial_callbacks=True)
server = app.server

# initialisation des données
sensors_df0 = pd.read_csv("data_capteur/map.csv", sep=";")
sensors_df0["Date_debut"] = pd.to_datetime(sensors_df0["Date_debut"], format='mixed', dayfirst=True)
sensors_df0["Date_fin"] = pd.to_datetime(sensors_df0["Date_fin"], format='mixed', dayfirst=True)
map0 = create_map(sensors_df0.to_dict('records'))

app.layout = html.Div(
    id='app-container',
    children=[
        html.Header(
            children=[html.Img(src='assets/logo_ratp.png', width='30%', style={'float': 'right'}),
                      html.H1("Fissuro logger")
                      ],
            className="header"),

        html.Div(
            id="app-container-inner",
            children=[

                dcc.Store(id='store-map-csv', data=sensors_df0.to_dict("records")),

                html.Div(
                    id='select-data-card', children=[
                        html.Div(
                            id='vertical-card',
                            children=[
                                generate_options_card(sensors_df0.to_dict("records")),
                                generate_map_card(map0),
                            ]
                        ),
                        html.Div(id='image-card')]
                ),

                generate_time_series_card(),

                dcc.Markdown(
                    id='markdown-message',
                    children="# Bienvenue",
                ),

                html.Div(
                    id='ingest-card',
                    children=[
                        generate_upload_card(),
                        generate_form_card(),
                        html.Div(id="button-card")

                    ]
                ),

                html.Div(id='ingest-info'),
                dcc.ConfirmDialog(
                    id='confirm-throw-ingestion',
                    message='attention'
                ),

                dcc.ConfirmDialog(
                    id='confirm-read-message',
                    message='attention'
                ),
                # html.Button('dev-test', id='button-test'),
                # dcc.Upload(
                #     id='upload-image-test',
                #     children="test télécharge une image de ton capteur",
                #     style={ 'width': '30%'},
                #     multiple=False
                # ),

            ]
        )
    ]
)


@callback(
    Output('dropdown-line', 'options'),
    Input('dropdown-net', 'value'),
    State('map', 'selectedData'),
    prevent_initial_call=True, interval=10000)
def update_line_in_control_card(net_value, selected_data):
    line_options = []
    if "RER" in net_value:
        line_options += ["A", "B"]
    if "M" in net_value:
        line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
    if "T" in net_value:
        line_options += ["1", "2", "3,""4", "5", "6", "7", "8", "9", "10"]

    if selected_data is None or (selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
        return line_options
    else:
        raise PreventUpdate


@callback(
    Output('dropdown-table', 'options'),
    Output('dropdown-table', 'value', allow_duplicate=True),
    Input('dropdown-line', 'value'),
    Input('dropdown-net', 'value'),
    State('store-map-csv', 'data'),
    State('map', 'selectedData'),
    prevent_initial_call=True, interval=10000)
def update_table_in_control_card(line_value, net_value, dict, selected_data):
    df = pd.DataFrame(dict)
    df["Ligne"] = df["Ligne"].astype(str)

    if selected_data is None or (selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
        if len(net_value) > 0 and len(line_value) > 0:
            return df.loc[(df["Reseau"].isin(net_value)) & (df["Ligne"].isin(line_value)), "Table"].unique(), None
        elif len(net_value) > 0 and len(line_value) == 0:
            return df.loc[(df["Reseau"].isin(net_value)), "Table"].unique(), None
        else:
            return df["Table"], None

    elif 'points' in selected_data.keys() and selected_data['points'] != []:
        raise PreventUpdate

    else:
        raise PreventUpdate


@callback(Output('dropdown-net', 'value'),
          Output('dropdown-line', 'value'),
          Input('map', 'clickData'),
          prevent_initial_call=True, interval=10000
          )
def update_control_card_with_click_on_line_map(click_data):
    custom_data = click_data['points'][0]['customdata']
    net_click_value = None
    line_click_value = None
    # click sur la ligne
    if type(custom_data) == str:
        if custom_data[0] == "R":
            net_click_value = ["RER"]
            line_click_value = [custom_data[3:]]
        else:
            net_click_value = [custom_data[0]]
            line_click_value = [custom_data[1:]]
    if type(custom_data) == list:
        raise PreventUpdate
    return net_click_value, line_click_value


@callback(Output('dropdown-net', 'value', allow_duplicate=True),
          Output('dropdown-line', 'value', allow_duplicate=True),
          Output('dropdown-table', 'value', allow_duplicate=True),
          Output('dropdown-table', 'options', allow_duplicate=True),
          Input('map', 'clickData'),
          prevent_initial_call=True, interval=10000
          )
def update_control_card_with_click_on_point_map(click_data):
    custom_data = click_data['points'][0]['customdata']
    table_click_value = None
    if type(custom_data) == list:
        net_click_value = [custom_data[1]]
        line_click_value = [custom_data[2]]
        table_click_value = custom_data[0]
        return net_click_value, line_click_value, table_click_value, [table_click_value]
    if type(custom_data) == str:
        raise PreventUpdate


@callback(Output('button_update_fig', 'disabled'),
          Output('button_update_fig', 'style'),
          Output('markdown-message', 'children', allow_duplicate=True),
          Input('date-picker-select', "start_date"),
          Input('date-picker-select', "end_date"),
          Input('aggregate-choice', 'value'),
          State('dropdown-table', 'value'),
          prevent_initial_call=True, interval=10000)
def show_button(start_date, end_date, aggregate, table_value):
    if table_value is not None:
        return False, {'background-color': 'rgb(10, 0, 130)'}, "Appuies sur le bouton pour mettre à jour les donnes"
    else:
        raise PreventUpdate


def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print("erreur")
    else:
        return f"data:image/png;base64,{encoded_string}"


@callback(
    Output('store-time-serie', 'data'),
    Output('graph-time-series', 'figure'),
    Output('button_update_fig', 'disabled', allow_duplicate=True),
    Output('button_update_fig', 'style', allow_duplicate=True),
    Output('markdown-message', 'children', allow_duplicate=True),
    Output('image-card', 'children'),
    Output('textarea-sensor-num', "value"),
    Output('textarea-zone', "value"),
    Output('textarea-lieu', "value"),
    Output('textarea-pk', "value"),
    Output('textarea-lat', "value"),
    Output('textarea-long', "value"),
    Output('button-show-metadata', 'hidden'),
    # Output('form-card', 'hidden', allow_duplicate=True),
    Input('button_update_fig', 'n_clicks'),
    Input('dropdown-table', 'value'),
    State('date-picker-select', "start_date"),
    State('date-picker-select', "end_date"),
    State('aggregate-choice', 'value'),
    State('store-map-csv', 'data'),
    prevent_initial_call=True, interval=10000)
def main_callback(n_clicks, table_name, start_date, end_date, aggregate, data):
    store = {}
    fig = fig0
    fig_message = "aucune donnée"
    image_card = html.P("")
    sensor_num, zone, pk, place, lat, long = "", "", "", "", "", ""
    button_show_metadata_is_hidden = True
    sensors_df = pd.DataFrame(data)
    sensors_df = sensors_df.set_index("Table")
    if table_name:
        button_show_metadata_is_hidden = False
        sensor_num = sensors_df.loc[table_name, "Num"]
        zone = sensors_df.loc[table_name, "Zone"]
        place = sensors_df.loc[table_name, "Lieu"]
        lat = sensors_df.loc[table_name, "Latitude"]
        long = sensors_df.loc[table_name, "Longitude"]
        delta_mm = sensors_df.loc[table_name, "Ouverture_debut"]
        pk = sensors_df.loc[table_name, "pk"]
        # if numpy.isnan(pk): pk = ""

        start_date_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        end_date_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()
        conn = sqlite3.connect('data_capteur/database.db')
        query = f"""
        SELECT strftime('%Y-%m-%d %H:%M:%S', datetime(unix,'unixepoch')) AS Date,mm,°C
        FROM {table_name}
        WHERE  unix > {start_date_timestamp} and unix < {end_date_timestamp}
        """
        if aggregate == "oui":
            query = f"""
                SELECT  strftime('%Y-%m-%d %H:00:00', datetime(unix,'unixepoch')) AS Date ,mm,°C
                FROM {table_name}
                WHERE unix > {start_date_timestamp} and unix < {end_date_timestamp}
                GROUP BY Date
                ORDER BY Date
            """

        df = pd.read_sql_query(query, conn)
        df = df.set_index('Date')
        df.index.name = "Date"
        size_on_memory = df.memory_usage(index=True, deep=False).sum()
        if size_on_memory > 200000:
            fig_message = "données trop volumineuses pour être affichées, modifier les options"

        if size_on_memory <= 200000:
            store = df.to_dict('records')
            fig = create_time_series_fig(df, table_name, delta_mm)
            fig_message = "données du graphe à jour"

        try:
            images_path = f'data_capteur/images/{table_name}/'
            images_name_file = os.listdir(images_path)
            images_number = [int(x.split(".")[0]) for x in images_name_file]
            image_displayed = f'{images_path}{max(images_number)}.png'

        except FileNotFoundError:
            image_card = html.P("il n'y a pas encore d'image du capteur dans les données du dashboard"),
        else:
            image_card = html.Img(src=encode_image(image_displayed), width='100%'),

    return (store, fig, True, {'background-color': 'rgb(0, 170, 145)'}, fig_message,
            image_card, str(sensor_num), zone, place, str(pk), str(lat), str(long),
            button_show_metadata_is_hidden)  # , form_card_is_hidden)


@callback(
    Output('store-data-uploaded', 'data'),
    Output('upload-card-inner', 'children', allow_duplicate=True),
    Output('button-card', 'children'),
    Output('textarea-sensor-model', 'value'),
    Output('form-card', 'hidden', allow_duplicate=True),
    Output('markdown-message', 'children', allow_duplicate=True),
    Input('upload-file', 'contents'),
    State('upload-file', 'filename'), prevent_initial_call=True, interval=10000)
def ingest_first_step(contents, filename):
    return parse_file_and_update_ingest_card(contents, filename)


@callback(

    Output('confirm-throw-ingestion', 'displayed'),
    Output('confirm-throw-ingestion', 'message'),
    Output('store-metadata-to-ingest', 'data'),
    Output('markdown-message', 'children', allow_duplicate=True),
    Input('button-ingest', 'n_clicks'),
    State('dropdown-table', 'value'),
    State('dropdown-table', 'options'),
    State('textarea-sensor-model', 'value'),
    State('textarea-sensor-num', 'value'),
    State('dropdown-net', 'value'),
    State('dropdown-line', 'value'),
    State('textarea-zone', 'value'),
    State('textarea-lieu', 'value'),
    State('textarea-pk', 'value'),
    State('textarea-long', 'value'),
    State('textarea-lat', 'value'),
    State('textarea-date-pose', 'value'),
    State('textarea-date-depose', 'value'),
    prevent_initial_call=True, interval=10000)
def ingest_middle_step(click, table_select, tables, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                       date_depose):

    if click is None:
        raise PreventUpdate

    elif table_select is not None:
        confirm_message = f"""
        Les données de ton fichier vont étre intégrées au capteur {table_select}.  
        Si oui,click ok
        Si non, click annuler puis décoche la table dans les options        
"""
        return True, confirm_message, {"Table": table_select}, confirm_message

    elif any(value is None for value in [net, line, zone, model, num, lat, long]):
        confirm_message = "Des élements ne sont pas renseignés"
        return False, "", None, confirm_message

    elif any(len(value) == 0 for value in [net, line]):
        confirm_message = "La ligne ou le réseau ne sont pas renseignés"
        return False, "", None, confirm_message

    elif not (re.compile(r'^[a-zA-Z]+$').match(zone)):
        confirm_message = "Le nom de la zone est formé de lettres."
        return False, "", None, confirm_message
    # todo : autoriser les valeurs vides
    elif not (re.compile(r'^[a-zA-Z0-9]+$').match(lieu)):
        confirm_message = "La précision de la zone comporte uniquement des lettres ou des chiffres."
        return False, "", None, confirm_message

    elif not (re.compile(r'^-?\d*\.?\d*$').match(pk)):
        confirm_message = f"""Le pk est un chiffre."""
        return False, "", None, confirm_message

    elif not (re.compile(r'^[a-zA-Z0-9]+$').match(num)):
        confirm_message = "Le numéro du capteur comporte uniquement des lettres ou des chiffres."
        return False, "", None, confirm_message

    elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_pose)):
        confirm_message = "Le date de pose est de la forme 01/01/2024."
        return False, "", None, confirm_message

    elif any(len(value) > 1 for value in [net, line]):
        confirm_message = "Sélectionne une seule ligne!"
        return False, "", None, confirm_message

    else:
        line = line[0]
        net = net[0]
        # a voir
        zone_name = "_".join(name for name in [zone, lieu] if name)
        # table_created = net + line + "_" + zone_name + "_" + num

        date_pose_timestamp = datetime.strptime(date_pose, "%d/%m/%Y").timestamp()
        # todo prendre le timestamp de la journee
        table_created = net + line + "_" + num + "_" + str(int(date_pose_timestamp))

        if table_created in tables:
            confirm_message = f"""
            Il y a deja un capteur nommé {table_created} dans le dashboard.
            Les données de ton fichier vont être intégrées à ce capteur ?
            """

        else:
            tables_formatted = ""
            for table in tables:
                tables_formatted += f"\n-{table}"

            confirm_message = f"""
Voici la liste des capteurs existants de la ligne: {tables_formatted}.  
Les données de ton fichier concernent un nouveau capteur. Ce capteur est nommé {table_created}.  
Vérifies bien que ton capteur n'existe pas dans la liste.  
Si oui presses sur ANNULER puis choisis le capteur existant dans le menu déroulant. 
Si non, presses sur OK pour lancer l'ingestion.
"""

        metadata = {'Reseau': net, 'Ligne': line, 'Zone': zone, 'Lieu': lieu, 'pk': pk, 'Modele': model,
                    'Num': num,
                    'Latitude': lat, 'Longitude': long, 'Date_debut': '06/01/1900', 'Date_fin': '06/01/2030',
                    'Ouverture_debut': 0, 'Table': table_created}

        return True, confirm_message, metadata, confirm_message


@callback(Output('text-error-upload-image', 'children'),
          Input('upload-image', 'contents'),
          )
def show_message_upload_image(contents):
    try:
        content_format, content_string = contents.split(',')

        if content_format != "data:image/png;base64":
            return 'télécharge une image png'
        decoded = base64.b64decode(content_string)
        if len(decoded) > 4000000:
            return 'télécharge une image de taille inférieure à 5Mo'
        else:
            return "image prête pour l'ingestion"
    except AttributeError:
        return "aucune image téléchargée"


@callback(
    Output('markdown-message', 'children'),
    Output('store-map-csv', 'data'),
    Output('form-card', 'hidden'),
    Output('ingest-card', 'children'),
    Input('confirm-throw-ingestion', 'submit_n_clicks'),
    State('store-data-uploaded', 'data'),
    State('store-map-csv', 'data'),
    State('store-metadata-to-ingest', 'data'),
    State('upload-image', 'contents'),
    Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate')
def ingest_final_step(click, data, all_metadata, metadata, image_contents):
    image_upload_info = ["aucune image uploadée"]
    # quand on lance l'appli le submit_n_clicks de confirm-throw-ingestion prend la valeur None et donc il y a un call
    if any(value is None for value in [click, data, metadata]):
        raise PreventUpdate()

    table_name = metadata["Table"]
    # todo: est ce qu'on garde la route dans le nom de la table?
    route = table_name.split("_")[0]

    df = pd.DataFrame(data)

    # extraire la liste des capteurs de la route avant l'ingestion
    conn = sqlite3.connect('data_capteur/database.db')
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT name
    FROM sqlite_master
    WHERE type='table' AND name like '{route}%';""")
    tables_name = cursor.fetchall()
    tables_name = [x[0] for x in tables_name]
    conn.close()

    # sauvegarder les données dans la database
    save_in_database(df, table_name)

    # extraire des infos de la table ingérée
    conn = sqlite3.connect('data_capteur/database.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    table_length = cursor.fetchone()[0]
    # cursor.execute(f"PRAGMA table_info({table_name})")
    # columns_info = cursor.fetchall()
    conn.close()

    if not table_name in tables_name:
        tables_name.append(table_name)
        all_metadata.append(metadata)

    database_info = (
            [f""" ### Information sur l'ingestion.
{table_length} mesures sont associées au capteur {table_name}.  
La liste des capteurs de la ligne {route} est :"""] + [f"- {table}\n" for table in tables_name]
    )

    try:
        content_format, content_string = image_contents.split(',')
        if content_format != "data:image/png;base64":
            raise ValueError("Erreur : le fichier n'est pas une image au format png")
        decoded = base64.b64decode(content_string)
        images_path = f"data_capteur/images/{table_name}"
        if table_name not in os.listdir("data_capteur/images"): os.makedirs(images_path)

        images_name_file = os.listdir(images_path)
        images_number = [int(x.split(".")[0]) for x in images_name_file]
        image_number = 1
        if len(images_name_file) > 0:
            image_number = max(images_number) + 1
    except (AttributeError, ValueError):
        image_upload_info = ["echec de l'intégration de l'image"]
    else:
        with open(f'{images_path}/{image_number}.png', 'wb') as f:
            f.write(decoded)
        image_upload_info = ["succes de l'intégration de l'image"]

    return database_info + image_upload_info, all_metadata, False, [generate_upload_card(), generate_form_card(),
                                                                    html.Div(id="button-card")]


@callback(Output('form-card', 'hidden', allow_duplicate=True),
          Output('button-card', 'children', allow_duplicate=True),
          Output('upload-card-inner', 'children', allow_duplicate=True),
          Output('markdown-message', 'children', allow_duplicate=True),
          Input('button-show-metadata', 'n_clicks'),
          Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate')
def show_form_card(click):
    if click is None: raise PreventUpdate
    return (False,
            html.Button('modifier les informations du capteur', id='button-update-metadata'),
            html.Div(""),
            "Tu peux changer les valeurs d'un capteur existant")


@callback(
    Output('markdown-message', 'children', allow_duplicate=True),
    Output('store-map-csv', 'data', allow_duplicate=True),
    Input('button-update-metadata', 'n_clicks'),
    State('store-map-csv', 'data'),
    State('dropdown-table', 'value'),
    State('textarea-lat', 'value'),
    State('textarea-long', 'value'),
    State('textarea-pk', 'value'),
    State('textarea-delta', 'value'),
    State('upload-image', 'contents'),

    Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate'
    # Prevent_initial_call=True, interval=10000
)
def update_sensors_info(click, sensors_data_stored, table_name, lat, long, pk, delta,image_contents):
    if click is None or table_name is None:
        raise PreventUpdate

    sensors_df = pd.DataFrame(sensors_data_stored)
    sensors_df = sensors_df.set_index("Table")

    try:
        if pk != "": float(pk)
        float(lat), float(long), float(delta)

        if image_contents:
            content_format, content_string = image_contents.split(',')
            if content_format != "data:image/png;base64":
                raise ValueError("fichier image invalide")

    except (TypeError, ValueError) as e:
        return f"echec de la mise à jour des données : {e}", sensors_data_stored

    except ValueError("fichier image invalide") as e:
        return f"echec de la mise à jour des données : {e}", sensors_data_stored

    else:
        sensors_df.loc[table_name, "Latitude"] = float(lat)
        sensors_df.loc[table_name, "Longitude"] = float(long)
        sensors_df.loc[table_name, "Ouverture_debut"] = float(delta)
        if pk == "":
            sensors_df.loc[table_name, "pk"] = ""
        else:
            sensors_df.loc[table_name, "pk"] = float(pk)

        sensors_df.reset_index(inplace=True)
        sensors_data_stored = sensors_df.to_dict('records')
        message= "information du capteur mis a jour"
        #ajouter une image
        if image_contents :
            content_format, content_string = image_contents.split(',')
            decoded = base64.b64decode(content_string)
            images_path = f"data_capteur/images/{table_name}"
            if table_name not in os.listdir("data_capteur/images"): os.makedirs(images_path)
            images_name_file = os.listdir(images_path)
            images_number = [int(x.split(".")[0]) for x in images_name_file]
            image_number = 1
            if len(images_name_file) > 0: image_number = max(images_number) + 1
            with open(f'{images_path}/{image_number}.png', 'wb') as f:
                f.write(decoded)
            message = "information du capteur mis a jour et ingestion d'une nouvelle image"

        return message, sensors_data_stored






@callback(Output('map', 'figure'),
          Input('store-map-csv', 'data'))
def update_map(sensors_dict):
    sensors_df = pd.DataFrame(sensors_dict)
    sensors_df.to_csv("data_capteur/map.csv", index=False, sep=";", header=True, mode="w")
    return create_map(sensors_dict)


# @app.callback(
#     Output('image-card', 'children', allow_duplicate=True),
#     Input('button-test', 'n_clicks'),
#     State('dropdown-table', 'value'),
#     prevent_initial_call=True)
# def test(click, table_name):
#     if table_name not in os.listdir("data_capteur/images"):
#         os.makedirs(f"data_capteur/images/{table_name}")
#     return html.P(f"data_capteur/images/{table_name}")


if __name__ == '__main__':
    app.run(debug=True, port=8051)
    # app.run(debug=True, host='0.0.0.0', port=8051)
