import time
import re
import numpy as np
from dash import html, Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd

from flask_login import current_user
from sqlalchemy import text, Table, MetaData, Column, Float, Integer, inspect

from app_factory.models import SensorInfo
from app_factory.utils.callback_function import parse_file_and_update_ingest_card
from app_factory.utils.ingest import save_image, \
    save_new_sensors_info, save_old_sensors_info, query_sensors_info_and_create_sensors_json, save_measures
from app_factory.utils.fig import create_map
from app_factory.utils.card import query_time_series_and_create_fig_card, \
    query_images_and_create_image_card
from app_factory import db

import logging.config

logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)


def register_callbacks(dash_app):
    @dash_app.callback(
        Output('store-sensors-info', 'data'),
        Output('welcome-info', 'children'),
        Input('url', 'pathname'))
    def welcome(url):
        if current_user.is_authenticated:
            mylogger.info(f"{current_user.email} ouvre l'application")

            return query_sensors_info_and_create_sensors_json(db), f'Bienvenue {current_user.email}'
        else:

            return [], "pas d'authentification"

    @dash_app.callback(
        Output('map', 'figure'),
        Input('store-sensors-info', 'data'),
        State('map', 'selectedData'))
    def update_map(sensors_json, selected_data):
        selected_point_index = -1

        if selected_data and 'points' in selected_data.keys() and selected_data['points'] != []:

            selected_sensor_id = selected_data['points'][0]['customdata'][0]
            sensors_df = pd.DataFrame(sensors_json)
            if sensors_df.shape[0] > 0:
                index = sensors_df.loc[sensors_df.Id == selected_sensor_id].index
                selected_point_index = -1 if len(index) == 0 else index[0]

        return create_map(sensors_json, selected_point_index)

    @dash_app.callback(Output('button-update-fig', 'hidden'),
                       Output('fig-message', 'children', allow_duplicate=True),
                       Input('date-picker-select', "start_date"),
                       Input('date-picker-select', "end_date"),
                       Input('aggregate-choice', 'value'),
                       State('map', 'selectedData'))
    def show_update_button(start_date, end_date, aggregate, selected_data):

        if selected_data and 'points' in selected_data.keys() and len(selected_data['points']) > 0:
            return False, "Appuies sur le bouton pour mettre à jour le graphique."
        else:
            raise PreventUpdate

    @dash_app.callback(
        Output('time-series-card', 'hidden'),
        Output('image-card', 'hidden'),
        Input('map', 'selectedData'))
    def show_image(selected_data):
        if selected_data and ('points' in selected_data.keys() and len(selected_data['points']) > 0):
            return False, False
        else:
            return True, True

    @dash_app.callback(

        Output('button-update-fig', 'hidden', allow_duplicate=True),
        Output('upload-image1-dcc', 'children'),
        Output('upload-image2-dcc', 'children'),
        Output('time-series-card', 'children', allow_duplicate=True),
        Output('fig-message', 'children', allow_duplicate=True),
        Output('image-message', 'children'),

        Input('button-update-fig', 'n_clicks'),
        Input('map', 'selectedData'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('store-sensors-info', 'data'),
        State('image-card', 'hidden'))
    def update_with_click_on_map(n_click, selected_data, start_date, end_date, aggregate, sensor_json,
                                 image_card_is_hidden):

        fig_card_children = []
        fig_message = "👋 Aucun capteur n'est sélectionné. Click sur la carte pour sélectionner un capteur."
        image_message = ""
        image1 = ""
        image2 = ""

        if selected_data and 'points' in selected_data.keys() and len(selected_data['points']) > 0:

            try:
                sensor_id = selected_data['points'][0]['customdata'][
                    0]  # premier 0 car on prend seulement le premier point selectionné

                sensors_df = pd.DataFrame(sensor_json)
                sensors_df = sensors_df.set_index("Id")
                delta = sensors_df.loc[sensor_id, "Ouverture_pose"]

                fig_card_children, fig_message = query_time_series_and_create_fig_card(db, sensor_id, start_date,
                                                                                       end_date, aggregate,
                                                                                       delta)
                image1 = query_images_and_create_image_card(db, sensor_id, 1, current_user.role)
                image2 = query_images_and_create_image_card(db, sensor_id, 2, current_user.role)

            except Exception as e:
                fig_message = "💣💣💣 indisponibilité du capteur"
                mylogger.error(f"{current_user.email} lève l'erreur {e}")

        if image_card_is_hidden:
            time.sleep(0)
        return True, image1, image2, fig_card_children, fig_message, image_message


def register_owner_callbacks(dash_app):
    @dash_app.callback(
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
        Output('textarea-date-collecte', "value"),
        Input('map', 'selectedData'),
        State('store-sensors-info', 'data'),
        Input('map', 'clickData'))
    def update_form_card(selected_data, data, click_data):

        model, num, zone, pk, place = "", "", "", "", ""
        lat, long = "", "",
        date_pose, date_depose, date_collecte = "", "", ""
        delta, divers = "", ""
        net, line = "", ""
        sensor_id = ""

        sensors_df = pd.DataFrame(data)

        if selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):

            if click_data and 'points' in click_data.keys() and type(
                    click_data['points'][0]['customdata']) == str:
                route = click_data['points'][0]['customdata']
                net = route.split(" ")[0]
                line = route.split(" ")[1]

        else:

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
            date_collecte = sensors_df.loc[sensor_id, "Date_collecte"]

            if date_depose is None: date_depose = ""
            if date_collecte is None: date_collecte = ""
            if pd.isna(pk) or pk is None: pk = ""
            if pd.isna(delta) or delta is None: delta = ""

        return (model, num, zone, place, str(pk), str(lat), str(long),
                str(date_pose), str(date_depose), str(delta), divers, net, line, str(sensor_id), str(date_collecte)
                )

    @dash_app.callback(
        Output('dropdown-line', 'options'),
        Input('dropdown-net', 'value'))
    def update_line_options(net_value):
        line_options = []
        if "RER" in net_value:
            line_options += ["A", "B"]
        if "METRO" in net_value:
            line_options += ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14"]
        if "TRAM" in net_value:
            line_options += ["1", "2", "3,""4", "5", "6", "7", "8", "9", "10"]
        return line_options

    @dash_app.callback(
        Output('button-update-sensors-info', 'hidden'),
        Output('button-delete-table', 'hidden'),
        Input('map', 'selectedData'))
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
        Output('time-series-card', 'hidden', allow_duplicate=True),
        Input('upload-file-dcc', 'contents'),
        State('upload-file-dcc', 'filename'))
    def ingest_first_step(contents, filename):
        return parse_file_and_update_ingest_card(contents, filename)

    @dash_app.callback(
        Output('confirm-throw-ingestion', 'displayed'),
        Output('confirm-throw-ingestion', 'message'),
        Output('store-sensors-info-to-ingest', 'data'),
        Output('ingest-message', 'children', allow_duplicate=True),
        Input('button-ingest', 'n_clicks'),
        State('map', 'selectedData'),
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
        State('textarea-date-collecte', 'value'),
        State('store-sensors-info-to-ingest', 'data'))
    def ingest_middle_step(click, selected_data, model, num, net, line, zone, lieu, pk, long, lat, date_pose,
                           date_depose, delta, divers, date_collecte, sensor_dict_stored):
        sensor_id = ""
        ingest_message = ""
        confirm_message_is_displayed = False
        confirm_message = ""
        sensor_dict = {}

        if sensor_dict_stored != {}:
            confirm_message_is_displayed = True
            confirm_message = f"""
                    🔥 Relance l'ingestion précedente.
                    click ok, pour lancer l'intégration.
                    click annuler puis rafraichis la page.
            """
            sensor_dict = sensor_dict_stored


        elif any(len(value) == 0 for value in [net, line]):
            ingest_message = "⚠️ La ligne ou le réseau ne sont pas renseignés"

        elif any(value == "" for value in [zone, model, lat, long]):
            ingest_message = "⚠️ Des élements obligatoires ne sont pas renseignés dans le formulaire"

        elif not (re.compile(r'^-?\d*\.?\d*$').match(pk) or pk == ""):
            ingest_message = "⚠️ Le pk est un chiffre."

        elif not (re.compile(r'^-?\d*\.?\d*$').match(delta) or delta == ""):
            ingest_message = "⚠️ L'ouverture est un chiffre."

        elif not (re.compile(r'^-?\d*\.?\d*$').match(lat)):
            ingest_message = "⚠️ La latitude est un chiffre."

        elif not (re.compile(r'^-?\d*\.?\d*$').match(long)):
            ingest_message = "⚠️ Le longitude est un chiffre."

        elif not (re.compile(r'^[a-zA-Z0-9]+$').match(num) or num == ""):
            ingest_message = "⚠️ Le numéro du capteur comporte uniquement des lettres ou des chiffres."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_pose)):
            ingest_message = "⚠️ Le date de pose est de la forme 01/01/2024."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_depose) or date_depose == ""):
            ingest_message = "⚠️ Le date de dépose est de la forme 01/01/2024."

        elif not (re.compile(r'^\d{2}/\d{2}/\d{4}$').match(date_collecte) or date_collecte == ""):
            ingest_message = "⚠️ Le date de dépose est de la forme 01/01/2024."

        elif type(net) == list and len(net) > 1:
            ingest_message = "⚠️ Sélectionne une seul reseau!"

        elif type(line) == list and len(line) > 1:
            ingest_message = "⚠️ Sélectionne une seule ligne!"

        else:
            confirm_message_is_displayed = True
            selected_sensor = selected_data['points'][0] if selected_data and 'points' in selected_data.keys() and len(
                selected_data['points']) > 0 else None
            if selected_sensor:
                sensor_id = selected_data['points'][0]['customdata'][0]

                confirm_message = f"""
                🏳️‍🌈 Ton fichier est associé à un capteur existant F{sensor_id}.  
                click ok, pour lancer l'intégration.
        
                click annuler, pour arrêter l'ingestion et changer de capteur.      
        """

            else:
                confirm_message = f"""
        🚨 Ton fichier concerne un NOUVEAU capteur.
        Vérifies bien que ton capteur n'existe pas sur la carte.     
        Click OK pour lancer l'ingestion.
        """

            sensor_dict = {'Id': sensor_id, 'Num': num, 'Modele': model,
                           'Reseau': net[0] if type(net) == list else net,
                           'Ligne': line[0] if type(line) == list else line,
                           'Zone': zone, 'Lieu': lieu,
                           'pk': None if pk == '' else float(pk),
                           'Latitude': float(lat), 'Longitude': float(long),
                           'Date_pose': date_pose, 'Date_depose': date_depose,
                           'Ouverture_pose': None if delta == '' else float(delta),
                           'Divers': divers,
                           'Date_collecte': date_collecte}

        return confirm_message_is_displayed, confirm_message, sensor_dict, ingest_message

    @dash_app.callback(

        Output('store-sensors-info', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('map', 'selectedData'),
        Output('store-data-uploaded', 'data', allow_duplicate=True),
        Output('store-sensors-info-to-ingest', 'data', allow_duplicate=True),
        Output('upload-file-inner-card', 'children', allow_duplicate=True),
        Input('confirm-throw-ingestion', 'submit_n_clicks'),
        State('store-data-uploaded', 'data'),
        State('store-sensors-info', 'data'),
        State('store-sensors-info-to-ingest', 'data'),
        State('date-picker-select', "start_date"),
        State('date-picker-select', "end_date"),
        State('aggregate-choice', 'value'),
        State('map', 'selectedData'),
        State('upload-file-inner-card', 'children'),
    )
    def ingest_final_step(click, data, sensors_json, new_sensor_dict, start_date, end_date, aggregate, selected_data,
                          inner_card):

        database_info = [""]
        mylogger.info(f"{current_user.email} lance ingest_final_step")

        if selected_data and 'points' in selected_data.keys() and len(selected_data['points']) > 0:
            sensor_id = selected_data['points'][0]['customdata'][0]

            try:
                table_length_before = db.session.execute(text(f"SELECT COUNT(*) FROM F{sensor_id};")).scalar()
                save_measures(db, data, sensor_id)
            except:
                mylogger.error(f"{current_user.email} échoue l'intégration des mesures")
                database_info = "❌❌❌ Les mesures n'ont pas été intégrées."
                return query_sensors_info_and_create_sensors_json(
                    db), database_info, selected_data, data, {}, inner_card
            else:
                db.session.commit()
                table_length_after = db.session.execute(text(f"SELECT COUNT(*) FROM F{sensor_id};")).scalar()
                table_length = table_length_after - table_length_before
                database_info = [f"✔️ Le capteur F{sensor_id} a intégré {table_length} mesures."]
                mylogger.info(f"{current_user.email} ajoute des mesures au fissuromètre {new_sensor_dict}")
                new_sensor_dict["Id"] = sensor_id
                sensors_json, message = save_old_sensors_info(db, sensors_json, new_sensor_dict)
                database_info = database_info + [message]

                return sensors_json, database_info, selected_data, [], {'ingest_final_step': 'old_sensor'}, ""


        else:

            for attempt in range(5):

                try:

                    sensors_id = [sensor_id[0] for sensor_id in db.session.query(SensorInfo.Id)]

                    tables = inspect(db.engine).get_table_names()
                    sensors_id_from_tables = [int(table.replace("F", "")) for table in tables if
                                              table.startswith("F")]
                    sensor_id = 1
                    while sensor_id in sensors_id + sensors_id_from_tables:
                        sensor_id = sensor_id + 1

                    mylogger.info(
                        f"{current_user.email} tente de créer un nouveau capteur pour la {attempt + 1} ème fois")
                    mylogger.info(f"{current_user.email} nomme le capteur {sensor_id} ")

                    new_sensor_dict["Id"] = sensor_id

                    sensors_json = save_new_sensors_info(db, sensors_json, new_sensor_dict)
                    db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    mylogger.error(f"{current_user.email} échoue la sauvegarde des informations : {e}")
                    database_info = database_info + ["❌Perte des informations "]  # on retourne dans la boucle

                else:

                    mylogger.info(f"{current_user.email} sauve les informations: {new_sensor_dict}")
                    database_info = database_info + ["😍Informations sauvegardées "]

                    try:

                        table = Table(
                            f"F{sensor_id}",
                            MetaData(),
                            Column('unix', Integer, primary_key=True),
                            Column('mm', Float),
                            Column('celsius', Float))
                        table.create(db.engine)


                    except Exception as e:
                        mylogger.error(f"{current_user.email} échoue la création de la table: {e}")
                        database_info = database_info + ["❌Table absente "]
                        time.sleep(5)
                        try:
                            sensor = SensorInfo.query.get(sensor_id)
                            db.session.delete(sensor)
                            db.session.commit()
                        except:
                            db.session.rollback()
                            mylogger.info(
                                f"{current_user.email} echoue la suppression des information du capteur {sensor_id}")
                            database_info = database_info + ["❌Informations erronée"]
                        else:
                            mylogger.info(f"{current_user.email} supprime les informations du capteur {sensor_id}")
                            database_info = database_info + ["✔️Informations purgées "]

                    else:

                        mylogger.info(f"{current_user.email} crée la table F{sensor_id}")
                        database_info = [f"✔️Création du capteur {sensor_id} "]

                        try:
                            save_measures(db, data, sensor_id)
                            db.session.commit()

                        except:
                            db.session.rollback()
                            mylogger.error(f"{current_user.email} échoue l'intégration des mesures")
                            database_info = database_info + [" ❌Aucune mesure"]

                        else:

                            table_length = db.session.execute(text(f"SELECT COUNT(*) FROM F{sensor_id};")).scalar()
                            mylogger.info(f"{current_user.email} intégre {table_length} mesures")
                            database_info = database_info + (
                                [f"✔️ Intégration de {table_length} mesures "])
                            selected_data = {'points': [{'customdata': [sensor_id]}]}

                        return sensors_json, database_info, selected_data, [], {'ingest_final_step': 'new_sensor'}, ""

            # database_info = "🔥🔥🔥 Echec de la création du capteur"
            sensors_json = query_sensors_info_and_create_sensors_json(db)
            return sensors_json, database_info, selected_data, data, new_sensor_dict, inner_card

    @dash_app.callback(

        Output('store-sensors-info', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Input('button-update-sensors-info', 'n_clicks'),
        State('store-sensors-info', 'data'),
        State('map', 'selectedData'),
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
        State('textarea-date-collecte', 'value'),
    )
    def update_sensors_info(click, sensors_json, selected_data, lat, long, pk, delta, num, date_pose, date_depose,
                            lieu, zone, divers, model, net, line, date_collecte):

        if click is None or selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            raise PreventUpdate

        else:
            sensor_id = selected_data['points'][0]['customdata'][0]
            sensor_updated = {'Id': sensor_id,
                              'Reseau': net[0] if type(net) == list else net,
                              'Ligne': line[0] if type(line) == list else line,
                              'Zone': zone, 'Lieu': lieu,
                              'pk': pk,
                              'Modele': model, 'Num': num, 'Latitude': lat, 'Longitude': long,
                              'Date_pose': date_pose,
                              'Date_depose': date_depose,
                              'Ouverture_pose': delta,
                              'Divers': divers,
                              'Date_collecte': date_collecte}

            try:
                sensors_json, diff_sensor = save_old_sensors_info(db, sensors_json, sensor_updated)
            except Exception as e:
                mylogger.error(e)
                message = f"❌ Les informations du capteur ne sont pas mis à jour."
            else:
                mylogger.info(
                    f"{current_user.email} met jour les informations du capteur {sensor_id} suivantes: {diff_sensor} ")
                message = f"😍 Les informations du capteur sont mis à jour."
                db.session.commit()

            return sensors_json, message

    @dash_app.callback(
        Output('confirm-delete-table', 'displayed'),
        Output('confirm-delete-table', 'message'),
        Input('button-delete-table', 'n_clicks'),
        State('map', 'selectedData'),
        State('store-sensors-info', 'data'))
    def delete_table_first_step(click, selected_data, sensors_json):

        if click is None or selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            raise PreventUpdate
        else:
            sensor_id = selected_data['points'][0]['customdata'][0]

            confirm_message = f" 💀 Les données du capteur {sensor_id} vont être supprimées."
            return True, confirm_message

    @dash_app.callback(
        Output('store-sensors-info', 'data', allow_duplicate=True),
        Output('ingest-message', 'children', allow_duplicate=True),
        Output('map', 'selectedData', allow_duplicate=True),
        Input('confirm-delete-table', 'submit_n_clicks'),
        State('map', 'selectedData'),
        State('store-sensors-info', 'data'))
    def delete_table_final_step(click, selected_data, sensors_json):
        if click is None or selected_data is None or (
                selected_data and 'points' in selected_data.keys() and selected_data['points'] == []):
            raise PreventUpdate

        else:
            sensor_id = selected_data['points'][0]['customdata'][0]
            mylogger.info(f"{current_user.email} demande la suppression du capteur {sensor_id}")
            for attempt in range(5):

                try:
                    db.session.execute(text(f" DELETE FROM sensors_image_tb WHERE sensor_id ='{sensor_id}'"))
                    db.session.execute(text(f" DELETE FROM sensors_info_tb WHERE Id ='{sensor_id}'"))

                except Exception as e:
                    mylogger.error(
                        f"{current_user.email} échoue pour la {attempt + 1} ième fois la suppression de la ligne avec l'erreur: {e}")
                    time.sleep(2)

                else:

                    try:
                        if db.engine.name == 'sqlite':
                            db.session.commit()

                        table_to_drop = Table(f"F{sensor_id}",
                                              MetaData(),
                                              Column('unix', Integer, primary_key=True),
                                              Column('mm', Float),
                                              Column('celsius', Float))
                        table_to_drop.drop(db.engine)

                    except Exception as e:
                        mylogger.error(
                            f"{current_user.email} échoue pour la {attempt + 1} ième fois la suppression de la table avec l'erreur : {e}")

                    else:
                        db.session.commit()
                        sensors_df = pd.DataFrame(sensors_json)
                        sensors_df.set_index("Id", inplace=True)
                        sensor_dict = sensors_df.loc[sensor_id, :].to_dict()
                        sensors_df.drop(sensor_id, inplace=True, axis=0)
                        sensors_df.reset_index(inplace=True)
                        sensor_dict["Id"] = sensor_id
                        mylogger.info(f"{current_user.email} supprime le fissuromètre {sensor_dict}")
                        ingest_message = f'capteur {sensor_id} supprimé 👌'

                        return sensors_df.to_dict('records'), ingest_message, None

            mylogger.error(f"{current_user.email} échoue la suppression du capteur")
            return sensors_json, "❌ Échec de la suppression du capteur", selected_data

    @dash_app.callback(
        Output('image-message', 'children', allow_duplicate=True),
        Output('upload-image1-dcc', 'children', allow_duplicate=True),
        Input('upload-image1-dcc', 'contents'),
        State('upload-image1-dcc', 'filename'),
        State('map', 'selectedData')
    )
    def ingest_image1(image_contents, image_name, selected_data):

        upload_info = save_image(
            db=db,
            selected_data=selected_data,
            image_content=image_contents,
            image_name=image_name,
            card_id=1)

        return upload_info, html.Img(src=image_contents, width='100%')

    @dash_app.callback(
        Output('image-message', 'children', allow_duplicate=True),
        Output('upload-image2-dcc', 'children', allow_duplicate=True),
        Input('upload-image2-dcc', 'contents'),
        State('upload-image2-dcc', 'filename'),
        State('map', 'selectedData')
    )
    def ingest_image2(image_contents, image_name, selected_data):

        upload_info = save_image(
            db=db,
            selected_data=selected_data,
            image_content=image_contents,
            image_name=image_name,
            card_id=2)

        return upload_info, html.Img(src=image_contents, width='100%')
