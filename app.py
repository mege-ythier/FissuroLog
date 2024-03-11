import base64
import sqlite3
from datetime import datetime
import re
import os

import numpy as np
from dash import Dash, html, dcc, Input, Output, callback, State
from dash.exceptions import PreventUpdate
import pandas as pd

from card_module import generate_options_card, generate_map_card, generate_time_series_card, generate_upload_card, fig0, \
    generate_form_card, generate_button_card, generate_message_card
from ingest_module import save_in_database
from ingest_module import parse_file_and_update_ingest_card
from fig_module import create_time_series_fig, create_map

app = Dash(__name__)
server = app.server

# initialisation des données

app.layout = html.Div(
    id='app-container',
    children=[
        html.Header(
            children=[html.Img(src='assets/logo_ratp.png', width='20%', style={'float': 'right'}),
                      html.H1("Fissuro logger")
                      ],
            className="header"),

        html.Div(
            id="app-container-inner",
            children=[

                dcc.Store(id='store-map-csv'),

                html.Div(
                    id='select-data-card', children=[
                        html.Div(
                            id='button_update_fig_card',
                            children=html.Button(id='button_update_fig', hidden=True, title='charger les mesures')),
                        html.Div(
                            id='vertical-card',
                            children=[
                                generate_options_card(),
                                generate_map_card(create_map({})),
                                html.H3(id='fig-message', children="click sur la carte"),
                            ]
                        ),
                        html.Div(id='image-card')]
                ),

                generate_time_series_card(),

                html.Div(
                    id='ingest-card',
                    children=[
                        generate_button_card(),
                        generate_form_card(),
                        generate_upload_card(),
                        generate_message_card()

                    ]
                ),

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


@callback(
    Output('dropdown-line', 'options'),
    Input('dropdown-net', 'value'),
    State('map', 'selectedData'),
    prevent_initial_call=True, interval=10000)
def update_line_in_control_card(net_value, selected_data):
    line_options = []
    if "RER" in net_value:
        line_options += ["A", "B"]
    if "METRO" in net_value:
        line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
    if "TRAM" in net_value:
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
def update_table_in_control_card(line_value, net_value, data_sensors, selected_data):
    df = pd.DataFrame(data_sensors)
    df["Ligne"] = df["Ligne"].astype(str)

    if selected_data is None or (selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
        if len(net_value) > 0 and len(line_value) > 0:
            table_options = df.loc[(df["Reseau"].isin(net_value)) & (df["Ligne"].isin(line_value)), "Table"].unique()
        elif len(net_value) > 0 and len(line_value) == 0:
            table_options = df.loc[(df["Reseau"].isin(net_value)), "Table"].unique()
        else:
            table_options = df["Table"]
        return table_options, None

    elif 'points' in selected_data.keys() and selected_data['points'] != []:

        raise PreventUpdate

    else:
        raise PreventUpdate


@callback(
    Output('dropdown-table', 'options', allow_duplicate=True),
    Input('store-map-csv', 'data'),
    prevent_initial_call=True, interval=10000)
def update_table_options(data_sensors):
    df = pd.DataFrame(data_sensors)
    return df["Table"]


@callback(Output('dropdown-net', 'value'),
          Output('dropdown-line', 'value'),
          Input('map', 'clickData'),
          prevent_initial_call=True, interval=10000
          )
def update_control_card_with_click_on_line_map(click_data):
    route = click_data['points'][0]['customdata']
    net_click_value = None
    line_click_value = None
    # click sur la ligne
    if type(route) == str:
        net_click_value = route.split(" ")[0]
        line_click_value = route.split(" ")[1]
    if type(route) == list:
        raise PreventUpdate
    return [net_click_value], [line_click_value]


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


@callback(Output('button_update_fig', 'hidden'),
          Output('fig-message', 'children', allow_duplicate=True),
          Input('date-picker-select', "start_date"),
          Input('date-picker-select', "end_date"),
          Input('aggregate-choice', 'value'),
          State('dropdown-table', 'value'),
          prevent_initial_call=True, interval=10000)
def show_button(start_date, end_date, aggregate, table_value):
    if table_value:
        return False, "Appuies sur le bouton pour mettre à jour les données"
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
    Output('button_update_fig', 'hidden', allow_duplicate=True),
    Output('fig-message', 'children', allow_duplicate=True),
    Output('image-card', 'children'),
    Output('textarea-model', "value"),
    Output('textarea-num', "value"),
    Output('textarea-zone', "value"),
    Output('textarea-lieu', "value"),
    Output('textarea-pk', "value"),
    Output('textarea-lat', "value"),
    Output('textarea-long', "value"),
    Output('textarea-date-pose', "value"),
    Output('textarea-date-depose', "value"),
    Output('textarea-delta', "value"),
    Output('button-update-metadata', 'hidden'),
    Output('button-delete-table', 'hidden'),
    Input('button_update_fig', 'n_clicks'),
    Input('dropdown-table', 'value'),
    State('date-picker-select', "start_date"),
    State('date-picker-select', "end_date"),
    State('aggregate-choice', 'value'),
    State('store-map-csv', 'data'),
    State('textarea-model', "value"),
    prevent_initial_call=True, interval=10000)
def update_with_table_changes(n_clicks, table_name, start_date, end_date, aggregate, data, model0):
    store = {}
    fig = fig0
    fig_message = "aucune donnée"
    image_card = html.H3("")
    model, num, zone, pk, place, lat, long, date_pose, date_depose, delta = model0, "", "", "", "", "", "", "", "", ""
    button_update_metadata_is_hidden, button_delete_table_is_hidden = True, True

    sensors_df = pd.DataFrame(data)
    sensors_df = sensors_df.set_index("Table")
    if table_name:
        button_update_metadata_is_hidden = False
        button_delete_table_is_hidden = False
        model = sensors_df.loc[table_name, "Modele"]
        num = sensors_df.loc[table_name, "Num"]
        zone = sensors_df.loc[table_name, "Zone"]
        place = sensors_df.loc[table_name, "Lieu"]
        lat = sensors_df.loc[table_name, "Latitude"]
        long = sensors_df.loc[table_name, "Longitude"]
        pk = sensors_df.loc[table_name, "pk"]
        date_pose = sensors_df.loc[table_name, "Date_pose"]
        date_depose = sensors_df.loc[table_name, "Date_depose"]
        delta = sensors_df.loc[table_name, "Ouverture_pose"]

        if not num: num = ""
        if not date_depose: date_depose = ""
        if not pk: pk = ""
        if not delta: delta = ""
        if type(pk) == np.float64 and np.isnan(pk) == True: pk = ""
        if type(delta) == np.float64 and np.isnan(delta) == True: delta = ""

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
            fig = create_time_series_fig(df, table_name, delta)
            fig_message = "données du graphe à jour"

        try:
            images_path = f'data_capteur/images/{table_name}/'
            images_name_file = os.listdir(images_path)
            images_number = [int(x.split(".")[0]) for x in images_name_file]
            image_displayed = f'{images_path}{max(images_number)}.png'

        except FileNotFoundError:
            image_card = html.H3("il n'y a pas encore d'image du capteur dans les données du dashboard"),
        else:
            image_card = html.Img(src=encode_image(image_displayed), width='100%'),

    return (store, fig, True, fig_message,
            image_card, str(model), str(num), zone, place, str(pk), str(lat), str(long), str(date_pose),
            str(date_depose), str(delta),
            button_update_metadata_is_hidden, button_delete_table_is_hidden)


@callback(
    Output('store-data-uploaded', 'data'),
    Output('upload-card-inner', 'children', allow_duplicate=True),
    Output('button-ingest', 'hidden'),
    Output('textarea-model', 'value', allow_duplicate=True),
    Output('ingest-card-message', 'children', allow_duplicate=True),
    Input('upload-file-dcc', 'contents'),
    State('upload-file-dcc', 'filename'), prevent_initial_call=True, interval=10000)
def ingest_first_step(contents, filename):
    return parse_file_and_update_ingest_card(contents, filename)


@callback(
    Output('confirm-throw-ingestion', 'displayed'),
    Output('confirm-throw-ingestion', 'message'),
    Output('store-metadata-to-ingest', 'data'),
    Output('ingest-card-message', 'children', allow_duplicate=True),
    Input('button-ingest', 'n_clicks'),
    State('dropdown-table', 'value'),
    State('dropdown-table', 'options'),
    State('textarea-model', 'value'),
    State('textarea-num', 'value'),
    State('dropdown-net', 'value'),
    State('dropdown-line', 'value'),
    State('textarea-zone', 'value'),
    State('textarea-lieu', 'value'),
    State('textarea-pk', 'value'),
    State('textarea-long', 'value'),
    State('textarea-lat', 'value'),
    State('textarea-date-pose', 'value'),
    State('textarea-date-depose', 'value'),
    State('textarea-delta', 'value'),
    State('store-map-csv', 'data'),

    prevent_initial_call=True, interval=10000)
def ingest_middle_step(click, table_select, tables, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                       date_depose, delta, metadata_stored):
    ingest_card_message = f""
    confirm_message_is_displayed = False
    confirm_message = ""
    table_metadata = None
    if click is None:
        raise PreventUpdate

    if any(len(value) == 0 for value in [net, line]) and not table_select:
        ingest_card_message = "La ligne ou le réseau ne sont pas renseignés dans les menus déroulants"

    elif any(value == "" for value in [zone, model, lat, long]):
        ingest_card_message = "Des élements obligatoires ne sont pas renseignés dans le formulaire"

    # elif not (re.compile(r'^[a-zA-Z\s]+$').match(zone)):
    #     ingest_card_message = "Le nom de la zone est formé de lettres."

    elif not (re.compile(r'^-?\d*\.?\d*$').match(pk) or pk == ""):
        ingest_card_message = f"""Le pk est un chiffre."""

    elif not (re.compile(r'^-?\d*\.?\d*$').match(delta) or delta == ""):
        ingest_card_message = f"""L'ouverture est un chiffre."""

    elif not (re.compile(r'^-?\d*\.?\d*$').match(lat)):
        ingest_card_message = f"""La latitude est un chiffre."""

    elif not (re.compile(r'^-?\d*\.?\d*$').match(long)):
        ingest_card_message = f"""Le longitude est un chiffre."""

    elif not (re.compile(r'^[a-zA-Z0-9]+$').match(num) or num == ""):
        ingest_card_message = "Le numéro du capteur comporte uniquement des lettres ou des chiffres."

    elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_pose)):
        ingest_card_message = "Le date de pose est de la forme 01/01/2024."

    elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_depose) or date_depose == ""):
        ingest_card_message = "Le date de dépose est de la forme 01/01/2024."

    elif any(len(value) > 1 for value in [net, line]):
        ingest_card_message = "Sélectionne une seule ligne!"

    elif table_select:
        # on prendre la valeur du reseau et de la ligne dans le store
        metadata_stored_df = pd.DataFrame(metadata_stored)
        metadata_stored_df.set_index('Table', inplace=True)
        net = metadata_stored_df.loc[table_select, "Reseau"]
        line = metadata_stored_df.loc[table_select, "Ligne"]
        table_metadata = table_select
        confirm_message_is_displayed = True
        confirm_message = f"""
        Les données de ton fichier vont étre intégrées au capteur existant {table_select}.  
        click ok, pour lancer l'intégration.

        click annuler, pour arrêter l'ingestion, puis choisis ou crée le bon capteur.      
"""

    else:
        line = line[0]
        net = net[0]
        net_dict = {"RER": "RER", "METRO": "M", "TRAM": "T"}
        table_created = net_dict[net] + str(int(datetime.today().replace(microsecond=0).timestamp()))
        table_metadata = table_created
        confirm_message_is_displayed = True
        if table_created in tables:
            confirm_message = f"""
Il y a deja un capteur nommé {table_created} dans le dashboard.
Les données de ton fichier vont être intégrées à ce capteur.  
Press OK pour lancer l'ingestion.  
            """
        else:
            # todo: gere l'erreur la table se crée mais pas la ligne dans le csv
            confirm_message = f"""
Les données de ton fichier concernent un nouveau capteur.
Ce capteur s'appelera {table_created}.  
Vérifies bien que ton capteur n'existe pas sous un autre nom.     
Press OK pour lancer l'ingestion.
"""

    metadata = {'Reseau': net, 'Ligne': line, 'Zone': zone, 'Lieu': lieu, 'pk': pk, 'Modele': model,
                'Num': num,
                'Latitude': lat, 'Longitude': long, 'Date_pose': date_pose, 'Date_depose': date_depose,
                'Ouverture_pose': delta, 'Table': table_metadata}

    return confirm_message_is_displayed, confirm_message, metadata, ingest_card_message


