import base64
import time
from datetime import datetime
import re

import numpy as np
from dash import html, Input, Output, State, dcc
from dash.exceptions import PreventUpdate
import pandas as pd

from flask_login import current_user
from sqlalchemy import text, desc, MetaData

from app_factory.models import SensorInfo
from app_factory.utils.card import fig0, left_column, right_column
from app_factory.utils.ingest import parse_file_and_update_ingest_card, save_image_in_database, \
    save_new_sensors_info, save_old_sensors_info
from app_factory.utils.fig import create_map, query_time_series_data_and_create_fig
from app_factory import db, metadata

import logging.config

logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)


def register_callbacks(dash_app):
    @dash_app.callback(
        Output('store-map-csv', 'data'),
        Output('welcome-info', 'children'),
        Input('url', 'pathname'), prevent_initial_call=True)
    def welcome(url):
        if current_user.is_authenticated:
            sensors_dtype = {'Id': str, 'Num': str, 'Modele': str, 'Reseau': str, 'Ligne': str, 'Zone': str,
                             'Lieu': str, 'pk': np.float64, 'Latitude': np.float64, 'Longitude': np.float64,
                             'Date_pose': 'datetime64[ns]', 'Date_depose': 'datetime64[ns]',
                             'Ouverture_pose': np.float64}

            sensors_df = pd.read_sql('select * from sensors_info_tb', con=db.engine, dtype=sensors_dtype)

            sensors_df["Date_pose"] = sensors_df['Date_pose'].dt.strftime('%d/%m/%Y')
            sensors_df["Date_depose"] = sensors_df['Date_depose'].dt.strftime('%d/%m/%Y')

            mylogger.info(f"{current_user.email} ouvre l'application")

            return sensors_df.to_dict('records'), f'Bienvenue {current_user.email}'
        else:

            return [], "pas d'authentification"

    @dash_app.callback(
        Output('map', 'figure'),
        Input('store-map-csv', 'data'),
        State('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def update_map(sensors_json, selected_data):
        selected_point_index = -1

        if selected_data and 'points' in selected_data.keys() and selected_data['points'] != []:
            # premier point selectionné,id est la premiere valeur
            selected_sensor_id = selected_data['points'][0]['customdata'][0]
            sensors_df = pd.DataFrame(sensors_json)
            if sensors_df.shape[0] > 0:
                index = sensors_df.loc[sensors_df.Id == selected_sensor_id].index
                selected_point_index = -1 if len(index) == 0 else index[0]

        return create_map(sensors_json, selected_point_index)

    @dash_app.callback(
        Output('dropdown-line', 'options'),
        Input('dropdown-net', 'value'),
        prevent_initial_call=True, interval=10000)
    def update_line_options(net_value):
        line_options = []
        if "RER" in net_value:
            line_options += ["A", "B"]
        if "METRO" in net_value:
            line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
        if "TRAM" in net_value:
            line_options += ["1", "2", "3,""4", "5", "6", "7", "8", "9", "10"]
        return line_options

    @dash_app.callback(Output('button_update_fig', 'hidden'),
                       Output('fig-message', 'children', allow_duplicate=True),
                       Input('date-picker-select', "start_date"),
                       Input('date-picker-select', "end_date"),
                       Input('aggregate-choice', 'value'),
                       State('dropdown-table', 'value'),
                       prevent_initial_call=True, interval=10000)
    def show_update_button(start_date, end_date, aggregate, table_value):
        if table_value:
            return False, "Appuies sur le bouton pour mettre à jour le graphique."
        else:
            raise PreventUpdate

    @dash_app.callback(
        Output('image-card', 'hidden'),
        Input('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def show_image(selected_data):
        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            return True
        else:
            return False

    @dash_app.callback(
        Output('time-series', 'figure', allow_duplicate=True),
        Output('button_update_fig', 'hidden', allow_duplicate=True),
        Output('upload-image1-dcc', 'children'),
        Output('upload-image2-dcc', 'children'),
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
        Output('textarea-divers', "value"),
        Output('dropdown-net', "value"),
        Output('dropdown-line', "value"),
        Output('dropdown-table', "value"),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('image-message', 'children'),
        Output('ingest-message', 'children'),
        Input('button_update_fig', 'n_clicks'),
        Input('map', 'selectedData'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('store-map-csv', 'data'),
        Input('map', 'clickData'),

        prevent_initial_call=True, interval=10000)
    def update_with_click_on_map(n_click, selected_data, start_date, end_date, aggregate, data, click_data):

        fig = fig0
        fig_message = ("Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                       " Tu peux aussi ajouter un nouveau capteur.")
        image_message = ""
        ingest_message = ""

        image1 = ''
        image2 = ''

        model, num, zone, pk, place = "", "", "", "", ""
        lat, long = "", "",
        date_pose, date_depose = "", ""
        delta, divers = "", ""
        net, line = "", ""
        sensor_id = ""

        sensors_df = pd.DataFrame(data)

        # aucun point selectionné
        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):

            if click_data and 'points' in click_data.keys() and type(
                    click_data['points'][0]['customdata']) == str:
                route = click_data['points'][0]['customdata']
                net = route.split(" ")[0]
                line = route.split(" ")[1]
                fig_message = "Click sur un point"


        else:
            # premier 0 car on prend seulement le premier point selectionné
            sensor_id = selected_data['points'][0]['customdata'][0]
            sensors_df = sensors_df.set_index("Id")

            model = sensors_df.loc[sensor_id, "Modele"]
            num = sensors_df.loc[sensor_id, "Num"]
            zone = sensors_df.loc[sensor_id, "Zone"]
            place = sensors_df.loc[sensor_id, "Lieu"]
            lat = sensors_df.loc[sensor_id, "Latitude"]
            long = sensors_df.loc[sensor_id, "Longitude"]
            pk = sensors_df.loc[sensor_id, "pk"]
            date_pose = sensors_df.loc[sensor_id, "Date_pose"]
            date_depose = sensors_df.loc[sensor_id, "Date_depose"]
            delta = sensors_df.loc[sensor_id, "Ouverture_pose"]
            divers = sensors_df.loc[sensor_id, "Divers"]
            net = sensors_df.loc[sensor_id, "Reseau"]
            line = sensors_df.loc[sensor_id, "Ligne"]

            if date_depose is None: date_depose = ""
            if pk is None: pk = ""
            if delta is None: delta = ""

            fig, fig_message = query_time_series_data_and_create_fig(db, sensor_id, start_date, end_date, aggregate,
                                                                     delta)

            def image(i):

                try:
                    query = f"""
                                SELECT data
                                FROM sensors_image_tb
                                WHERE sensor_id ='{sensor_id}' AND card_id={i}
                                ORDER BY id DESC
                                LIMIT 1
                                """
                    image1_from_database = db.session.execute(text(query)).scalar()
                    image1_encoded = base64.b64encode(image1_from_database).decode('utf-8')

                except:
                    if current_user.role == 'owner':
                        return html.Div("Click pour ajouter une image")

                else:
                    # a voir png, cherher le format
                    return html.Img(src=f"data:image/png;base64,{image1_encoded}")

            image1 = image(1)
            image2 = image(2)

        return (fig, True, image1, image2, model, num, zone, place, str(pk), str(lat), str(long),
                str(date_pose), str(date_depose), str(delta), divers, net, line, str(sensor_id),
                fig_message, image_message, ingest_message)


def register_owner_callbacks(dash_app):
    @dash_app.callback(
        Output('button-update-metadata', 'hidden'),
        Output('button-delete-table', 'hidden'),
        Input('map', 'selectedData'),
        prevent_initial_call=True, interval=10000)
    def show_button(selected_data):
        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            return True, True
        else:
            return False, False

    @dash_app.callback(
        Output('store-data-uploaded', 'data'),
        Output('upload-file-inner-card', 'children', allow_duplicate=True),
        Output('button-ingest', 'hidden'),
        Output('textarea-model', 'value', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Input('upload-file-dcc', 'contents'),
        State('upload-file-dcc', 'filename'), prevent_initial_call=True, interval=10000)
    def ingest_first_step(contents, filename):
        return parse_file_and_update_ingest_card(contents, filename)

    @dash_app.callback(
        Output('confirm-throw-ingestion', 'displayed'),
        Output('confirm-throw-ingestion', 'message'),
        Output('store-metadata-to-ingest', 'data'),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('upload-file-inner-card', 'children'),
        Input('button-ingest', 'n_clicks'),
        State('dropdown-table', 'value'),
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
        State('textarea-divers', 'value'),

        prevent_initial_call=True, interval=10000)
    def ingest_middle_step(click, selected_sensor, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                           date_depose, delta, divers):
        ingest_sensor = ""
        ingest_card_message = f""
        confirm_message_is_displayed = False
        confirm_message = ""
        sensor_dict = {}

        if click is None:
            raise PreventUpdate

        elif any(len(value) == 0 for value in [net, line]) and not selected_sensor:
            ingest_card_message = "ECHEC : La ligne ou le réseau ne sont pas renseignés dans les menus déroulants"

        elif any(value == "" for value in [zone, model, lat, long]):
            ingest_card_message = "ECHEC : Des élements obligatoires ne sont pas renseignés dans le formulaire"

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
            ingest_card_message = "ECHEC : Le numéro du capteur comporte uniquement des lettres ou des chiffres."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_pose)):
            ingest_card_message = "ECHEC : Le date de pose est de la forme 01/01/2024."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_depose) or date_depose == ""):
            ingest_card_message = "ECHEC : Le date de dépose est de la forme 01/01/2024."

        elif type(net) == list and len(net) > 1:
            ingest_card_message = "ECHEC : Sélectionne une seul reseau!"

        elif type(line) == list and len(line) > 1:
            ingest_card_message = "ECHEC : Sélectionne une seule ligne!"

        else:
            if selected_sensor:
                ingest_sensor = selected_sensor
                confirm_message_is_displayed = True
                confirm_message = f"""
                Les données de ton fichier vont étre intégrées au capteur existant F{selected_sensor}.  
                click ok, pour lancer l'intégration.
        
                click annuler, pour arrêter l'ingestion, puis choisis ou crée le bon capteur.      
        """

            else:
                query = db.select(SensorInfo.Id).order_by(desc(SensorInfo.Id))
                last_sensor_number = db.session.execute(query).scalar()
                created_sensor_number = last_sensor_number + 1 if last_sensor_number else 1
                ingest_sensor = created_sensor_number

                confirm_message_is_displayed = True

                confirm_message = f"""
        Les données de ton fichier concernent un NOUVEAU capteur.
        Elles sont sauvegardées dans la table F{created_sensor_number}.  
        Vérifies bien que ton capteur n'existe pas sous un autre nom.     
        Press OK pour lancer l'ingestion.
        """

            sensor_dict = {'Id': ingest_sensor, 'Num': num, 'Modele': model,
                           'Reseau': net[0] if type(net) == list else net,
                           'Ligne': line[0] if type(line) == list else line,
                           'Zone': zone, 'Lieu': lieu,
                           'pk': None if pk == '' else float(pk),
                           'Latitude': float(lat), 'Longitude': float(long), 'Date_pose': date_pose,
                           'Date_depose': date_depose,
                           'Ouverture_pose': None if delta == '' else float(delta),
                           'Divers': divers}

        return confirm_message_is_displayed, confirm_message, sensor_dict, ingest_card_message, ""

    @dash_app.callback(

        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Output('time-series', 'figure', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('map', 'selectedData'),
        Output('button-ingest', 'hidden', allow_duplicate=True),
        Input('confirm-throw-ingestion', 'submit_n_clicks'),
        State('store-data-uploaded', 'data'),
        State('store-map-csv', 'data'),
        State('store-metadata-to-ingest', 'data'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        interval=10000, prevent_initial_call='initial_duplicate')
    def ingest_final_step(click, data, sensors_json, new_sensor_dict, start_date, end_date, aggregate):

        if click is None or new_sensor_dict == {}:
            raise PreventUpdate

        else:
            sensor_id = new_sensor_dict["Id"]
            sensor_table = "F" + str(sensor_id)
            df = pd.DataFrame(data)

            def create_table(sensor_name):
                class Measure(db.Model):
                    __tablename__ = sensor_name
                    unix = db.Column(db.Integer, primary_key=True)
                    mm = db.Column(db.Float)
                    celsius = db.Column(db.Float)

                db.create_all()

            create_table(sensor_table)
            db.session.commit()

            table_length_before = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_table};")).scalar()
            for index, row in df.iterrows():
                parameters = {'unix': row['unix'], 'mm': row['mm'], 'celsius': row['celsius']}

                if db.engine.name == 'sqlite':
                    query = text(
                        f"INSERT OR IGNORE INTO {sensor_table} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)")
                if db.engine.name == 'mysql':
                    query = text(f"INSERT IGNORE INTO {sensor_table} (unix, mm, celsius) VALUES (:unix, :mm, :celsius)")
                db.session.execute(query, parameters)

            db.session.commit()
            table_length_after = db.session.execute(text(f"SELECT COUNT(*) FROM {sensor_table};")).scalar()
            table_length = table_length_after - table_length_before
            database_info = (
                [f" # Information sur l'ingestion : le capteur {sensor_table} a {table_length} nouvelles mesures."])

            sensors_df = pd.DataFrame(data=sensors_json)
            if 'Id' in sensors_df.columns and sensor_id in sensors_df['Id'].values:
                sensors_json = save_old_sensors_info(db, sensors_json, new_sensor_dict)
            else:
                sensors_json = save_new_sensors_info(db, sensors_json, new_sensor_dict)

            fig, fig_message = query_time_series_data_and_create_fig(db, sensor_id, start_date, end_date, aggregate,
                                                                     new_sensor_dict["Ouverture_pose"])

            selected_data = {'points': [{'customdata': [sensor_id]}]}

            mylogger.info(f"{current_user.email} crée le fissuromètre {new_sensor_dict}")

            return sensors_json, database_info, str(sensor_id), fig, fig_message, selected_data, True

    @dash_app.callback(

        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
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
        State('textarea-lieu', 'value'),
        State('textarea-zone', 'value'),
        State('textarea-divers', 'value'),
        State('textarea-model', 'value'),
        State('dropdown-net', 'value'),
        State('dropdown-line', 'value'),
        Prevent_initial_call=True, interval=10000, prevent_initial_call='initial_duplicate'

    )
    def update_sensors_info(click, sensors_json, sensor_id, lat, long, pk, delta, num, date_pose, date_depose,
                            lieu, zone, divers, model, net, line):
        if click is None or sensor_id is None:
            raise PreventUpdate

        # validation des données du formulaire
        try:
            lat = float(lat)
            long = float(long)
            pk = None if pk == "" else float(pk)
            delta = None if delta == "" else float(delta)

            if date_depose != "":
                datetime.strptime(date_depose, "%d/%m/%Y")

        except (TypeError, ValueError) as e:
            return sensors_json, f"echec de la mise à jour des données : {e}"


        else:
            sensor_updated = {'Id': sensor_id,
                              'Reseau': net[0] if type(net) == list else net,
                              'Ligne': line[0] if type(line) == list else line,
                              'Zone': zone, 'Lieu': lieu, 'pk': pk,
                              'Modele': model, 'Num': num, 'Latitude': lat, 'Longitude': long,
                              'Date_pose': date_pose,
                              'Date_depose': date_depose, 'Ouverture_pose': delta, 'Divers': divers}

            sensors_df = pd.DataFrame(sensors_json)
            sensors_json = save_old_sensors_info(db, sensors_df, sensor_updated)

            message = ["information du capteur mis a jour"]
            mylogger.info(f"{current_user.email} met à jour le fissuromètre {sensor_updated} ")

            return sensors_json, message

    @dash_app.callback(
        Output('confirm-delete-table', 'displayed'),
        Output('confirm-delete-table', 'message'),
        Input('button-delete-table', 'n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_first_step(click, sensor_select, sensors_json):
        if click is None or sensor_select is None:
            raise PreventUpdate
        else:
            confirm_message = f"Les données du capteurs {sensor_select} vont être supprimer."
            return True, confirm_message

    @dash_app.callback(
        Output('store-map-csv', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('dropdown-table', 'value', allow_duplicate=True),
        Output('time-series', 'figure', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('form-card', 'children', allow_duplicate=True),
        Output('image-card', 'hidden', allow_duplicate=True),
        Input('confirm-delete-table', 'submit_n_clicks'),
        State('dropdown-table', 'value'),
        State('store-map-csv', 'data'),
        prevent_initial_call=True, interval=10000)
    def delete_table_final_step(click, sensor_select, sensors_json):
        if click is None or sensor_select is None:
            raise PreventUpdate
        else:
            for attempt in range(5):

                try:
                    if f"F{sensor_select}" in metadata.tables:
                        table_to_drop = metadata.tables[f"F{sensor_select}"]
                        table_to_drop.drop(db.engine)
                    else:
                        db.session.execute(text(f"DROP TABLE IF EXISTS F{sensor_select}"))
                    db.session.execute(text(f" DELETE FROM sensors_image_tb WHERE sensor_id ='{sensor_select}'"))
                    db.session.execute(text(f" DELETE FROM sensors_info_tb WHERE Id ='{sensor_select}'"))
                    sensors_df = pd.DataFrame(sensors_json)
                    sensors_df.set_index("Id", inplace=True)
                    sensor_select_dict = sensors_df.loc[sensor_select, :].to_dict()
                    sensors_df.drop(sensor_select, inplace=True, axis=0)
                    sensors_df.reset_index(inplace=True)

                    db.session.commit()
                    mylogger.info(f"{current_user.email} supprime le fissuromètre {sensor_select_dict}")
                    fig_message = (
                        "Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur existant."
                        " Tu peux aussi ajouter un nouveau capteur.")
                    ingest_message = f'capteur {sensor_select} supprimé'

                    fig = fig0
                    return sensors_df.to_dict('records'), ingest_message, "", fig, fig_message, [left_column,
                                                                                                 right_column], True
                except Exception as e:
                    mylogger.info(f"Tentative {attempt + 1} échouée: {e}")
                    db.session.close_all()
                    db.engine.dispose()
                    time.sleep(2)

            mylogger.info(f"Échec après 5 tentatives.")
            raise PreventUpdate

    @dash_app.callback(
        Output('image-message', 'children', allow_duplicate=True),
        Output('upload-image1-dcc', 'children', allow_duplicate=True),
        Input('upload-image1-dcc', 'contents'),
        State('upload-image1-dcc', 'filename'),
        State('map', 'selectedData'),
        prevent_initial_call=True
    )
    def ingest_image1(image_contents, image_name, selected_data):

        upload_info = save_image_in_database(
            db=db,
            selected_data=selected_data,
            image_content=image_contents,
            image_name=image_name,
            card_id=1)

        if upload_info.split(":")[0] == "SUCCES":
            return upload_info, html.Img(src=image_contents, width='100%')
        else:
            raise PreventUpdate

    @dash_app.callback(
        Output('image-message', 'children', allow_duplicate=True),
        Output('upload-image2-dcc', 'children', allow_duplicate=True),
        Input('upload-image2-dcc', 'contents'),
        State('upload-image2-dcc', 'filename'),
        State('map', 'selectedData'),
        prevent_initial_call=True
    )
    def ingest_image2(image_contents, image_name, selected_data):

        upload_info = save_image_in_database(
            db=db,
            selected_data=selected_data,
            image_content=image_contents,
            image_name=image_name,
            card_id=2)

        if upload_info.split(":")[0] == "SUCCES":
            return upload_info, html.Img(src=image_contents, width='100%')
        else:
            raise PreventUpdate