@callback(Output('text-error-upload-image', 'children'),
          Input('upload-image-dcc', 'contents'),
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

    Output('store-map-csv', 'data'),
    Output('ingest-card-message', 'children', allow_duplicate=True),
    # Output('upload-file-dcc', 'contents'),
    Output('dropdown-table', 'value', allow_duplicate=True),
    Input('confirm-throw-ingestion', 'submit_n_clicks'),
    State('store-data-uploaded', 'data'),
    State('store-map-csv', 'data'),
    State('store-metadata-to-ingest', 'data'),
    State('upload-image-dcc', 'contents'), interval=10000, prevent_initial_call='initial_duplicate')
def ingest_final_step(click, data, all_metadata, metadata, image_contents):
    image_upload_info = ["aucune image uploadée"]
    # quand on lance l'appli le submit_n_clicks de confirm-throw-ingestion prend la valeur None et donc il y a un call
    if click is None:
        sensors_df = pd.read_csv("data_capteur/map.csv", sep=";")
        return (sensors_df.to_dict('records'),
                ("Dans le bloc du haut, indique la ligne et le réseau de ton nouveau capteur ou sélectionne un "
                 "capteur existant."), None)
    elif metadata == {}:
        raise PreventUpdate
    else:
        table_name = metadata["Table"]
        df = pd.DataFrame(data)

        # sauvegarder les données dans la database
        save_in_database(df, table_name)

        # extraire des infos de la table ingérée
        conn = sqlite3.connect('data_capteur/database.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        table_length = cursor.fetchone()[0]
        conn.close()

        # mise à jour du store
        all_metadata_df = pd.DataFrame(all_metadata)
        # mise a jour du store de metadata
        if table_name in all_metadata_df['Table'].values:
            all_metadata_df.set_index('Table', inplace=True)
            all_metadata_df.loc[table_name, "Modele"] = metadata["Modele"]
            all_metadata_df.loc[table_name, "Num"] = metadata["Num"]
            all_metadata_df.loc[table_name, "Zone"] = metadata["Zone"]
            all_metadata_df.loc[table_name, "Lieu"] = metadata["Lieu"]
            all_metadata_df.loc[table_name, "Latitude"] = metadata["Latitude"]
            all_metadata_df.loc[table_name, "Longitude"] = metadata["Longitude"]
            all_metadata_df.loc[table_name, "pk"] = metadata["Latitude"]
            all_metadata_df.loc[table_name, "Date_pose"] = metadata["Date_pose"]
            all_metadata_df.loc[table_name, "Date_depose"] = metadata["Date_depose"]
            all_metadata_df.loc[table_name, "Ouverture_pose"] = metadata["Ouverture_pose"]
            all_metadata_df.reset_index(inplace=True)
            all_metadata = all_metadata_df.to_dict("records")
        # ajout d'une ligne dans le store
        else:
            all_metadata.append(metadata)

        database_info = ([
            f""" ### Information sur l'ingestion.
Le capteur {table_name} a mesuré {table_length} ouvertures.
"""])

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

        return all_metadata, database_info + image_upload_info, table_name


@callback(

    Output('store-map-csv', 'data', allow_duplicate=True),
    Output('ingest-card-message', 'children', allow_duplicate=True),
    Input('button-update-metadata', 'n_clicks'),
    State('store-map-csv', 'data'),
    State('dropdown-table', 'value'),
    State('textarea-lat', 'value'),
    State('textarea-long', 'value'),
    State('textarea-pk', 'value'),
    State('textarea-delta', 'value'),
    State('textarea-num', 'value'),
    State('textarea-date-pose', 'value'),
    State('textarea-date-depose', 'value'),
    State('upload-image-dcc', 'contents'),
    Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate'

)
def update_sensors_info(click, sensors_data_stored, table_name, lat, long, pk, delta, num, date_pose, date_depose,
                        image_contents):
    if click is None or table_name is None:
        raise PreventUpdate

    sensors_df = pd.DataFrame(sensors_data_stored)
    sensors_df = sensors_df.set_index("Table")

    try:
        if pk == "": pk= np.float64('nan')
        if delta == "": delta=np.float64('nan')
        float(lat), float(long), float(pk), float(delta)

        if date_depose != "":
            datetime.strptime(date_depose, "%d/%m/%Y")

        if image_contents:
            content_format, content_string = image_contents.split(',')
            if content_format != "data:image/png;base64":
                raise ValueError("fichier image invalide")

    except (TypeError, ValueError) as e:
        return sensors_data_stored, f"echec de la mise à jour des données : {e}"

    except ValueError("fichier image invalide") as e:
        return sensors_data_stored, f"echec de la mise à jour des données : {e}"

    else:
        sensors_df.loc[table_name, "Latitude"] = float(lat)
        sensors_df.loc[table_name, "Longitude"] = float(long)
        sensors_df.loc[table_name, "Ouverture_pose"] = delta
        sensors_df.loc[table_name, "Date_pose"] = date_pose
        sensors_df.loc[table_name, "Date_depose"] = date_depose
        sensors_df.loc[table_name, "Num"] = num
        sensors_df.loc[table_name, "pk"] = pk

        sensors_df.reset_index(inplace=True)
        sensors_data_stored = sensors_df.to_dict('records')
        message = "information du capteur mis a jour"
        # ajouter une image
        if image_contents:
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

        return sensors_data_stored, message


@callback(
    Output('confirm-delete-table', 'displayed'),
    Output('confirm-delete-table', 'message'),
    Input('button-delete-table', 'n_clicks'),
    State('dropdown-table', 'value'),
    State('store-map-csv', 'data'),
    prevent_initial_call=True, interval=10000)
def delete_table_first_step(click, table_select, sensors_data):
    if click is None:
        raise PreventUpdate
    elif table_select is None:
        raise PreventUpdate
    else:
        confirm_message = f"""
    Les données du capteurs {table_select} vont être supprimer.         
"""
        return True, confirm_message


@callback(
    Output('store-map-csv', 'data', allow_duplicate=True),
    Output('ingest-card-message', 'children', allow_duplicate=True),
    Output('dropdown-table', 'value', allow_duplicate=True),
    Input('confirm-delete-table', 'submit_n_clicks'),
    State('dropdown-table', 'value'),
    State('store-map-csv', 'data'),
    prevent_initial_call=True, interval=10000)
def delete_table_final_step(click, table_select, sensors_data):
    if click is None:
        raise PreventUpdate
    elif table_select is None:
        raise PreventUpdate
    else:
        sensors_df = pd.DataFrame(sensors_data)
        sensors_df.set_index("Table", inplace=True)
        sensors_df.drop(table_select, inplace=True, axis=0)
        sensors_df.reset_index(inplace=True)

        conn = sqlite3.connect('data_capteur/database.db')
        cursor = conn.cursor()
        cursor.execute(f"""DROP TABLE IF EXISTS {table_select} """)
        conn.commit()

        return sensors_df.to_dict('records'), f'capteur {table_select} supprimé', None


@callback(Output('map', 'figure'),
          Input('store-map-csv', 'data'),
          prevent_initial_call=True)
def update_map(sensors_data):
    sensors_df = pd.DataFrame(sensors_data)
    sensors_df.to_csv("data_capteur/map.csv", index=False, sep=";", header=True, mode="w")
    return create_map(sensors_data)


if __name__ == '__main__':
    app.run(debug=True, port=8051)
    # app.run(debug=True, host='0.0.0.0', port=8051)
    # app.run()
